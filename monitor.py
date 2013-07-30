#!/usr/bin/python


# Monitor a set of sensors and load them into the web app database


import datetime
import httplib
import os
import subprocess
import sys

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


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "home_automation.settings")
    from sensor_data.models import Sensor, Reading, Prediction
    from django.utils.timezone import utc
    from django.db import transaction

    # XXX Are these timezones actually set up correctly?
    dt = datetime.datetime.utcnow().replace(tzinfo=utc)

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


