# Copyright (c) 2015 Daniel Hiltgen

from django.test import TestCase
from django.test import Client
from django.test.utils import setup_test_environment
from django.utils.timezone import utc
from sprinklers.models import Circuit, WateringEvent, poll, WateringTime
from mock import patch
from datetime import timedelta, datetime
from sensor_data.models import Sensor, Reading


def dummy_circuits():
    """
    Set up some dummy circuits for test purposes
    """
    c = Circuit(path="1",
                label="Circuit 1 Label",
                volume_label="inches",
                target_wk=1.5,
                rate_hr=2.5)
    c.save()

    c = Circuit(path="2",
                label="Circuit 2 Label",
                volume_label="inches",
                target_wk=4.0,
                rate_hr=3.0)
    c.save()

    rs = Sensor(name='Rainfall',
                server="sensors:4304",
                device="1D.3ACA0F000000",
                sensor_type="R",
                units="counter",
                subsensor="counters.B")
    rs.save()


class SprinklerViewBlankSlateTest(TestCase):
    """
    Test Sprinkler without circuits
    """
    def setUp(self):
        setup_test_environment()
        self.client = Client()

    def test_root(self):
        response = self.client.get('/')
        assert response.status_code == 200
        assert 'circuits' in response.context
        assert 'sensors' in response.context
        assert 'prediction' in response.context
        assert '<title>Home Automation</title>' in response.content

    def test_circuits(self):
        response = self.client.get('/circuits/')
        assert response.status_code == 200
        assert 'circuits' in response.context
        assert len(response.context['circuits']) == 0
        assert '<title>Home Automation</title>' in response.content


