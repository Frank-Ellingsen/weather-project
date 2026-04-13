https://frank-ellingsen.github.io/weather-project/
[Weather Project](https://frank-ellingsen.github.io/weather-project/)
# Weather Project 🌦️

Automated Python project that collects weather data on an hourly schedule, stores it in a SQLite database, and generates an up‑to‑date HTML weather report using GitHub Actions.


## 📌 Features

- Hourly weather data collection via external API
- Persistent SQLite database updated automatically
- HTML report generation
- Fully automated scheduling with GitHub Actions
- Manual workflow trigger support

---

## 🗂️ Project Structure

```text
weather-project/
├── weather.py                 # Fetches and stores weather data
├── generate_report.py         # Generates HTML report from database
├── requirements.txt           # Python dependencies
├── weather.db                 # SQLite database (auto-updated)
├── docs/
│   └── weather_report.html    # Generated HTML report
├── .github/
│   └── workflows/
│       └── weather.yml        # GitHub Actions workflow
└── README.md
