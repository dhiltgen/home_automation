# Copyright (c) 2015 Daniel Hiltgen


from django.utils.timezone import utc
from datetime import datetime
from sensor_data.models import Reading


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
    :param multiplier: Optional value to multiply all values by
                       (e.g., converting counters to some well known units)
    """
    base_value = data_range[0].value
    for i in range(len(data_range)):
        data_range[i].raw_value = data_range[i].value
        data_range[i].value = (float(data_range[i].value - base_value)) * \
            multiplier


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
             t1.strftime('%Y-%m-%d')))]
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
             t2.strftime('%Y-%m-%d')))]

    normalize(raw_data, multiplier)
    return raw_data


def get_range(raw_data):
    """
    Given a sensor readings, retrieve the range over that duration

    :param raw_data: The Sensor readings
    :returns: The delta between t1 and t2's values
    """
    try:
        return float(raw_data[-1].value - raw_data[0].value)
    except:
        return float(0.0)


# TODO - This belongs in a separate "rain" module
def get_season_start():
    now = datetime.utcnow().replace(tzinfo=utc)
    now_year = now.year
    now_month = now.month
    rain_season_month_start = 7
    if now_month < rain_season_month_start:
        return datetime(year=now_year - 1,
                        month=rain_season_month_start,
                        day=1, tzinfo=utc)
    else:
        return datetime(year=now_year,
                        month=rain_season_month_start,
                        day=1, tzinfo=utc)
