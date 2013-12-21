from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from sensor_data.models import Sensor, Reading, Prediction
from datetime import datetime, timedelta

def prime_results(request):
    results = dict()
    humidity_sensor = Sensor.objects.filter(name='Outside Humidity')[0]
    temp_sensor = Sensor.objects.filter(name='Outside Temperature')[0]
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

def prior_temp(offset):
    """
    Find the temp readings for this time over the last few days

    :param count: The number of days ago to retrieve
    :returns: The reading or None
    """
    temp_sensor = Sensor.objects.filter(name='Outside Temperature')[0]
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

def prior_min_max(offset):
    temp_sensor = Sensor.objects.filter(name='Outside Temperature')[0]
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
    results = prime_results(request)
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
            past_day['at_this_time'] = prior_temp(i).value
        except:
            past_day['at_this_time'] = 'NA'
        prediction = prior_prediction(i)
        if prediction:
            past_day['min_prediction'] = prediction.min1
            past_day['max_prediction'] = prediction.max1
        else:
            past_day['min_prediction'] = 'NA'
            past_day['max_prediction'] = 'NA'
        (past_day['min_actual'], past_day['max_actual']) = prior_min_max(i)
        past.append(past_day)
    results['past'] = past


    return render_to_response('sensor_data/outside_current.html', results)

def outside_summary(request, start_year, start_month, start_day,
                   start_hour, start_minute, start_second,
                   tz_hour, tz_minute, active_link=None):
    results = prime_results(request)
    start = datetime(int(start_year), int(start_month), int(start_day), int(start_hour), int(start_minute), int(start_second), 0).replace(tzinfo=utc)


    results['active_link'] = active_link
    results['readings'] = Reading.objects.raw(
        "select cast(`when` as date), min(value) as minimum, "
        "max(value) as maximum, id, sensor_id "
        "from sensor_data_reading where sensor_id='%s' and "
        "`when` >= '%s' "
        "group by 1 order by 1" %
        (results['temp_sensor'].id, start.strftime('%Y-%m-%d %H:%M:%S')))
    return render_to_response('sensor_data/outside_summary.html', results)

def outside_detail(request, start_year, start_month, start_day,
                   start_hour, start_minute, start_second,
                   tz_hour, tz_minute, active_link=None):
    humidity_sensor = Sensor.objects.filter(name='Outside Humidity')[0]
    temp_sensor = Sensor.objects.filter(name='Outside Temperature')[0]
    results = prime_results(request)
    start = datetime(int(start_year), int(start_month), int(start_day), int(start_hour), int(start_minute), int(start_second), 0).replace(tzinfo=utc)
    results['active_link'] = active_link
    results['readings'] = Reading.objects.filter(sensor_id=temp_sensor.id,
                                                 when__gt=start)
    return render_to_response('sensor_data/outside_detail.html', results)
