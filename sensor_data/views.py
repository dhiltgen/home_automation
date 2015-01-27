# Copyright (c) 2013-2015 Daniel Hiltgen

from datetime import datetime, timedelta
from django.shortcuts import render_to_response
from django.utils.timezone import utc
from django.views.generic import View
from sensor_data import cumulative, statistics
from sensor_data.models import Sensor, Reading, Prediction
import logging


log = logging.getLogger(__name__)


class CommonView(View):
    # Override for specific sensors
    TEMPLATE = None
    GROUP = None
    SMOOTHING = 0.2

    def smooth(self, data):
        """
        Given a series of sensor data, use exponential smoothing
        """
        for i in range(1, len(data)):
            data[i].value = self.SMOOTHING * float(data[i].value) + \
                (1 - self.SMOOTHING) * float(data[i-1].value)

    def common_prime_results(self, request, sensor):
        results = dict()
        current_reading = Reading.objects.filter(
            sensor_id=sensor.id).latest('ts')
        results['latest_datetime'] = current_reading.ts
        day = timedelta(days=1)
        week = timedelta(weeks=1)
        year = timedelta(weeks=52)

        results['day_ago_datetime'] = current_reading.ts - day
        results['two_days_ago_datetime'] = current_reading.ts - day - day
        results['week_ago_datetime'] = current_reading.ts - week
        results['year_ago_datetime'] = current_reading.ts - year
        results['year_start_datetime'] = datetime(
            year=current_reading.ts.year, month=1, day=1,
            tzinfo=current_reading.ts.tzinfo)
        return results


class TempHumidityView(CommonView):
    # Override for specific sensors
    TEMP_SENSOR_NAME = None
    HUMIDITY_SENSOR_NAME = None
    PREDICTIONS = None

    def get_sensors(self):
        temp_sensor = Sensor.objects.filter(name=self.TEMP_SENSOR_NAME)[0]
        humidity_sensor = Sensor.objects.filter(
            name=self.HUMIDITY_SENSOR_NAME)[0]
        return (temp_sensor, humidity_sensor)

    def prime_results(self, request, humidity_sensor, temp_sensor):
        results = self.common_prime_results(request, temp_sensor)
        results['temp_sensor'] = temp_sensor
        results['humidity_sensor'] = humidity_sensor
        current_temp = Reading.objects.filter(
            sensor_id=temp_sensor.id).latest('ts')
        results['current_humidity'] = \
            Reading.objects.filter(sensor_id=humidity_sensor.id).latest('ts')

        results['current_temp'] = current_temp
        results['group'] = self.GROUP
        return results

    def get_start(self, results, days):
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
            now = datetime.utcnow().replace(tzinfo=utc)
            now_year = now.year
            start = datetime(int(now_year), 1, 1).replace(tzinfo=utc)
            active_link = 'ytd'
        results['active_link'] = active_link
        return start

    def get_prediction(self, when):
        try:
            res = Prediction.objects.raw(
                "select * from sensor_data_prediction "
                "where ts < '%s' "
                "order by ts desc "
                "limit 1" %
                (when))[0]
            #print when, res.__dict__
            return res
        except Exception as e:
            print 'No prior prediction for', when, e
            return None