class SprinklerViewTest(TestCase):
    """
    Test Sprinkler with circuits
    """
    def setUp(self):
        setup_test_environment()
        self.client = Client()
        dummy_circuits()

    def test_circuits(self):
        response = self.client.get('/circuits/')
        assert response.status_code == 200
        assert 'circuits' in response.context
        assert len(response.context['circuits']) == 2
        assert '<title>Home Automation</title>' in response.content

    @patch("sprinklers.models.backend.stop", new=lambda x: None)
    @patch("sprinklers.models.backend.start", new=lambda x: None)
    def test_watering(self):
        circuits = Circuit.objects.all().order_by("label")
        assert len(circuits) > 0
        response = self.client.post('/circuits/%d/update/' % (circuits[0].id),
                                    {'action': 'start'})
        assert response.status_code == 302

        events = WateringEvent.objects.filter(circuit=circuits[0].id)
        assert len(events) == 1
        assert events[0].volume == 0.0

        # Dummy up the event to have started in the past
        # so we can get a non-zero volume calculation
        events[0].time = events[0].time - timedelta(minutes=30)
        events[0].save()

        # Now stop the sprinkler
        response = self.client.post('/circuits/%d/update/' % (circuits[0].id),
                                    {'action': 'stop'})
        assert response.status_code == 302

        # Check that the event was updated, and the volume looks plausible
        events = WateringEvent.objects.filter(circuit=circuits[0].id)
        assert len(events) == 1
        assert events[0].volume != 0.0

    def start_watering_in_past(self, circuit, minutes):
        """
        Dummy up the events so it looks like we started watering
        in the past
        """
        circuit.start_watering()
        event = WateringEvent.objects.filter(circuit=circuit.id).order_by(
            "-time")[0]
        event.save()
        event.time = event.time - timedelta(minutes=minutes)
        event.save()

    def add_window_now(self):
        now = datetime.utcnow().replace(tzinfo=utc)
        buf = timedelta(minutes=1)
        window = WateringTime(weekday=now.weekday(),
                              start_time=(now-buf).time(),
                              end_time=(now+buf).time())
        window.save()
        return window

    @patch("sprinklers.models.backend.stop", new=lambda x: None)
    @patch("sprinklers.models.backend.start", new=lambda x: None)
    def test_poll_max_time_not_ok_to_start(self):
        import sprinklers.circuit_backend
        circuits = Circuit.objects.all().order_by("label")
        assert len(circuits) == 2
        self.start_watering_in_past(circuits[0], 46)

        def get_state(path):
            if path == "1":
                return 1
            return 0
        orig = sprinklers.circuit_backend.get_state
        sprinklers.circuit_backend.get_state = get_state
        try:
            poll()
            circuits = Circuit.objects.all().order_by("label")
            assert not circuits[0].current_state, \
                "Didn't stop running sprinkler"
            assert not circuits[1].current_state, \
                "Started other sprinkler out of window"
        finally:
            sprinklers.circuit_backend.get_state = orig

    @patch("sprinklers.models.backend.stop", new=lambda x: None)
    @patch("sprinklers.models.backend.start", new=lambda x: None)
    @patch("sprinklers.models.backend.get_state", new=lambda x: 0)
    def test_poll_overwatered(self):
        window = self.add_window_now()
        circuits = Circuit.objects.all().order_by("label")
        assert len(circuits) == 2
        event = WateringEvent(circuit=circuits[0],
                              volume=str(float(circuits[0].target_wk) * 2))
        event.save()
        event = WateringEvent(circuit=circuits[1],
                              volume=str(float(circuits[1].target_wk) * 2))
        event.save()
        poll()
        window.delete()
        circuits = Circuit.objects.all().order_by("label")
        assert not circuits[0].current_state, \
            "Started 1st sprinkler when overwatered"
        assert not circuits[1].current_state, \
            "Started 2nd sprinkler when overwatered"

    @patch("sprinklers.models.backend.stop", new=lambda x: None)
    @patch("sprinklers.models.backend.start", new=lambda x: None)
    @patch("sprinklers.models.backend.get_state", new=lambda x: 0)
    def test_poll_all_overwatered(self):
        window = self.add_window_now()
        circuits = Circuit.objects.all().order_by("label")
        assert len(circuits) == 2
        event = WateringEvent(circuit=circuits[0],
                              volume=str(float(circuits[0].target_wk) * 2))
        event.save()
        poll()
        window.delete()
        circuits = Circuit.objects.all().order_by("label")
        assert not circuits[0].current_state, \
            "Started sprinkler when overwatered"
        assert circuits[1].current_state, \
            "Failed to start other sprinkler"

    @patch("sprinklers.models.backend.stop", new=lambda x: None)
    @patch("sprinklers.models.backend.start", new=lambda x: None)
    @patch("sprinklers.models.backend.get_state", new=lambda x: 0)
    def test_poll_too_recent(self):
        now = datetime.utcnow().replace(tzinfo=utc)
        window = self.add_window_now()
        circuits = Circuit.objects.all().order_by("label")
        assert len(circuits) == 2
        event = WateringEvent(circuit=circuits[0],
                              volume=str(float(circuits[0].target_wk)))
        event.save()
        event.time = now - timedelta(minutes=1)
        event.save()
        event = WateringEvent(circuit=circuits[1],
                              volume=str(float(circuits[1].target_wk)))
        event.save()
        event.time = now - timedelta(hours=96)
        event.save()
        poll()
        window.delete()
        circuits = Circuit.objects.all().order_by("label")
        assert not circuits[0].current_state, \
            "Started sprinkler when too recent"
        assert circuits[1].current_state, \
            "Failed to start other sprinkler"

    @patch("sprinklers.models.backend.stop", new=lambda x: None)
    @patch("sprinklers.models.backend.start", new=lambda x: None)
    def test_poll_more_time(self):
        import sprinklers.circuit_backend
        circuits = Circuit.objects.all().order_by("label")
        assert len(circuits) == 2
        self.start_watering_in_past(circuits[0], 1)
        assert circuits[0].current_state, "Didn't start"

        def get_state(path):
            if path == "1":
                return 1
            return 0
        orig = sprinklers.circuit_backend.get_state
        sprinklers.circuit_backend.get_state = get_state
        try:
            poll()
            print circuits
            circuits = Circuit.objects.all().order_by("label")
            print circuits
            assert circuits[0].current_state, \
                "Didn't leave sprinkler running"
            assert not circuits[1].current_state, \
                "Started other sprinkler"
        finally:
            sprinklers.circuit_backend.get_state = orig

    @patch("sprinklers.models.backend.stop", new=lambda x: None)
    @patch("sprinklers.models.backend.start", new=lambda x: None)
    def test_poll_enough_time(self):
        print 'XXX enough_time'
        window = self.add_window_now()
        import sprinklers.circuit_backend
        circuits = Circuit.objects.all().order_by("label")
        assert len(circuits) == 2
        cycle_count_goal = 3
        cycle_length_goal = float(circuits[0].target_wk) / \
            float(circuits[0].rate_hr) / cycle_count_goal * 60
        self.start_watering_in_past(circuits[0], int(cycle_length_goal) + 1)
        assert circuits[0].current_state, "Didn't start"

        def get_state(path):
            if path == "1":
                return 1
            return 0
        orig = sprinklers.circuit_backend.get_state
        sprinklers.circuit_backend.get_state = get_state
        try:
            poll()
            window.delete()
            circuits = Circuit.objects.all().order_by("label")
            assert not circuits[0].current_state, \
                "Didn't stop sprinkler"
            assert circuits[1].current_state, \
                "Didn't start other sprinkler"
        finally:
            sprinklers.circuit_backend.get_state = orig
            print 'XXX enough_time done'

    def test_poll_recent_rain(self):
        window = self.add_window_now()
        sensor = Sensor.objects.filter(name='Rainfall')[0]
        now = datetime.utcnow().replace(tzinfo=utc)
        reading = Reading(sensor=sensor, ts=now, value=10000)
        reading.save()
        reading = Reading(sensor=sensor, ts=now-timedelta(hours=1),
                          value=1)
        reading.save()
        circuits = Circuit.objects.all().order_by("label")
        assert len(circuits) == 2
        poll()
        window.delete()
        circuits = Circuit.objects.all().order_by("label")
        assert not circuits[0].current_state, \
            "Failed to detect rain"
        assert not circuits[1].current_state, \
            "Failed to detect rain"
