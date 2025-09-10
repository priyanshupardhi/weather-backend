from rest_framework import serializers
from .models import WeatherRecord


class WeatherRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherRecord
        fields = [
            "timestamp",
            "latitude",
            "longitude",
            "temperature_2m",
            "relative_humidity_2m",
        ]


