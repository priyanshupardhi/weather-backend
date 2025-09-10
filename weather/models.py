from django.db import models


class WeatherRecord(models.Model):
    timestamp = models.DateTimeField(db_index=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    temperature_2m = models.FloatField()
    relative_humidity_2m = models.FloatField()

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["latitude", "longitude", "timestamp"]),
        ]
        ordering = ["timestamp"]

    def __str__(self) -> str:
        return f"{self.timestamp.isoformat()} @ ({self.latitude}, {self.longitude})"


