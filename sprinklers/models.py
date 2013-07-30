from django.db import models
from django.utils.timezone import utc
import datetime

# Create your models here.

class Circuit(models.Model):
    path = models.CharField(max_length=128, blank=True)
    label = models.CharField(max_length=96, blank=True)
    last_watered = models.DateTimeField(null=True, blank=True)
    last_duration = models.IntegerField('Duration (minutes)', null=True,
                                        blank=True)
    current_state = models.BooleanField(default=False)
    disabled = models.BooleanField(default=False)
    next_scheduled_run = models.DateTimeField(null=True, blank=True)
    cfh = models.IntegerField('Cubic feet per hour water usage', null=True,
                              blank=True)

    def __unicode__(self):
        # TODO Might want to make this prettier
        return "%s - currently %s" % (self.label,
                                      "ON" if self.current_state else "OFF")

    def start_watering(self, duration):
        # TODO - Actually call out to the 1-wire tools
        #
        self.current_state = True
        self.last_watered = datetime.datetime.utcnow().replace(tzinfo=utc)
        if duration and duration != '':
            self.last_duration = int(duration)
        else:
            self.last_duration = None

    def stop_watering(self):
        # TODO - Actually call out to the 1-wire tools
        #
        self.current_state = False
        # update the duration so it's accurate
        start = self.last_watered
        finish = datetime.datetime.utcnow().replace(tzinfo=utc)
        delta = (finish - start).total_seconds()
        if delta < 60:
            self.last_duration = 1
        else:
            self.last_duration = int(delta / 60)


class History(models.Model):
    circuit = models.ForeignKey(Circuit)
    time = models.DateTimeField(auto_now_add=True)
    duration = models.IntegerField('Duration (minutes)')

class Schedule(models.Model):
    circuit = models.ForeignKey(Circuit)
    interval = models.IntegerField('Interval (days)')
    start_time = models.TimeField()
    duration = models.IntegerField('Duration (minutes)')
    # TODO - add support for picking days of the week

    def __unicode__(self):
        return self.circuit.label

class Configuration(models.Model):
    price_per_cf = models.DecimalField(max_digits=8, decimal_places=5)
    max_active_circuits = models.IntegerField(default=1)
