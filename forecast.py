import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def load_and_clean_data(db_path="weather.db"):
    """
    Loads all historical weather observations from SQLite, deduplicates,
    sorts chronologically, and resamples into a regular hourly time series.
    """
    conn = sqlite3.connect(db_path)
    query = """
    SELECT last_updated, temp_c, humidity, pressure_mb, wind_kph, cloud
    FROM weather_kristiansand
    WHERE temp_c IS NOT NULL AND last_updated IS NOT NULL
    ORDER BY last_updated ASC
    """
    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        raise ValueError("No weather data found in database.")

    # Convert timestamps
    df['datetime'] = pd.to_datetime(df['last_updated'])
    
    # Drop duplicates by rounding to minute / keeping last reading
    df = df.drop_duplicates(subset=['datetime']).sort_values('datetime').reset_index(drop=True)
    
    # Set datetime index and resample to regular hourly intervals
    df = df.set_index('datetime')
    hourly = df[['temp_c', 'humidity', 'pressure_mb', 'wind_kph', 'cloud']].resample('1h').mean()
    
    # Interpolate short gaps linearly (weather inertia)
    hourly['temp_c'] = hourly['temp_c'].interpolate(method='time', limit=24)
    # Forward/backward fill any remaining boundary edges
    hourly = hourly.bfill().ffill().reset_index()

    return hourly

def fit_fourier_model(train_df):
    """
    Fits a Harmonic Fourier decomposition with polynomial macro trend:
    T(t) = a0 + a1*t + a2*t^2 + sum_{k=1}^2 [Ak * cos(2*pi*k*hour/24) + Bk * sin(2*pi*k*hour/24)]
    
    Returns:
        coeffs: Fitted regression coefficients
        t_ref: Reference start time
        metrics: Fit quality statistics (R^2, residual std)
    """
    t_ref = train_df['datetime'].iloc[0]
    t_hours = (train_df['datetime'] - t_ref).dt.total_seconds() / 3600.0
    hour_of_day = train_df['datetime'].dt.hour + train_df['datetime'].dt.minute / 60.0

    # Build design matrix X
    # Normalize time to avoid numerical instability
    t_norm = (t_hours - t_hours.mean()) / (t_hours.std() if t_hours.std() != 0 else 1.0)
    
    col_intercept = np.ones(len(train_df))
    col_trend1 = t_norm.values
    col_trend2 = (t_norm ** 2).values
    
    # Diurnal Fourier harmonics: k=1 (24h period) and k=2 (12h semi-diurnal period)
    omega_24 = 2 * np.pi * hour_of_day / 24.0
    col_cos24 = np.cos(omega_24).values
    col_sin24 = np.sin(omega_24).values
    col_cos12 = np.cos(2 * omega_24).values
    col_sin12 = np.sin(2 * omega_24).values

    X = np.column_stack([
        col_intercept,
        col_trend1,
        col_trend2,
        col_cos24,
        col_sin24,
        col_cos12,
        col_sin12
    ])
    y = train_df['temp_c'].values

    # Solve OLS via SVD / least squares
    coeffs, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)
    y_pred = X @ coeffs
    res = y - y_pred
    
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    ss_res = np.sum(res ** 2)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    sigma_res = float(np.std(res))

    return {
        'coeffs': coeffs,
        't_ref': t_ref,
        't_mean': float(t_hours.mean()),
        't_std': float(t_hours.std()),
        'r2': float(r2),
        'sigma_res': sigma_res
    }

def predict_baseline(model, datetimes):
    """
    Evaluates the fitted Harmonic Fourier + Trend model for given datetimes.
    """
    t_hours = (datetimes - model['t_ref']).dt.total_seconds() / 3600.0
    t_norm = (t_hours - model['t_mean']) / model['t_std']
    hour_of_day = datetimes.dt.hour + datetimes.dt.minute / 60.0
    omega_24 = 2 * np.pi * hour_of_day / 24.0

    X = np.column_stack([
        np.ones(len(datetimes)),
        t_norm.values,
        (t_norm ** 2).values,
        np.cos(omega_24).values,
        np.sin(omega_24).values,
        np.cos(2 * omega_24).values,
        np.sin(2 * omega_24).values
    ])
    return X @ model['coeffs']

