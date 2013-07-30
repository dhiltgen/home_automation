from django.db import models

# Create your models here.

class Sensor(models.Model):
    SENSOR_TYPES = (
        ('T', 'Temperature'),
        ('H', 'Humidity'),
        ('R', 'Rain'),
        # Barameter, Moisture, Binary, ...
    )
    name = models.CharField(max_length=128, blank=False)
    server = models.CharField(max_length=96, blank=False)
    device = models.CharField(max_length=96, blank=False)
    subsensor = models.CharField(max_length=96, blank=False)
    sensor_type = models.CharField(max_length=1, choices=SENSOR_TYPES)

    # TODO - Make this an enum someday, and add smarts for conversions...
    units = models.CharField(max_length=64, blank=False)

class Reading(models.Model):
    sensor = models.ForeignKey(Sensor)
    when = models.DateTimeField(blank=False)
    value = models.DecimalField(max_digits=10, decimal_places=4, blank=False)

class Prediction(models.Model):
    """
    National Weather Service Predictions for temperatures near us

    Gathered once a day, and used for correlation and predictions on min/max
    temps over the next few days.
    """
    when = models.DateTimeField(blank=False)
    min1 = models.DecimalField(max_digits=10, decimal_places=4, blank=False)
    min2 = models.DecimalField(max_digits=10, decimal_places=4, blank=False)
    min3 = models.DecimalField(max_digits=10, decimal_places=4, blank=False)
    min4 = models.DecimalField(max_digits=10, decimal_places=4, blank=False)
    min5 = models.DecimalField(max_digits=10, decimal_places=4, blank=False)
    min6 = models.DecimalField(max_digits=10, decimal_places=4, blank=False)
    min7 = models.DecimalField(max_digits=10, decimal_places=4, blank=False)
    max1 = models.DecimalField(max_digits=10, decimal_places=4, blank=False)
    max2 = models.DecimalField(max_digits=10, decimal_places=4, blank=False)
    max3 = models.DecimalField(max_digits=10, decimal_places=4, blank=False)
    max4 = models.DecimalField(max_digits=10, decimal_places=4, blank=False)
    max5 = models.DecimalField(max_digits=10, decimal_places=4, blank=False)
    max6 = models.DecimalField(max_digits=10, decimal_places=4, blank=False)
    max7 = models.DecimalField(max_digits=10, decimal_places=4, blank=False)
