#
from django.utils.timezone import utc
from datetime import datetime, timedelta
from sensor_data.models import Sensor, Reading, Prediction


"""
Generic routines for cumulative sensors (e.g., rain, etc.)

"""


def normalize(data_range, multiplier=1.0):
    """
    Normalize the readings over a given range

    The values will be normalized over the range so that
    the first value in the range is zero, and subsequent values
    will show their delta from the first value

    :param data_range: list of Readings, with offset [0] as the initial value
    :param multiplier: Optional value to multiply all values by (e.g., converting
                       counters to some well known units)
    """
    base_value = data_range[0].value
    for i in range(len(data_range)):
        data_range[i].value = (float(data_range[i].value - base_value)) * multiplier


def get_readings(sensor, t1, t2=None, multiplier=1.0):
    """
    Given a sensor, retrieve the normalized readings from t1 to t2

    :param sensor: The Sensor object to retrieve readings for
    :param t1: The "old" DateTime to retrieve
    :param t2: The optional "new" time to retrieve.  If omitted, all
               readings from t1 to now will be retrieved
    :param multiplier: The value multiplier for unit conversions
    :returns: The normalized sensor readings over the specified range
    """
    if t2 is None:
        raw_data = [x for x in Reading.objects.raw(
            "select distinct on (value) id, value, ts "
            "from sensor_data_reading "
            "where sensor_id=%d and "
            "ts >= to_timestamp('%s', 'YYYY-MM-DD') "
            "order by value, ts asc; " %
            (sensor.id,
             t1.strftime('%Y-%m-%d'),
            ))]
        # Append the very latest reading for completeness in the graph.
        last = Reading.objects.filter(
            sensor_id=sensor.id).order_by('-ts')[:1]
        raw_data.append(last[0])
    else:
        raw_data = [x for x in Reading.objects.raw(
            "select distinct on (value) id, value, ts "
            "from sensor_data_reading "
            "where sensor_id=%d and "
            "ts >= to_timestamp('%s', 'YYYY-MM-DD') "
            "and ts <= to_timestamp('%s', 'YYYY-MM-DD') "
            "order by value, ts asc; " %
            (sensor.id,
             t1.strftime('%Y-%m-%d'),
             t2.strftime('%Y-%m-%d'),
            ))]

    normalize(raw_data, multiplier)
    return raw_data


def get_range(sensor, t1, t2=None):
    """
    Given a sensor, retrieve the range of readings over that duration

    :param sensor: The Sensor object to retrieve readings for
    :param t1: The "old" DateTime to retrieve
    :param t2: The optional "new" time to retrieve.  If omitted, all
               readings from t1 to now will be retrieved
    :returns: The delta between t1 and t2's values
    """
    t1_data = Reading.objects.filter(
        sensor_id=sensor.id).filter(
        ts__gt=t1).order_by('ts')[0]
    if t2 is None:
        t2_data = Reading.objects.filter(
            sensor_id=sensor.id).order_by('-ts')[0]
    else:
        t2_data = Reading.objects.filter(
            sensor_id=sensor.id).filter(
            ts__lt=t2).order_by('-ts')[0]
    return float(t2_data.value - t1_data.value)
