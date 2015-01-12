# Copyright (c) 2013-2015 Daniel Hiltgen

from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from sensor_data.models import Sensor, Reading, Prediction
from datetime import datetime, timedelta
from sensor_data import cumulative
import logging


log = logging.getLogger(__name__)


# TODO
#  A bunch of this should be generalized with some common
#  view classes


def get_start_of_year():
    now = datetime.utcnow().replace(tzinfo=utc)
    now_year = now.year
    return datetime(int(now_year), 1, 1).replace(tzinfo=utc)

def get_humidty_and_temp_sensors(name):
    humidity = Sensor.objects.filter(name=name + " Humidity")[0]
    temp = Sensor.objects.filter(name=name + " Temperature")[0]
    return (humidity, temp)

def common_prime_results(request, sensor):
    results = dict()
    current_reading = Reading.objects.filter(sensor_id=sensor.id).latest('ts')
    results['latest_datetime'] = current_reading.ts
    day = timedelta(days=1)
    week = timedelta(weeks=1)
    year = timedelta(weeks=52)

    results['day_ago_datetime'] = current_reading.ts - day
    results['two_days_ago_datetime'] = current_reading.ts - day - day
    results['week_ago_datetime'] = current_reading.ts - week
    results['year_ago_datetime'] = current_reading.ts - year
    results['year_start_datetime'] = datetime(year=current_reading.ts.year,
                                              month=1, day=1,
                                              tzinfo=current_reading.ts.tzinfo)
    return results


def prime_results(request, humidity_sensor, temp_sensor):
    results = common_prime_results(request, temp_sensor)
    results['temp_sensor'] = temp_sensor
    results['humidity_sensor'] = humidity_sensor
    current_temp = Reading.objects.filter(sensor_id=temp_sensor.id).latest('ts')
    results['current_humidity'] = \
        Reading.objects.filter(sensor_id=humidity_sensor.id).latest('ts')

    results['current_temp'] = current_temp
    return results


def prior_temp(offset, temp_sensor):
    """
    Find the temp readings for this time over the last few days

    :param offset: The number of days ago to retrieve
    :returns: The reading or None
    """
    try:
        res = Reading.objects.raw(
            "select * from sensor_data_reading where "
            "ts >= (now() - interval '%d hours') and "
            "ts <= (now() - interval '%d hours') and "
            "sensor_id=%s order by ts desc limit 1"
            % (offset*24+6, offset*24, temp_sensor.id))[0]
        return res
    except:
        print 'No prior temp for', offset, temp_sensor.id
        return None


def prior_prediction(offset):
    try:
        res = Prediction.objects.raw(
            "select * from sensor_data_prediction where "
            "ts <= (current_date - interval '%d days') and "
            "ts >= (current_date - interval '%d days') "
            "order by ts desc limit 1" %
            (offset, (offset + 1)))[0]
        print offset, res.__dict__
        return res
    except:
        print 'No prior prediction for', offset
        return None


def prior_min_max(offset, sensor):
    try:
        reading = Reading.objects.raw(
            "select min(id) as id, date_trunc('day', ts) as day, min(value) as minimum, max(value) as maximum "
            "from sensor_data_reading "
            "where sensor_id=%d and "
            "ts <=  (current_date - interval '%d days') and "
            "ts >= (current_date - interval '%d days') "
            "group by date_trunc('day', ts) "
            "order by date_trunc('day', ts) desc;" %
            (sensor.id, offset, (offset + 1)))[0]
        return (reading.minimum, reading.maximum)
    except Exception as e:
        print 'Failed to lookup prior min/max', e
        return ("NA", "NA")


def outside_current(request):
    (humidity_sensor, temp_sensor) = get_humidty_and_temp_sensors('Outside')
    return generic_current(request, 'sensor_data/outside_current.html',
                           humidity_sensor, temp_sensor, "outside")


def cellar_current(request):
    (humidity_sensor, temp_sensor) = get_humidty_and_temp_sensors('Cellar')
    return generic_current(request, 'sensor_data/cellar_current.html',
                           humidity_sensor, temp_sensor, "cellar")


def generic_current(request, template, humidity_sensor, temp_sensor, group):
    results = prime_results(request, humidity_sensor, temp_sensor)
    results['group'] = group
    results['active_link'] = 'current'

    try:
        results['prediction'] = Prediction.objects.latest('ts')
    except Exception as e:
        log.exception("No predictions available: %e", e)
        results['prediction'] = None

    # TODO:
    # Prediction confidence (+/- based on accuracy over the last week)

    # TODO - Add humidity
    past = []
    for i in range(0, 4):
        past_day = dict()
        if i == 0:
            past_day['label'] = "Today"
        elif i == 1:
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


def outside_summary(request, days=None):
    (humidity_sensor, temp_sensor) = get_humidty_and_temp_sensors('Outside')
    return generic_summary(request, 'sensor_data/outside_summary.html',
                           humidity_sensor, temp_sensor, "outside", days)


def cellar_summary(request, days=None):
    (humidity_sensor, temp_sensor) = get_humidty_and_temp_sensors('Cellar')
    return generic_summary(request, 'sensor_data/cellar_summary.html',
                           humidity_sensor, temp_sensor, "cellar", days)