class TempHumidityCurrent(TempHumidityView):
    def prior_temp(self, offset, temp_sensor):
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

    def prior_prediction(self, offset):
        try:
            res = Prediction.objects.raw(
                "select * from sensor_data_prediction where "
                "ts <= (current_date - interval '%d days') and "
                "ts >= (current_date - interval '%d days') "
                "order by ts desc limit 1" %
                (offset, (offset + 1)))[0]
            #print offset, res.__dict__
            return res
        except:
            print 'No prior prediction for', offset
            return None

    def prior_min_max(self, offset, sensor):
        try:
            reading = Reading.objects.raw(
                "select min(id) as id, date_trunc('day', ts) as day, "
                "min(value) as minimum, max(value) as maximum "
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

    def get(self, request):
        (temp_sensor, humidity_sensor) = self.get_sensors()
        results = self.prime_results(request, humidity_sensor, temp_sensor)
        results['active_link'] = 'current'

        if self.PREDICTIONS:
            try:
                results['prediction'] = Prediction.objects.latest('ts')

                # Prediction confidence (+/- based on accuracy over interval)
                # we'll use a trailing 30 day sample to determine accuracy
                pred_range = 30
                results['stdev_interval'] = pred_range
                interval = range(1, pred_range)
                predictions = [self.prior_prediction(i) for i in interval]
                min_maxs = [self.prior_min_max(i, temp_sensor)
                            for i in interval]
                min_deltas = [float(predictions[i].min1) - float(min_maxs[i][0])
                              for i in range(len(predictions))
                              if predictions[i] and min_maxs[i]]
                max_deltas = [float(predictions[i].max1) - float(min_maxs[i][1])
                              for i in range(len(predictions))
                              if predictions[i] and min_maxs[i]]
                min_delta_mean = statistics.mean(min_deltas)
                max_delta_mean = statistics.mean(max_deltas)
                min_stdev = statistics.pstdev(min_deltas)
                max_stdev = statistics.pstdev(max_deltas)
                results['min_prediction_stdev'] = min_stdev
                results['max_prediction_stdev'] = max_stdev

                # Update the prediction with ranges
                pred = results['prediction']
                for i in range(1,8):
                    if 'min%d' % (i) in pred.__dict__:
                        pred.__dict__["min%d_low" % (i)] = \
                            (float(pred.__dict__["min%d" % (i)]) -
                             min_delta_mean - min_stdev)
                        pred.__dict__["min%d_high" % (i)] = \
                            (float(pred.__dict__["min%d" % (i)]) -
                             min_delta_mean + min_stdev)
                    if 'max%d' % (i) in pred.__dict__:
                        pred.__dict__["max%d_low" % (i)] = \
                            (float(pred.__dict__["max%d" % (i)]) -
                             max_delta_mean - max_stdev)
                        pred.__dict__["max%d_high" % (i)] = \
                            (float(pred.__dict__["max%d" % (i)]) -
                             max_delta_mean + max_stdev)
            except Exception as e:
                log.exception("No predictions available: %e", e)
                results['prediction'] = None


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
                past_day['at_this_time'] = self.prior_temp(
                    i, temp_sensor).value
            except:
                past_day['at_this_time'] = 'NA'

            if self.PREDICTIONS:
                prediction = self.prior_prediction(i)
            else:
                prediction = None
            if prediction:
                past_day['min_prediction'] = prediction.min1
                past_day['max_prediction'] = prediction.max1
            else:
                past_day['min_prediction'] = 'NA'
                past_day['max_prediction'] = 'NA'
            (past_day['min_actual'], past_day['max_actual']) = \
                self.prior_min_max(i, temp_sensor)
            past.append(past_day)
        results['past'] = past

        return render_to_response(self.TEMPLATE, results)


class TempHumiditySummary(TempHumidityView):
    # Override for specific sensors
    TEMPLATE = None
    TEMP_SENSOR_NAME = None
    HUMIDITY_SENSOR_NAME = None
    GROUP = None
    PREDICTIONS = None

    def get(self, request, days=None):
        (temp_sensor, humidity_sensor) = self.get_sensors()
        results = self.prime_results(request, humidity_sensor, temp_sensor)
        start = self.get_start(results, days)

        # TODO
        #  May want to refactor this so min/max are distinct sensors so the
        #  timestamps are more accurate

        raw_temps = [x for x in Reading.objects.raw(
            "select min(id) as id, date_trunc('day', ts) as day, "
            "min(value) as minimum, max(value) as maximum "
            "from sensor_data_reading "
            "where sensor_id=%d and "
            "ts >= to_timestamp('%s', 'YYYY-MM-DD') "
            "group by date_trunc('day', ts) "
            "order by date_trunc('day', ts) desc;" %
            (temp_sensor.id, start.strftime('%Y-%m-%d')))]
        raw_humidities = [x for x in Reading.objects.raw(
            "select min(id) as id, date_trunc('day', ts) as day, "
            "min(value) as minimum, max(value) as maximum "
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
            if self.PREDICTIONS:
                prediction = self.get_prediction(reading.ts)
                # TODO - validate the timestamp is right (~1 day before)
                if prediction:
                    reading.predicted_minimum = prediction.min1
                    reading.predicted_maximum = prediction.max1
            reading.humidity_minimum = humidity.minimum
            reading.humidity_maximum = humidity.maximum
            if readings and readings[-1].day == reading.day:
                # The query above may yield duplicates if more than one
                # readhing throughout the day matches the min/max,
                # so discard them
                continue
            readings.append(reading)

        results['readings'] = readings
        return render_to_response(self.TEMPLATE, results)


class TempHumidityDetail(TempHumidityView):
    # Override for specific sensors
    TEMPLATE = None
    TEMP_SENSOR_NAME = None
    HUMIDITY_SENSOR_NAME = None
    GROUP = None
    PREDICTIONS = None

    def get(self, request, days):
        (temp_sensor, humidity_sensor) = self.get_sensors()
        results = self.prime_results(request, humidity_sensor, temp_sensor)
        start = self.get_start(results, days)

        raw_temps = [x for x in Reading.objects.filter(
            sensor_id=temp_sensor.id, ts__gt=start).order_by('-ts')]
        raw_humidities = [x for x in Reading.objects.filter(
                          sensor_id=humidity_sensor.id,
                          ts__gt=start).order_by('-ts')]

        self.smooth(raw_temps)
        self.smooth(raw_humidities)
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
        return render_to_response(self.TEMPLATE, results)


# TODO - drive these from configuration instead of hard-coding
#        so additional sensors can be added "on the fly" via conf
class OutsideCurrent(TempHumidityCurrent):
    TEMPLATE = 'sensor_data/outside_current.html'
    TEMP_SENSOR_NAME = 'Outside Temperature'
    HUMIDITY_SENSOR_NAME = 'Outside Humidity'
    GROUP = 'outside'
    PREDICTIONS = True


class CellarCurrent(TempHumidityCurrent):
    TEMPLATE = 'sensor_data/cellar_current.html'
    TEMP_SENSOR_NAME = 'Cellar Temperature'
    HUMIDITY_SENSOR_NAME = 'Cellar Humidity'
    GROUP = 'cellar'


class OutsideSummary(TempHumiditySummary):
    TEMPLATE = 'sensor_data/outside_summary.html'
    TEMP_SENSOR_NAME = 'Outside Temperature'
    HUMIDITY_SENSOR_NAME = 'Outside Humidity'
    GROUP = 'outside'
    PREDICTIONS = True


class CellarSummary(TempHumiditySummary):
    TEMPLATE = 'sensor_data/cellar_summary.html'
    TEMP_SENSOR_NAME = 'Cellar Temperature'
    HUMIDITY_SENSOR_NAME = 'Cellar Humidity'
    GROUP = 'cellar'


class OutsideDetail(TempHumidityDetail):
    TEMPLATE = 'sensor_data/outside_detail.html'
    TEMP_SENSOR_NAME = 'Outside Temperature'
    HUMIDITY_SENSOR_NAME = 'Outside Humidity'
    GROUP = 'outside'
    PREDICTIONS = True


class CellarDetail(TempHumidityDetail):
    TEMPLATE = 'sensor_data/cellar_detail.html'
    TEMP_SENSOR_NAME = 'Cellar Temperature'
    HUMIDITY_SENSOR_NAME = 'Cellar Humidity'
    GROUP = 'cellar'


# TODO - Convert rain into a view
def rain_ytd(request):
    now = datetime.utcnow().replace(tzinfo=utc)
    now_year = now.year
    start_of_year = datetime(int(now_year), 1, 1).replace(tzinfo=utc)
    return rain_common(request, start_of_year, "ytd")


def rain_data(request, days=None):
    if days:
        days = int(days)
        start = datetime.utcnow().replace(tzinfo=utc) - timedelta(days)
        if days == 1:
            active_link = '24'
        elif days <= 7:
            active_link = 'week'
        elif days == 30:
            active_link = '30d'
        elif days == 60:
            active_link = '60d'
        elif days == 90:
            active_link = '90d'
        else:
            active_link = None
    else:
        active_link = "season"
        start = cumulative.get_season_start()

    return rain_common(request, start, active_link)


def rain_common(request, start, active_link):
    sensor = Sensor.objects.filter(name='Rainfall')[0]
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
    results['group'] = "rain"

    results['active_link'] = active_link
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
