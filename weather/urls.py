from django.urls import path
from .views import WeatherReportView, ExportExcelView, ExportPdfView


urlpatterns = [
    path("weather-report", WeatherReportView.as_view(), name="weather-report"),
    path("export/excel", ExportExcelView.as_view(), name="export-excel"),
    path("export/pdf", ExportPdfView.as_view(), name="export-pdf"),
]


