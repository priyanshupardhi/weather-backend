from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="WeatherRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField(db_index=True)),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
                ("temperature_2m", models.FloatField()),
                ("relative_humidity_2m", models.FloatField()),
            ],
            options={
                "ordering": ["timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="weatherrecord",
            index=models.Index(fields=["timestamp"], name="weather_wea_timesta_5df3c0_idx"),
        ),
        migrations.AddIndex(
            model_name="weatherrecord",
            index=models.Index(fields=["latitude", "longitude", "timestamp"], name="weather_wea_latitud_cb6ca2_idx"),
        ),
    ]