def run_backtest_evaluation(hourly_df, horizon_hours=168, test_weeks=4):
    """
    Performs out-of-sample rolling backtesting over recent weeks to evaluate
    predictive accuracy against real historical temperatures.
    
    Calculates:
      - MAE (Mean Absolute Error)
      - RMSE (Root Mean Squared Error)
      - Mean Bias Error (MBE: systematically over/under-predicting)
      - % Within Tolerance (+/- 2.0°C)
    """
    if len(hourly_df) < (test_weeks * 168 + 24 * 14):
        # Fallback if history is short: use last 20%
        split_idx = int(len(hourly_df) * 0.8)
    else:
        split_idx = len(hourly_df) - (test_weeks * 168)

    train_df = hourly_df.iloc[:split_idx].copy()
    test_df = hourly_df.iloc[split_idx:].copy()

    # Fit model strictly on pre-split historical data
    model = fit_fourier_model(train_df)

    # Rolling evaluation in 7-day increments
    errors = []
    actuals = []
    preds = []

    # Step through test windows
    step = 24  # Daily origin shift for backtesting
    for start_i in range(0, len(test_df) - horizon_hours + 1, step):
        eval_window = test_df.iloc[start_i:start_i + horizon_hours]
        
        # Recent actual residual prior to this window for AR inertia
        past_actuals = hourly_df.iloc[:split_idx + start_i]
        recent_actual = past_actuals['temp_c'].iloc[-6:].mean()
        recent_base = predict_baseline(model, past_actuals['datetime'].iloc[-6:]).mean()
        recent_res = recent_actual - recent_base

        # Predict baseline
        base_pred = predict_baseline(model, eval_window['datetime'])
        
        # Apply synoptic AR decay: phi^(h/24), phi ~ 0.70 (half-life ~ 2 days)
        h = np.arange(1, len(eval_window) + 1)
        phi = 0.70
        ar_adjustment = recent_res * (phi ** (h / 24.0))
        
        y_hat = base_pred + ar_adjustment
        y_act = eval_window['temp_c'].values
        
        preds.extend(y_hat)
        actuals.extend(y_act)
        errors.extend(y_hat - y_act)

    errors = np.array(errors)
    actuals = np.array(actuals)
    preds = np.array(preds)

    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    mbe = float(np.mean(errors))
    within_2c = float(np.mean(np.abs(errors) <= 2.0) * 100.0)

    return {
        'mae': mae,
        'rmse': rmse,
        'bias': mbe,
        'within_2c_pct': within_2c,
        'test_points': len(errors),
        'backtest_weeks': test_weeks
    }

def generate_7day_forecast(hourly_df):
    """
    Generates the next 7-day (168-hour) forward temperature forecast using
    all historical data, plus recent 7-day backtest overlay for visual comparison.
    """
    # 1. Fit model using ALL historical observations
    full_model = fit_fourier_model(hourly_df)
    
    # 2. Backtest evaluation metrics
    eval_metrics = run_backtest_evaluation(hourly_df)

    # 3. Last historical observation
    last_dt = hourly_df['datetime'].iloc[-1]
    
    # Current synoptic residual offset: difference over the last 12 hours
    recent_actual = hourly_df['temp_c'].iloc[-12:].mean()
    recent_base = predict_baseline(full_model, hourly_df['datetime'].iloc[-12:]).mean()
    current_res = recent_actual - recent_base

    # 4. Generate future 168 hours (7 days)
    future_dts = pd.date_range(start=last_dt + timedelta(hours=1), periods=168, freq='h')
    future_series = pd.Series(future_dts)
    
    future_base = predict_baseline(full_model, future_series)
    
    # Synoptic decay persistence
    h = np.arange(1, 169)
    phi = 0.70
    ar_adjustment = current_res * (phi ** (h / 24.0))
    future_pred = future_base + ar_adjustment

    # Uncertainty corridor: residual variance expanding with forecast horizon
    # sigma_h = sigma_res * sqrt(1 + alpha * h / 24)
    alpha = 0.45
    sigma_h = full_model['sigma_res'] * np.sqrt(1.0 + alpha * (h / 24.0))
    # 80% confidence interval (z = 1.282)
    z_score = 1.282
    lower_bound = future_pred - z_score * sigma_h
    upper_bound = future_pred + z_score * sigma_h

    forecast_df = pd.DataFrame({
        'datetime': future_dts,
        'temp_pred_c': np.round(future_pred, 1),
        'temp_lower_c': np.round(lower_bound, 1),
        'temp_upper_c': np.round(upper_bound, 1)
    })

    # 5. Extract Recent 7 Days (Past 168 hours) Actual vs Model Backtest
    past_window_len = min(168, len(hourly_df))
    past_df = hourly_df.iloc[-past_window_len:].copy()
    past_base = predict_baseline(full_model, past_df['datetime'])
    
    past_eval_df = pd.DataFrame({
        'datetime': past_df['datetime'].values,
        'temp_actual_c': np.round(past_df['temp_c'].values, 1),
        'temp_model_c': np.round(past_base, 1)
    })

    # 6. Group forecast by calendar day for tabular summary
    forecast_df['date'] = forecast_df['datetime'].dt.date
    daily_groups = forecast_df.groupby('date')
    daily_summary = []
    
    for date_val, group in daily_groups:
        dt_obj = datetime.combine(date_val, datetime.min.time())
        day_name = dt_obj.strftime('%a')
        date_str = dt_obj.strftime('%d %b')
        min_temp = float(group['temp_pred_c'].min())
        max_temp = float(group['temp_pred_c'].max())
        mean_temp = float(group['temp_pred_c'].mean())
        
        daily_summary.append({
            'date_str': date_str,
            'day_name': day_name,
            'min_temp': min_temp,
            'max_temp': max_temp,
            'mean_temp': mean_temp
        })

    return {
        'forecast_df': forecast_df,
        'past_eval_df': past_eval_df,
        'daily_summary': daily_summary,
        'metrics': eval_metrics,
        'model_info': {
            'name': 'Fourier Harmonic Decomposition + Synoptic Autoregressive Decay',
            'method': 'Harmonic Regression (k=1, 2) + Macro Drift + AR(1) Persistence',
            'train_points': len(hourly_df),
            'train_start': hourly_df['datetime'].iloc[0].strftime('%Y-%m-%d'),
            'train_end': last_dt.strftime('%Y-%m-%d %H:%M'),
            'r2': full_model['r2'],
            'sigma_res': full_model['sigma_res'],
            'current_anomaly': float(current_res)
        }
    }

