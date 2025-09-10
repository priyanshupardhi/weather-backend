# Weather Backend (Django + DRF)

Fetches time-series weather (temperature & humidity) from Open‑Meteo, stores in SQLite, and exports Excel/PDF with a chart.

## Stack
- Django 4.2, Django REST Framework
- SQLite
- Open‑Meteo API (MeteoSwiss primary, Forecast fallback)
- Pandas, Matplotlib, OpenPyXL
- PDF: WeasyPrint (primary) + ReportLab fallback
- Docker (optional)

## Setup (local)
1) Create venv and install:
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```
2) Create `.env`:
```env
DJANGO_SECRET_KEY=replace-this-in-production
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
TIME_ZONE=UTC
DEFAULT_LAT=47.37
DEFAULT_LON=8.55
```
3) Migrate and run:
```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## API Usage
- Fetch & store last 2 days:
```bash
curl "http://localhost:8000/weather-report?lat=47.37&lon=8.55"
# or rely on .env defaults:
curl "http://localhost:8000/weather-report"
```
- Export Excel (last 48h):
```bash
curl -L "http://localhost:8000/export/excel" -o weather_last_48h.xlsx
```
- Export PDF (chart + metadata):
```bash
curl -L "http://localhost:8000/export/pdf" -o weather_report.pdf
```

## Direct Open‑Meteo reference
```bash
curl "https://api.open-meteo.com/v1/meteoswiss?latitude=47.37&longitude=8.55&hourly=temperature_2m,relative_humidity_2m&past_days=2&timezone=UTC"
```

## Docker
```bash
docker compose up --build
```
App: http://localhost:8000

## Notes
- Excel requires timezone-unaware timestamps; UTC used internally.
- PDF falls back to ReportLab locally if WeasyPrint native libs are missing.
