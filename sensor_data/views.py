from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from sensor_data.models import Sensor, Reading, Prediction
from datetime import datetime, timedelta

def get_humidty_and_temp_sensors(name):
    humidity = Sensor.objects.filter(name=name + " Humidity")[0]
    temp = Sensor.objects.filter(name=name + " Temperature")[0]
    return (humidity, temp)

def prime_results(request, humidity_sensor, temp_sensor):
    results = dict()
    results['temp_sensor'] = temp_sensor
    results['humidity_sensor'] = humidity_sensor
    current_temp = Reading.objects.filter(sensor_id=temp_sensor.id).latest('when')
    results['current_humidity'] = \
        Reading.objects.filter(sensor_id=humidity_sensor.id).latest('when')
    results['latest_datetime'] = current_temp.when

    day = timedelta(days=1)
    week = timedelta(weeks=1)

    results['day_ago_datetime'] = current_temp.when - day
    results['two_days_ago_datetime'] = current_temp.when - day - day
    results['week_ago_datetime'] = current_temp.when - week
    results['year_start_datetime'] = datetime(year=current_temp.when.year,
                                              month=1, day=1,
                                              tzinfo=current_temp.when.tzinfo)
    results['current_temp'] = current_temp
    return results

def prior_temp(offset, temp_sensor):
    """
    Find the temp readings for this time over the last few days

    :param count: The number of days ago to retrieve
    :returns: The reading or None
    """
    try:
        res = Reading.objects.raw(
        'select * from sensor_data_reading where '
        '`when` >= subtime(utc_timestamp(), "%d:06:00.0") and '
        '`when` <= subtime(utc_timestamp(), "%d:00:00.0") and '
        'sensor_id="%s" order by `when` desc limit 1'
        % (offset*24, offset*24, temp_sensor.id))[0]
        return res
    except:
        print 'No prior temp for', offset
        return None

# TODO - Make these calculations a little smarter about when to cross
#        over from today to yesterday, and so on...
def prior_prediction(offset):
    try:
        res = Prediction.objects.raw(
            'select * from sensor_data_prediction where '
            '`when` <= subtime(utc_timestamp(), "%d:00:00.0") and '
            '`when` >= subtime(utc_timestamp(), "%d:00:00.0") '
            'order by `when` desc limit 1' %
            ((offset * 24 - 12, (offset + 1) * 24 - 12)))[0]
        return res
    except:
        print 'No prior prediction for', offset
        return None

def prior_min_max(offset, temp_sensor):
    try:
        reading = Reading.objects.raw(
            'select cast(`when` as date), min(value) as minimum, '
            'max(value) as maximum, id, sensor_id '
            'from sensor_data_reading where sensor_id="%s" and '
            '`when` <= subtime(utc_timestamp(), "%d:00:00.0") and '
            '`when` >= subtime(utc_timestamp(), "%d:00:00.0") '
            "group by 1 order by 1 desc limit 1" %
            (temp_sensor.id, offset * 24 - 12, (offset + 1) * 24 - 12))[0]
        return (reading.minimum, reading.maximum)
    except:
        return ("NA", "NA")


def outside_current(request):
    (humidity_sensor, temp_sensor)  = get_humidty_and_temp_sensors('Outside')
    return generic_current(request, 'sensor_data/outside_current.html',
                           humidity_sensor, temp_sensor)


def cellar_current(request):
    (humidity_sensor, temp_sensor)  = get_humidty_and_temp_sensors('Cellar')
    return generic_current(request, 'sensor_data/cellar_current.html',
                           humidity_sensor, temp_sensor)


def generic_current(request, template, humidity_sensor, temp_sensor):
    results = prime_results(request, humidity_sensor, temp_sensor)
    results['active_link'] = 'current'

    results['prediction'] = Prediction.objects.latest('when')

    # TODO:
    # Prediction confidence (+/- based on accuracy over the last week)

    # TODO - Add humidity
    past = []
    for i in range(1, 5):
        past_day = dict()
        if i == 1:
            past_day['label'] = "Yesterday"
        else:
            # TODO - label for other days
            past_day['label'] = str(-i)
        try:
            past_day['at_this_time'] = prior_temp(i, temp_sensor).value
        except:
            past_day['at_this_time'] = 'NA'
        prediction = prior_prediction(i)
        if prediction:
            past_day['min_prediction'] = prediction.min1
            past_day['max_prediction'] = prediction.max1
        else:
            past_day['min_prediction'] = 'NA'
            past_day['max_prediction'] = 'NA'
        (past_day['min_actual'], past_day['max_actual']) = prior_min_max(
            i, temp_sensor)
        past.append(past_day)
    results['past'] = past

    return render_to_response(template, results)