def generic_summary(request, template, humidity_sensor, temp_sensor, group, days):
    results = prime_results(request, humidity_sensor, temp_sensor)
    results['group'] = group
    if days:
        days = int(days)
        start = datetime.utcnow().replace(tzinfo=utc) - timedelta(days)
        if days == 1:
            active_link = '24'
        elif days == 2:
            active_link = '48'
        elif days <= 7:
            active_link = 'week'
        elif days > 7:
            active_link = 'year'
    else:
        start = get_start_of_year()
        active_link = 'ytd'

    results['active_link'] = active_link

    # TODO
    #  May want to refactor this so min/max are distinct sensors so the
    #  timestamps are more accurate

    raw_temps = [x for x in Reading.objects.raw(
        "select min(id) as id, date_trunc('day', ts) as day, min(value) as minimum, max(value) as maximum "
        "from sensor_data_reading "
        "where sensor_id=%d and "
        "ts >= to_timestamp('%s', 'YYYY-MM-DD') "
        "group by date_trunc('day', ts) "
        "order by date_trunc('day', ts) desc;" %
        (temp_sensor.id, start.strftime('%Y-%m-%d')))]
    raw_humidities = [x for x in Reading.objects.raw(
        "select min(id) as id, date_trunc('day', ts) as day, min(value) as minimum, max(value) as maximum "
        "from sensor_data_reading "
        "where sensor_id=%d and "
        "ts >= to_timestamp('%s', 'YYYY-MM-DD') "
        "group by date_trunc('day', ts) "
        "order by date_trunc('day', ts) desc;" %
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
        if readings and readings[-1].day == reading.day:
            # The query above may yield duplicates if more than one
            # readhing throughout the day matches the min/max, so discard them
            continue
        readings.append(reading)
    results['readings'] = readings
    return render_to_response(template, results)


def outside_detail(request, days):
    (humidity_sensor, temp_sensor) = get_humidty_and_temp_sensors('Outside')
    return generic_detail(request, 'sensor_data/outside_detail.html',
                          humidity_sensor, temp_sensor, "outside", days)


def cellar_detail(request, days):
    (humidity_sensor, temp_sensor) = get_humidty_and_temp_sensors('Cellar')
    return generic_detail(request, 'sensor_data/cellar_detail.html',
                          humidity_sensor, temp_sensor, "cellar", days)


def generic_detail(request, template, humidity_sensor, temp_sensor, group, days):
    results = prime_results(request, humidity_sensor, temp_sensor)
    results['group'] = group
    days = int(days)
    start = datetime.utcnow().replace(tzinfo=utc) - timedelta(days)
    if days == 1:
        active_link = '24'
    elif days == 2:
        active_link = '48'
    elif days <= 7:
        active_link = 'week'
    elif days > 7:
        active_link = 'year'
    results['active_link'] = active_link
    raw_temps = [x for x in Reading.objects.filter(
        sensor_id=temp_sensor.id, ts__gt=start).order_by('-ts')]
    raw_humidities = [x for x in Reading.objects.filter(
                      sensor_id=humidity_sensor.id,
                      ts__gt=start).order_by('-ts')]

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


def rain_ytd(request):
    return rain_common(request, get_start_of_year(), "ytd")


def rain_data(request, days=None):
    if days:
        days = int(days)
        start = datetime.utcnow().replace(tzinfo=utc) - timedelta(days)
        if days == 1:
            active_link = '24'
        elif days <= 7:
            active_link = 'week'
        elif days > 7:
            active_link = 'year'
    else:
        active_link = "season"
        start = cumulative.get_season_start()

    return rain_common(request, start, active_link)


def rain_common(request, start, active_link):
    sensor = Sensor.objects.filter(name='Rainfall')[0]
    results = common_prime_results(request, sensor)
    results['group'] = "rain"

    results['active_link'] = active_link
    """
    select distinct on (value) id, value, ts
    from sensor_data_reading
    where sensor_id=6 and ts >= to_timestamp('2014-11-20', 'YYYY-MM-DD')
    order by value, ts asc;
    """
    raw_data = cumulative.get_readings(sensor, start, None, 0.01)
    total = cumulative.get_range(raw_data)
    results['total'] = total

    if len(raw_data) == 1:
        results['readings'] = []
        results['last_rain'] = 'NA in this interval'
        return render_to_response('sensor_data/rain.html', results)

    # Get the first occurrence of the latest reading (time of last rain)
    last_bump = Reading.objects.filter(
        sensor_id=sensor.id).filter(
        value=raw_data[-1].raw_value).earliest('ts')
    last_rain = datetime.utcnow().replace(tzinfo=utc) - last_bump.ts
    if last_rain.days:
        results['last_rain'] = '%d days %d hours ago' \
            % (last_rain.days, last_rain.seconds/(60*60))
    else:
        results['last_rain'] = '%d hours ago' % (last_rain.seconds/(60*60))
    results['readings'] = raw_data

    return render_to_response('sensor_data/rain.html', results)
