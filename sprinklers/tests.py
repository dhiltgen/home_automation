# Copyright (c) 2015 Daniel Hiltgen

from django.test import TestCase
from django.test import Client
from django.test.utils import setup_test_environment


class SprinklerViewTest(TestCase):
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

    # TODO - Add some more tests for manipulating individual sprinklers