def outside_summary(request, start_year, start_month, start_day,
                   start_hour, start_minute, start_second,
                   tz_hour, tz_minute, active_link=None):
    (humidity_sensor, temp_sensor)  = get_humidty_and_temp_sensors('Outside')
    return generic_summary(request, 'sensor_data/outside_summary.html',
                           humidity_sensor, temp_sensor,
                           start_year, start_month, start_day,
                           start_hour, start_minute, start_second,
                           tz_hour, tz_minute, active_link)


def cellar_summary(request, start_year, start_month, start_day,
                   start_hour, start_minute, start_second,
                   tz_hour, tz_minute, active_link=None):
    (humidity_sensor, temp_sensor)  = get_humidty_and_temp_sensors('Cellar')
    return generic_summary(request, 'sensor_data/cellar_summary.html',
                           humidity_sensor, temp_sensor,
                           start_year, start_month, start_day,
                           start_hour, start_minute, start_second,
                           tz_hour, tz_minute, active_link)


def generic_summary(request, template, humidity_sensor, temp_sensor,
                    start_year, start_month, start_day,
                    start_hour, start_minute, start_second,
                    tz_hour, tz_minute, active_link=None):
    results = prime_results(request, humidity_sensor, temp_sensor)
    start = datetime(int(start_year), int(start_month), int(start_day), int(start_hour), int(start_minute), int(start_second), 0).replace(tzinfo=utc)

    results['active_link'] = active_link
    raw_temps = [x for x in Reading.objects.raw(
        "select cast(`when` as date), min(value) as minimum, "
        "max(value) as maximum, id, sensor_id "
        "from sensor_data_reading where sensor_id='%s' and "
        "`when` >= '%s' "
        "group by 1 order by 1 desc" %
        (temp_sensor.id, start.strftime('%Y-%m-%d %H:%M:%S')))]
    raw_humidities = [x for x in Reading.objects.raw(
        "select cast(`when` as date), min(value) as minimum, "
        "max(value) as maximum, id, sensor_id "
        "from sensor_data_reading where sensor_id='%s' and "
        "`when` >= '%s' "
        "group by 1 order by 1 desc" %
        (humidity_sensor.id, start.strftime('%Y-%m-%d %H:%M:%S')))]
    # XXX this is a little fragile as it assumes there's always matching
    #     entries between temp and humidity readings
    readings = []
    while len(raw_temps) > 0:
        reading = raw_temps.pop()
        try:
            humidity = raw_humidities.pop()
        except:
            # Recycle prior reading
            pass
        reading.humidity_minimum = humidity.minimum
        reading.humidity_maximum = humidity.maximum
        readings.append(reading)
    results['readings'] = readings
    return render_to_response(template, results)


def outside_detail(request, start_year, start_month, start_day,
                   start_hour, start_minute, start_second,
                   tz_hour, tz_minute, active_link=None):
    (humidity_sensor, temp_sensor)  = get_humidty_and_temp_sensors('Outside')
    return generic_detail(request, 'sensor_data/outside_detail.html',
                          humidity_sensor, temp_sensor,
                          start_year, start_month, start_day,
                          start_hour, start_minute, start_second,
                          tz_hour, tz_minute, active_link)


def cellar_detail(request, start_year, start_month, start_day,
                   start_hour, start_minute, start_second,
                   tz_hour, tz_minute, active_link=None):
    (humidity_sensor, temp_sensor)  = get_humidty_and_temp_sensors('Cellar')
    return generic_detail(request, 'sensor_data/cellar_detail.html',
                          humidity_sensor, temp_sensor,
                          start_year, start_month, start_day,
                          start_hour, start_minute, start_second,
                          tz_hour, tz_minute, active_link)


def generic_detail(request, template, humidity_sensor, temp_sensor,
                   start_year, start_month, start_day,
                   start_hour, start_minute, start_second,
                   tz_hour, tz_minute, active_link=None):
    results = prime_results(request, humidity_sensor, temp_sensor)
    start = datetime(int(start_year), int(start_month), int(start_day), int(start_hour), int(start_minute), int(start_second), 0).replace(tzinfo=utc)
    results['active_link'] = active_link
    raw_temps = [x for x in Reading.objects.filter(
                 sensor_id=temp_sensor.id, when__gt=start).order_by('-when')]
    raw_humidities = [x for x in Reading.objects.filter(
                      sensor_id=humidity_sensor.id,
                      when__gt=start).order_by('-when')]

    # XXX this is a little fragile as it assumes there's always matching
    #     entries between temp and humidity readings
    readings = []
    while len(raw_temps) > 0:
        reading = raw_temps.pop()
        try:
            humidity = raw_humidities.pop()
        except:
            # Recycle prior reading
            pass
        reading.humidity = humidity.value
        readings.append(reading)
    results['readings'] = readings
    return render_to_response(template, results)
