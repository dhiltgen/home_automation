# Copyright (c) 2015 Daniel Hiltgen

from django.test import TestCase
from django.test import Client
from django.test.utils import setup_test_environment
from sensor_data.models import Sensor, Reading, Prediction
from datetime import datetime
from django.utils.timezone import utc


class SensorViewTest(TestCase):
    def setUp(self):
        setup_test_environment()
        self.client = Client()

        # Add Sensors to the DB
        # TODO - this should be from some config metadata...
        ohs = Sensor(name='Outside Humidity',
                     server="sensors:4304",
                     device="26.C29821010000",
                     sensor_type="H",
                     units="percent",
                     subsensor="humidity")
        ohs.save()
        ots = Sensor(name='Outside Temperature',
                     server="sensors:4304",
                     device="26.C29821010000",
                     sensor_type="T",
                     units="fahrenheit",
                     subsensor="temperature")
        ots.save()
        chs = Sensor(name='Cellar Humidity',
                     server="sensors:4304",
                     device="26.489A21010000",
                     sensor_type="H",
                     units="percent",
                     subsensor="humidity")
        chs.save()
        cts = Sensor(name='Cellar Temperature',
                     server="sensors:4304",
                     device="26.489A21010000",
                     sensor_type="T",
                     units="fahrenheit",
                     subsensor="temperature")
        cts.save()
        rs = Sensor(name='Rainfall',
                    server="sensors:4304",
                    device="1D.3ACA0F000000",
                    sensor_type="R",
                    units="counter",
                    subsensor="counters.B")
        rs.save()

        now = datetime.now().replace(tzinfo=utc)
        # Add some dummy data
        Reading(sensor=ohs,
                ts=now,
                value=1.0).save()
        Reading(sensor=ots,
                ts=now,
                value=2.0).save()
        Reading(sensor=chs,
                ts=now,
                value=3.0).save()
        Reading(sensor=cts,
                ts=now,
                value=4.0).save()
        Reading(sensor=rs,
                ts=now,
                value=5.0).save()


    def test_outside(self):
        response = self.client.get('/outside')
        assert response.status_code == 200
        assert isinstance(response.context, list)
        assert '<title>Home Automation</title>' in response.content

    def test_outside_detail_one(self):
        response = self.client.get('/outside/detail/1')
        assert response.status_code == 200
        assert isinstance(response.context, list)
        assert '<title>Home Automation</title>' in response.content

    def test_outside_summary_one(self):
        response = self.client.get('/outside/summary/1')
        assert response.status_code == 200
        assert isinstance(response.context, list)
        assert '<title>Home Automation</title>' in response.content

    def test_cellar(self):
        response = self.client.get('/cellar')
        assert response.status_code == 200
        assert isinstance(response.context, list)
        assert '<title>Home Automation</title>' in response.content

    def test_cellar_detail_one(self):
        response = self.client.get('/cellar/detail/1')
        assert response.status_code == 200
        assert isinstance(response.context, list)
        assert '<title>Home Automation</title>' in response.content

    def test_cellar_summary_one(self):
        response = self.client.get('/cellar/summary/1')
        assert response.status_code == 200
        assert isinstance(response.context, list)
        assert '<title>Home Automation</title>' in response.content

    def test_rain(self):
        response = self.client.get('/rain')
        assert response.status_code == 200
        assert isinstance(response.context, list)
        assert '<title>Home Automation</title>' in response.content

    def test_rain_one(self):
        response = self.client.get('/rain/1')
        assert response.status_code == 200
        assert isinstance(response.context, list)
        assert '<title>Home Automation</title>' in response.content
