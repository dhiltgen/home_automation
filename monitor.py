#!/usr/bin/python


# Monitor a set of sensors and load them into the web app database


import datetime
import httplib
import os
import subprocess
import sys
import logging

log = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "home_automation.settings")
from sensor_data.models import Sensor, Reading, Prediction
from sprinklers.models import Circuit
from django.utils.timezone import utc
from django.db import transaction

sensors = [
   { 'name':'Outside Humidity',
     'server':'sensors:4304',
     'device':'26.C29821010000',
     'subsensor':'humidity'},
   { 'name':'Outside Temperature',
     'server':'sensors:4304',
     'device':'26.C29821010000',
     'subsensor':'temperature'},
   { 'name':'Cellar Temperature',
     'server':'proto:4304',
     'device':'26.489A21010000',
     'subsensor':'temperature'},
   { 'name':'Cellar Humidity',
     'server':'proto:4304',
     'device':'26.489A21010000',
     'subsensor':'humidity'},
   { 'name':'Rainfall',
     'server':'sensors:4304',
     'device':'1D.3ACA0F000000',
     'subsensor':'counters.B'}
   ]

def cycle_sprinklers():
    """
    Iterate through the sprinkler circuits and update as needed

    This code will check for scheduled starts, and expired durations
    and start/stop circuits as needed.
    """

    utcnow = datetime.datetime.utcnow().replace(tzinfo=utc)
    # First turn anything off that needs to be turned off
    circuits = Circuit.objects.all()
    for circuit in circuits:
        if not circuit.current_state:
            continue
        if circuit.last_duration:
            duration = datetime.timedelta(minutes=circuit.last_duration)
        else:
            # Don't let them go more than 90 minutes without a duration
            duration = datetime.timedelta(minutes=90)
        if (circuit.last_watered + duration) < utcnow:
            log.info("Stopping circuit %s", circuit.label)
            circuit.stop_watering()
            circuit.save()
            # Theoretically we should never have multiples running
            # but we'll continue looping just to be paranoid
        else:
            timeleft = utcnow - circuit.last_watered - duration
            log.debug("Circuit %s still running for %r", circuit.label,
                      timeleft)

    # Now check to see if we have any circuits that need to be started
    #TODO


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    dt = datetime.datetime.utcnow().replace(tzinfo=utc)

    cycle_sprinklers()

    for sensor in sensors:
        try:
            res = Sensor.objects.filter(server=sensor['server'],
                                        device=sensor['device'],
                                        subsensor=sensor['subsensor'])
            if len(res) == 1:
                s = res[0]
            else:
                raise Exception("Failed to find existing sensor definition")


            val = str(subprocess.check_output(['owread', '-s', sensor['server'], '-F', '/'+sensor['device']+'/'+sensor['subsensor']])).strip()
            print sensor['name'], val
            r = Reading(sensor=s, when=dt, value=val)
            r.save()

        except Exception as e:
            print 'Failed to insert data',  sensor['name'], e


