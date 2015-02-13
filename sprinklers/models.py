from django.db import models
from django.utils.timezone import utc
import datetime
import logging
import sprinklers.circuit_backend as backend
from sensor_data import cumulative
from sensor_data.models import Sensor

log = logging.getLogger(__name__)


MAX_RUN_TIME = datetime.timedelta(minutes=45)
"Max time to allow sprinklers to run"


def detect_current_state():
    """
    Query the known sensors, and update their current state from live data
    """
    log.info("Verifying circuit states")
    for circuit in Circuit.objects.all():
        try:
            current_state = backend.get_state(circuit.path)

            if current_state != circuit.current_state:
                log.info("Circuit %s doesn't match current state - "
                         "updating to %d", circuit.label, current_state)
                circuit.current_state = current_state
                circuit.save()
        except Exception:
            log.exception("Failed to read circuit %s", circuit.label)


def stop_all():
    for circuit in Circuit.objects.all():
        if circuit.current_state:
            circuit.stop_watering()
            circuit.save()


def circuits_by_percentage():
    """
    Return a sorted list of all circuits by worst percentage

    If we're in a watering time slot, start watering with
    the first (i.e., worst) item in the returned list
    """
    return sorted(Circuit.objects.all(), key=Circuit.percent_of_target)


def ok_to_start_watering():
    """
    Determine if it's OK to start watering right now
    """
    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    times = WateringTime.objects.all()
    for time in times:
        if time.weekday == now.weekday() and \
                now.time() >= time.start_time and \
                now.time() <= time.end_time:
            log.debug("We're within a watering time: %r", time)
            return True
    log.debug("We're not within a watering time")
    return False


def check_for_rain(circuit):
    """
    Given a circuit, see if there has been any rain since last watering
    """
    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    two_weeks = datetime.timedelta(days=14)
    last_watered = circuit.last_watered()

    # Check since last watering time, or 2 weeks ago
    if last_watered and now - last_watered < two_weeks:
        start = last_watered
    else:
        start = now - two_weeks

    # TODO - Create a rain module to hide the gory details...
    sensor = Sensor.objects.filter(name='Rainfall')[0]
    raw_data = cumulative.get_readings(sensor, start, None, 0.01)
    total = cumulative.get_range(raw_data)

    # Ignore extremely light drizzle
    if total < 0.05:
        return

    event = WateringEvent(circuit=circuit,
                          volume=str(total))
    event.save()
    # Figure out when the rain stopped
    last = raw_data[-1]
    reading = last.value
    for data in reversed(raw_data):
        if data.value != reading:
            last = data
            break
    event.time = last.ts
    event.save()
    log.info("Adding rain watering event %r on %r", event.volume, event.time)


def poll():
    """
    Called periodically to turn on/off sprinklers as needed

    This routine uses the targets and trailing percentage to
    cyle through sprinklers.
    """
    print('XXX poll')
    detect_current_state()
    circuits = circuits_by_percentage()
    now = datetime.datetime.utcnow().replace(tzinfo=utc)

    running = [c for c in circuits if c.current_state]
    if running:
        print('XXX running', running[0])
        circuit = running[0]
        log.debug("%r currently watering", circuit.label)
        # Should we keep running it, or stop it?
        last_watered = circuit.last_watered()
        if now - last_watered > MAX_RUN_TIME:
            log.info("Exceeded max time, stopping")
            circuit.stop_watering()
        else:
            # How many cycles should we aim for per week?
            cycle_count_goal = 24 * 7 / circuit.spacing_hr
            if cycle_count_goal < 1:
                cycle_count_goal = 1

            log.debug("cycle_count_goal: %r", cycle_count_goal)
            # How long should the cycles be (minutes)?
            cycle_length_goal = float(circuit.target_wk) / \
                float(circuit.rate_hr) / cycle_count_goal * 60
            if now - last_watered < datetime.timedelta(
                    minutes=cycle_length_goal):
                # Still needs more time
                log.debug("Needs more time")
                return
            log.info("Watered enough, stopping")
            circuit.stop_watering()

    if not ok_to_start_watering():
        return

    for circuit in circuits:
        log.debug("Evaluating %s for watering", circuit.label)
        check_for_rain(circuit)
        if circuit.disabled:
            log.debug("Skipping since it's disabled")
            continue
        percent_of_target = circuit.percent_of_target()
        if percent_of_target >= 1.0:
            # already over target, skip this one
            log.debug("Skipping already over target: %r",
                      percent_of_target*100)
            continue
        last_watered = circuit.last_watered()
        if last_watered and \
                (now - datetime.timedelta(hours=circuit.spacing_hr)) \
                < last_watered:
            # Hasn't been long enough since last watering, skip this one
            log.debug("Skipping since watered too recently")
            continue
        log.info("Picking %r to water", circuit.label)
        circuit.start_watering()
        return
    log.info("No circuits to water at this time")


