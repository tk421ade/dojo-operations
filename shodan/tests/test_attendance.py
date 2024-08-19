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
from shodan.models import Session, Student, Attendance


class AttendanceTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):

        logging.basicConfig(level=logging.INFO)

        # Create a client instance
        self.admin_client = Client()




    def test_attendance(self):

        self.admin_client.login(username='admin', password='password')

        # create a session
        dojo = Dojo.objects.first()
        classes = Classes.objects.first()
        data = {
            'name': 'session for attendance',
            'classes': classes.pk,
            'dojo': dojo.pk,
            'date': '2024-08-19'
        }
        response = self.admin_client.post(reverse('admin:shodan_session_add'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Session.objects.filter(name=data['name']).exists())
        session = Session.objects.filter(name=data['name']).first()

        # create a student
        data = {
            'dojo': dojo.pk,
            'status': 'active',
            'name': 'Bartolome Segui',
            'email': 'bartolome@segui.com',
            'kyu': '10'
        }
        response = self.admin_client.post(reverse('admin:shodan_student_add'), data)
        print_form_errors_from_response(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Student.objects.filter(name=data['name']).exists())
        student = Student.objects.filter(name=data['name']).first()
        pre_hours = student.hours

        # create attendance

        data = {
            'student': student.pk,
            'session': session.pk,
            'dojo': dojo.pk,
            'date': '2024-08-19'
        }

        response = self.admin_client.post(reverse('admin:shodan_attendance_add'), data)

        if response.context:
            print_form_errors_from_response(response)
            self.assertEqual(len(response.context['adminform'].errors.items()), 0)

        # Check response status code
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Attendance.objects.filter(
            student=student.pk,
            session=session.pk
        ).exists())

        # make sure that the hours has been added
        student = Student.objects.filter(id=student.pk).first()
        self.assertNotEqual(student.hours, pre_hours)