import logging
from django.contrib.auth.models import Group

from django.contrib.auth.handlers.modwsgi import groups_for_user
from django.db.models import QuerySet
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from sqlparse.engine.grouping import group

from dojoconf.models import Dojo, Classes, Event
from dojoconf.tests.utils import print_form_errors_from_response
from shodan.models import Session


class SessionTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):

        logging.basicConfig(level=logging.INFO)

        # Create a client instance
        self.admin_client = Client()


    def test_admin_cant_choose_both_classes_and_event_fails(self):

        self.admin_client.login(username='admin', password='password')

        # get a dojo, class and event
        dojo = Dojo.objects.first()
        classes = Classes.objects.first()
        event = Event.objects.first()

        # create a session related to a class AND a vent, it should fail
        data = {
            'name': 'test failed session',
            'dojo': dojo.pk,
            'classes': classes.pk,
            'event': event.pk,
            'date': '2024-08-19'
        }

        response = self.admin_client.post(reverse('admin:shodan_session_add'), data)

        self.assertIsNotNone(response.context, "The form validation should have not allowed to choose a class and an event.")
        print_form_errors_from_response(response)
        self.assertEqual(len(response.context['adminform'].errors.items()), 2)

        # Check response status code
        self.assertEqual(response.status_code, 200)

        # Check instance created
        self.assertFalse(Session.objects.filter(name=data['name']).exists())

    def test_admin_must_choose_one_classes_and_event(self):

        self.admin_client.login(username='admin', password='password')

        # get a dojo, class and event
        dojo = Dojo.objects.first()

        # create a session related to a class AND a vent, it should fail
        data = {
            'name': 'test failed session',
            'dojo': dojo.pk,
            'date': '2024-08-19'
        }

        response = self.admin_client.post(reverse('admin:shodan_session_add'), data)

        self.assertIsNotNone(response.context, "The form validation should have not allowed to choose a class and an event.")
        print_form_errors_from_response(response)
        self.assertEqual(len(response.context['adminform'].errors.items()), 2)

        # Check response status code
        self.assertEqual(response.status_code, 200)

        # Check instance created
        self.assertFalse(Session.objects.filter(name=data['name']).exists())

    def test_admin_create_class_from_classes(self):

        self.admin_client.login(username='admin', password='password')

        # get a dojo, class and event
        dojo = Dojo.objects.first()
        classes = Classes.objects.first()

        # create a session related to a class AND a vent, it should fail
        data = {
            'name': 'session from class',
            'classes': classes.pk,
            'dojo': dojo.pk,
            'date': '2024-08-19'
        }

        response = self.admin_client.post(reverse('admin:shodan_session_add'), data)

        if response.context:
            print_form_errors_from_response(response)
            self.assertEqual(len(response.context['adminform'].errors.items()), 0)

        # Check response status code
        self.assertEqual(response.status_code, 302)

        # Check instance created
        self.assertTrue(Session.objects.filter(name=data['name']).exists())
        session: Session = Session.objects.filter(name=data['name']).first()
        self.assertEqual(session.time_from, classes.time_from)
        self.assertEqual(session.time_to, classes.time_to)
        self.assertIsNotNone(session.duration)

    def test_admin_create_class_from_event_no_times_or_duration(self):

        self.admin_client.login(username='admin', password='password')

        # get a dojo, class and event
        dojo = Dojo.objects.first()
        event = Event.objects.first()

        # create a session related to a class AND a vent, it should fail
        data = {
            'name': 'session from class',
            'event': event.pk,
            'dojo': dojo.pk,
            'date': '2024-08-19'
        }

        response = self.admin_client.post(reverse('admin:shodan_session_add'), data)

        self.assertIsNotNone(response.context, "The form validation should have not allowed to create a session without time or duration.")
        print_form_errors_from_response(response)
        self.assertEqual(len(response.context['adminform'].errors.items()), 3)

        # Check response status code
        self.assertEqual(response.status_code, 200)

        # Check instance created
        self.assertFalse(Session.objects.filter(name=data['name']).exists())

    def test_admin_create_class_from_event(self):

        self.admin_client.login(username='admin', password='password')

        # get a dojo, class and event
        dojo = Dojo.objects.first()
        event = Event.objects.first()

        # create a session related to a class AND a vent, it should fail
        data = {
            'name': 'session from class',
            'event': event.pk,
            'dojo': dojo.pk,
            'time_from': '18:00',
            'time_to': '18:30',
            'duration': '0:30',
            'date': '2024-08-19'
        }

        response = self.admin_client.post(reverse('admin:shodan_session_add'), data)

        if response.context:
            print_form_errors_from_response(response)
            self.assertEqual(len(response.context['adminform'].errors.items()), 0)

        # Check response status code
        self.assertEqual(response.status_code, 302)

        # Check instance created
        self.assertTrue(Session.objects.filter(name=data['name']).exists())
        session: Session = Session.objects.filter(name=data['name']).first()
        self.assertIsNotNone(session.time_from)
        self.assertIsNotNone(session.time_to)
        self.assertIsNotNone(session.duration)