class Circuit(models.Model):
    path = models.CharField(max_length=128, blank=True)
    label = models.CharField(max_length=96, blank=True)
    current_state = models.BooleanField(default=False)
    disabled = models.BooleanField(default=False)

    # Typically units such as inches of water per hour
    # target and rate must be same units
    # Defaults set up to give ~2 15 minute watering cycles per week
    volume_label = models.CharField(max_length=96, blank=True,
                                    default='inches')
    target_wk = models.DecimalField(max_digits=10,
                                    decimal_places=4,
                                    blank=False,
                                    default=1.0)
    rate_hr = models.DecimalField(max_digits=10,
                                  decimal_places=4,
                                  blank=False,
                                  default=2.0)
    spacing_hr = models.IntegerField('Minimum hours between watering',
                                     default=48)

    def __unicode__(self):
        # TODO Might want to make this prettier
        return "%s - currently %s (%s)%s" % (self.label,
                                             "ON" if self.current_state
                                             else "OFF",
                                             self.path,
                                             " DISABLED" if self.disabled
                                             else "")

    def start_watering(self):
        try:
            self.current_state = True
            event = WateringEvent(circuit=self,
                                  volume="0.0")
            # Make sure all other sprinklers are turned off first
            stop_all()
            backend.start(self.path)
            event.save()
            self.save()
        except Exception:
            # If something goes wrong, stop it just in case
            # so we don't wind up with runaway sprinklers
            log.exception("Failed to start %r", self.label)
            backend.stop(self.path)
            raise

    def stop_watering(self):
        self.current_state = False
        finish = datetime.datetime.utcnow().replace(tzinfo=utc)
        backend.stop(self.path)
        self.save()
        event = WateringEvent.objects.filter(circuit=self).order_by(
            '-time')[0]
        print('Found event', event)
        if float(event.volume) < 0.0001:
            start = event.time

            # Missing in python 2.6
            def total_seconds(td):
                return (td.microseconds +
                        (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

            delta = total_seconds(finish - start)
            # convert duration to hours for calculations
            duration = float(delta / 3600.0)
            event.volume = str(duration * float(self.rate_hr))
            print('Watering volume is', event.volume)
            event.save()
        else:
            print('bustage')
            log.warning("Iconsistent watering event detected")

    def last_watered(self):
        try:
            return WateringEvent.objects.filter(circuit=self).order_by(
                '-time')[0].time
        except:
            return None

    def percent_of_target(self):
        """
        Figure out how close we are to our target over the last 2 weeks

        :returns: A float percentage with 1.0 == 100%
                  actual values may exceed 100% if we've overwatered
        """
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        two_weeks_ago = now - datetime.timedelta(days=14)
        events = WateringEvent.objects.filter(circuit=self).filter(
            time__gt=two_weeks_ago)
        actual = sum([float(e.volume) for e in events])
        goal = float(self.target_wk) * 2.0
        return actual / goal


class WateringEvent(models.Model):
    circuit = models.ForeignKey(Circuit)
    time = models.DateTimeField(auto_now_add=True)
    volume = models.DecimalField(max_digits=10,
                                 decimal_places=4,
                                 blank=False)

    def __unicode__(self):
        return u"%s %r %r" % (self.circuit.label,
                              self.time,
                              self.volume)


class WateringTime(models.Model):
    weekday = models.IntegerField('Day of week (0==Monday)')
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __unicode__(self):
        dow = [
            'Monday',
            'Tuesday',
            'Wednesday',
            'Thursday',
            'Friday',
            'Saturday',
            'Sunday']
        return u"%s %s - %s" % (dow[self.weekday],
                                self.start_time,
                                self.end_time)


class Configuration(models.Model):
    price_per_cf = models.DecimalField(max_digits=8, decimal_places=5)
    max_active_circuits = models.IntegerField(default=1)
