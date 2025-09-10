import base64
import io
from datetime import datetime, timedelta, timezone

import pandas as pd
from django.db import transaction
from django.http import FileResponse, HttpResponse, JsonResponse
from django.utils.dateparse import parse_datetime
from rest_framework.views import APIView

from .models import WeatherRecord
from .serializers import WeatherRecordSerializer
from .services import fetch_weather_series, render_chart_png, pdf_html_template


class WeatherReportView(APIView):
    def get(self, request):
        # allow defaults from env if not provided
        from django.conf import settings
        try:
            lat_param = request.GET.get("lat", getattr(settings, "DEFAULT_LAT", None))
            lon_param = request.GET.get("lon", getattr(settings, "DEFAULT_LON", None))
            latitude = float(lat_param)
            longitude = float(lon_param)
        except (TypeError, ValueError):
            return JsonResponse({"detail": "lat and lon are required float query params or set DEFAULT_LAT/DEFAULT_LON in .env"}, status=400)

        df = fetch_weather_series(latitude, longitude)

        # store into DB
        with transaction.atomic():
            records = []
            for _, row in df.iterrows():
                records.append(
                    WeatherRecord(
                        timestamp=row["timestamp"],
                        latitude=latitude,
                        longitude=longitude,
                        temperature_2m=float(row["temperature_2m"]),
                        relative_humidity_2m=float(row["relative_humidity_2m"]),
                    )
                )
            # To avoid duplicates, we can bulk create and ignore conflicts for same (lat,lon,timestamp)
            # For simplicity in SQLite, delete overlapping timeframe first then insert
            start_ts = df["timestamp"].min()
            end_ts = df["timestamp"].max()
            WeatherRecord.objects.filter(
                latitude=latitude, longitude=longitude, timestamp__range=(start_ts, end_ts)
            ).delete()
            WeatherRecord.objects.bulk_create(records, batch_size=500)

        last_rec = (
            WeatherRecord.objects.filter(latitude=latitude, longitude=longitude)
            .order_by("timestamp")
            .last()
        )
        serialized = WeatherRecordSerializer(last_rec)
        return JsonResponse({"inserted": int(len(df)), "sample_last": serialized.data}, status=200)


class ExportExcelView(APIView):
    def get(self, request):
        # last 48 hours (any location)
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=48)
        qs = WeatherRecord.objects.filter(timestamp__gte=start, timestamp__lte=end).order_by("timestamp")
        df = pd.DataFrame(list(qs.values("timestamp", "temperature_2m", "relative_humidity_2m")))
        if df.empty:
            return JsonResponse({"detail": "No data in the last 48 hours"}, status=404)

        # Excel doesn't support tz-aware datetimes; ensure naïve timestamps
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        from pandas.api.types import is_datetime64tz_dtype
        if is_datetime64tz_dtype(df["timestamp"]):
            df["timestamp"] = df["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="weather")
        buf.seek(0)

        return FileResponse(buf, as_attachment=True, filename="weather_last_48h.xlsx", content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


class ExportPdfView(APIView):
    def get(self, request):
        # last 48 hours (any location)
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=48)
        qs = WeatherRecord.objects.filter(timestamp__gte=start, timestamp__lte=end).order_by("timestamp")
        df = pd.DataFrame(list(qs.values("timestamp", "temperature_2m", "relative_humidity_2m")))
        if df.empty:
            return JsonResponse({"detail": "No data in the last 48 hours"}, status=404)

        chart_png = render_chart_png(df)
        b64 = base64.b64encode(chart_png).decode("ascii")

        # Determine a representative location from data if available
        first = WeatherRecord.objects.filter(timestamp__gte=start, timestamp__lte=end).first()
        location = f"lat={first.latitude}, lon={first.longitude}" if first else "Unknown"

        html = pdf_html_template(location, start, end, b64)

        # Try WeasyPrint first; if unavailable on host, fall back to ReportLab
        try:
            from weasyprint import HTML  # type: ignore
            pdf_bytes = HTML(string=html).write_pdf()
            buf = io.BytesIO(pdf_bytes)
            buf.seek(0)
            return FileResponse(buf, as_attachment=True, filename="weather_report.pdf", content_type="application/pdf")
        except Exception:
            # Fallback: simple PDF with ReportLab and embedded chart image
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.utils import ImageReader
                from reportlab.pdfgen import canvas
            except Exception as e:
                return JsonResponse({"detail": f"PDF fallback error: {e}"}, status=500)

            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=letter)
            width, height = letter
            c.setTitle("Weather Report")
            c.setFont("Helvetica-Bold", 16)
            c.drawString(40, height - 60, "Weather Report")
            c.setFont("Helvetica", 10)
            c.drawString(40, height - 80, f"Location: {location}")
            c.drawString(40, height - 95, f"Range: {start.isoformat()} to {end.isoformat()} (UTC)")

            # Insert chart image
            img_reader = ImageReader(io.BytesIO(chart_png))
            img_width = width - 80
            img_height = img_width * 0.45
            c.drawImage(img_reader, 40, height - 120 - img_height, width=img_width, height=img_height, preserveAspectRatio=True, mask='auto')

            c.showPage()
            c.save()
            buf.seek(0)
            return FileResponse(buf, as_attachment=True, filename="weather_report.pdf", content_type="application/pdf")