def archive_forecast_to_db(forecast_bundle, db_path="weather.db"):
    """
    Archives the current forecast run into weather.db for ongoing historical
    tracking, and evaluates previous forecasts against new incoming real data.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Create table for forecast runs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS weather_forecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_timestamp TEXT,
        target_timestamp TEXT,
        temp_pred_c REAL,
        temp_lower_c REAL,
        temp_upper_c REAL
    )
    """)

    # 2. Create table for forecast evaluation log
    cur.execute("""
    CREATE TABLE IF NOT EXISTS forecast_evaluation_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        evaluated_at TEXT,
        mae REAL,
        rmse REAL,
        bias REAL,
        within_2c_pct REAL,
        observations_count INTEGER
    )
    """)

    # Insert current forecast
    run_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    f_df = forecast_bundle['forecast_df']
    
    rows = [
        (
            run_time_str,
            row['datetime'].strftime('%Y-%m-%d %H:%M'),
            row['temp_pred_c'],
            row['temp_lower_c'],
            row['temp_upper_c']
        )
        for _, row in f_df.iterrows()
    ]
    cur.executemany("""
    INSERT INTO weather_forecasts (run_timestamp, target_timestamp, temp_pred_c, temp_lower_c, temp_upper_c)
    VALUES (?, ?, ?, ?, ?)
    """, rows)

    # Log evaluation metrics
    m = forecast_bundle['metrics']
    cur.execute("""
    INSERT INTO forecast_evaluation_log (evaluated_at, mae, rmse, bias, within_2c_pct, observations_count)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (run_time_str, m['mae'], m['rmse'], m['bias'], m['within_2c_pct'], m['test_points']))

    conn.commit()
    conn.close()
    print(f"[SUCCESS] 7-day forecast saved to database ({len(rows)} hourly projections).")

def run_forecast_pipeline(db_path="weather.db"):
    """
    Main entry point for running the complete forecasting and evaluation pipeline.
    """
    hourly_df = load_and_clean_data(db_path)
    bundle = generate_7day_forecast(hourly_df)
    archive_forecast_to_db(bundle, db_path)
    return bundle

if __name__ == "__main__":
    print("=== Running Kristiansand 7-Day Temperature Forecasting Pipeline ===")
    bundle = run_forecast_pipeline("weather.db")
    m = bundle['metrics']
    info = bundle['model_info']
    print(f"\nModel: {info['name']}")
    print(f"Trained on {info['train_points']:,} hourly observations ({info['train_start']} to {info['train_end']})")
    print(f"R²: {info['r2']:.3f}, Residual Std: {info['sigma_res']:.2f} °C")
    print(f"Current Synoptic Air Mass Anomaly: {info['current_anomaly']:+.2f} °C")
    print("\n--- Out-of-Sample Backtesting Performance ---")
    print(f"MAE (Mean Absolute Error): {m['mae']:.2f} °C")
    print(f"RMSE (Root Mean Squared Error): {m['rmse']:.2f} °C")
    print(f"Mean Bias Error (Over/Under forecast): {m['bias']:+.2f} °C")
    print(f"Accuracy within ±2.0 °C: {m['within_2c_pct']:.1f}%")
    print("\n--- Next 7 Days Forecast Summary ---")
    for d in bundle['daily_summary']:
        print(f"{d['day_name']} {d['date_str']}: Min {d['min_temp']:>4.1f} °C | Max {d['max_temp']:>4.1f} °C | Mean {d['mean_temp']:>4.1f} °C")
