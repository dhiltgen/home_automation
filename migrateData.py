import os
import sys
import datetime
import gc
from pytz import timezone

pacific = timezone('US/Pacific')

# How many entries to process per transaction
BUF_SIZE=1024

# Set to false if this is a fresh load to speed it up
DUP_CHECK=True

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "home_automation.settings")
    from sensor_data.models import Sensor, Reading, Prediction
    from django.utils.timezone import utc
    from django.db import transaction

    # Hard-coded to import from the legacy sensors DB
    def sensor_load(filename, name, server, device, subsensor,
                    sensor_type, units):
        with transaction.commit_on_success():
            res = Sensor.objects.filter(name=name)
            if len(res) == 1:
                s = res[0]
            else:
                s = Sensor(name=name, server=server, device=device,
                           sensor_type=sensor_type, units=units,
                           subsensor=subsensor)
                s.save()

        with open('migrate_data/%s.txt' % (filename), 'r') as readings:
            while True:
                print 'Processing chunk...'
                print 'GC results:', gc.collect()
                buf = []
                for i in range(1, BUF_SIZE):
                    entry = readings.readline()
                    if entry == '':
                        break
                    buf.append(entry)
                if len(buf) == 0:
                    break

                # Check for dup's - assume they're batched
                if DUP_CHECK:
                    raw_when, value = buf[-1].split(',')
                    when = datetime.datetime.strptime(
                        raw_when, '%Y-%m-%d %H:%M:%S').\
                        replace(tzinfo=pacific)
                    r = Reading.objects.filter(sensor=s,
                                               when=when,
                                               value=value)
                    if len(r) == 1:
                        print 'Skipping existing block through:', when
                        continue

                with transaction.commit_on_success():
                    for line in buf:
                        raw_when, value = line.split(',')
                        when = datetime.datetime.strptime(
                            raw_when, '%Y-%m-%d %H:%M:%S').\
                            replace(tzinfo=pacific)

                        if DUP_CHECK:
                            # Look for existing reading first...
                            r = Reading.objects.filter(sensor=s,
                                                       when=when,
                                                       value=value)
                            if len(r) == 1:
                                print 'Skipping existing entry', when
                                continue
                        r = Reading(sensor=s, when=when, value=value)
                        r.save()

    # NWS predictions are "special"
    with open('migrate_data/nws_predictions.txt', 'r') as readings:
        with transaction.commit_on_success():
            for line in readings:
                raw_when, min1, min2, min3, min4, min5, min6, min7, \
                    max1, max2, max3, max4, max5, max6, max7 = line.split(',')
                when = datetime.datetime.strptime(
                    raw_when, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pacific)
                if DUP_CHECK:
                    r = Prediction.objects.filter(when=when)
                    if len(r) == 1:
                        print 'Skipping existing prediction entry', when
                        continue
                r = Prediction(when=when,
                               min1=min1,
                               min2=min2,
                               min3=min3,
                               min4=min4,
                               min5=min5,
                               min6=min6,
                               min7=min7,
                               max1=max1,
                               max2=max2,
                               max3=max3,
                               max4=max4,
                               max5=max5,
                               max6=max6,
                               max7=max7)
                r.save()

    filename = 'outside_temp'
    name = 'Outside Temperature'
    server = 'sensors:4304'
    device = '26.C29821010000'
    subsensor = 'temperature'
    sensor_type = 'T'
    units = 'fahrenheit'
    print 'Loading', name
    sensor_load(filename, name, server, device, subsensor, sensor_type, units)

    filename = 'outside_humidity'
    name = 'Outside Humidity'
    server = 'sensors:4304'
    device = '26.C29821010000'
    subsensor = 'humidity'
    sensor_type = 'H'
    units = 'percent'
    print 'Loading', name
    sensor_load(filename, name, server, device, subsensor, sensor_type, units)

    filename = 'cellar_temp'
    name = 'Cellar Temperature'
    server = 'proto:4304'
    device = '26.489A21010000'
    subsensor = 'temperature'
    sensor_type = 'T'
    units = 'fahrenheit'
    print 'Loading', name
    sensor_load(filename, name, server, device, subsensor, sensor_type, units)

    filename = 'cellar_humidity'
    name = 'Cellar Humidity'
    server = 'proto:4304'
    device = '26.489A21010000'
    subsensor = 'humidity'
    sensor_type = 'H'
    units = 'percent'
    print 'Loading', name
    sensor_load(filename, name, server, device, subsensor, sensor_type, units)


    filename = 'rain'
    name = 'Rainfall'
    server = 'sensors:4304'
    device = '1D.3ACA0F000000'
    subsensor = 'counters.B'
    sensor_type = 'R'
    units = 'counter'
    print 'Loading', name
    sensor_load(filename, name, server, device, subsensor, sensor_type, units)
