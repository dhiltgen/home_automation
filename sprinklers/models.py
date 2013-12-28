from django.db import models
from django.utils.timezone import utc
import datetime
import subprocess

# Create your models here.


def detect_current_state():
    """
    Query the known sensors, and update their current state from live data
    """
    for circuit in Circuit.objects.all():
        try:
            current_state = int(subprocess.check_output(
                ['/usr/bin/owread', circuit.path]))

            if current_state != circuit.current_state:
                log.info("Circuit %s doesn't match current state - updating to %d", circuit.label, current_state)
                circuit.current_state = current_state
                circuit.save()
        except Exception as e:
            log.exception("Failed to read circuit %s", circuit.label)


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
        self.current_state = True
        self.last_watered = datetime.datetime.utcnow().replace(tzinfo=utc)
        if duration and duration != '':
            self.last_duration = int(duration)
        else:
            self.last_duration = None
        subprocess.check_output(['/usr/bin/owwrite', self.path, '1'])

    def stop_watering(self):
        self.current_state = False
        # update the duration so it's accurate
        start = self.last_watered
        finish = datetime.datetime.utcnow().replace(tzinfo=utc)
        delta = (finish - start).total_seconds()
        if delta < 60:
            self.last_duration = 1
        else:
            self.last_duration = int(delta / 60)
        subprocess.check_output(['/usr/bin/owwrite', self.path, '0'])


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
