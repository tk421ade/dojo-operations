import base64
import logging
from datetime import date

from django.test import TestCase, Client
from django.urls import reverse

from dojoconf.models import Dojo, Classes, Address
from shodan.models import Student, Session, Attendance, StudentWaiver
from shodan.service import get_or_create_today_sessions, WEEKDAY_NAMES

MINIMAL_PNG_DATA_URL = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='


def _valid_waiver_form_data(email='newstudent@test.com', dob='2000-01-15'):
    return {
        'email2': '',
        'first_name': 'John',
        'last_name': 'Test',
        'address': '123 Test Street',
        'suburb': 'Testville',
        'state': 'SA',
        'post_code': '5000',
        'phone': '0412345678',
        'email': email,
        'date_of_birth': dob,
        'current_grade': '10kyu',
        'emergency_contact_name': 'Jane Test',
        'emergency_contact_relationship': 'Parent',
        'emergency_contact_phone': '0487654321',
        'terms_accepted': 'on',
        'q1': 'no', 'q2': 'no', 'q3': 'no', 'q4': 'no',
        'q5': 'no', 'q6': 'no', 'q7': 'no', 'q8': 'no',
        'q9': 'no', 'q10': 'no', 'q11': 'no', 'q12': 'no',
        'q13': 'no', 'q14': 'no',
        'q13_specify': '', 'q14_specify': '',
        'allergies': '',
        'applicant_signature_data': MINIMAL_PNG_DATA_URL,
        'applicant_name': 'John Test',
        'applicant_date': date.today().isoformat(),
        'guardian_signature_data': '',
        'guardian_name': '',
        'guardian_date': '',
    }


class KioskActivationTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):
        self.client = Client()
        self.dojo = Dojo.objects.first()
        self.dojo.kiosk_pin = '1234'
        self.dojo.save()

    def _set_session(self, **kwargs):
        session = self.client.session
        for k, v in kwargs.items():
            session[k] = v
        session.save()

    def test_activate_with_correct_pin(self):
        self._set_session(dojo_id=self.dojo.id)
        response = self.client.post(reverse('kiosk_activate'), {'pin': '1234'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get('kiosk_mode'), True)

    def test_activate_with_wrong_pin(self):
        self._set_session(dojo_id=self.dojo.id)
        response = self.client.post(reverse('kiosk_activate'), {'pin': '9999'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('kiosk_mode', self.client.session)

    def test_activate_without_pin_configured(self):
        self.dojo.kiosk_pin = None
        self.dojo.save()
        self._set_session(dojo_id=self.dojo.id)
        response = self.client.post(reverse('kiosk_activate'), {'pin': '1234'})
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('kiosk_mode', self.client.session)

    def test_deactivate_with_correct_pin(self):
        self._set_session(dojo_id=self.dojo.id, kiosk_mode=True)
        response = self.client.post(reverse('kiosk_deactivate'), {'pin': '1234'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get('kiosk_mode'), False)

    def test_kiosk_home_requires_active_mode(self):
        self._set_session(dojo_id=self.dojo.id, kiosk_mode=False)
        response = self.client.get(reverse('kiosk_home'))
        self.assertEqual(response.status_code, 302)

    def test_kiosk_home_renders_when_active(self):
        self._set_session(dojo_id=self.dojo.id, kiosk_mode=True)
        response = self.client.get(reverse('kiosk_home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'New Student')
        self.assertContains(response, 'Register Attendance')

    def test_activate_pre_creates_sessions_from_classes(self):
        Classes.objects.filter(dojo=self.dojo).delete()
        today_weekday = WEEKDAY_NAMES[date.today().weekday()]
        address = Address.objects.first()
        Classes.objects.create(
            dojo=self.dojo, address=address, name='Today Class',
            type='weekly', days_of_week=[today_weekday],
            starting_at=date.today(), time_from='18:00', time_to='20:00',
        )
        Session.objects.filter(dojo=self.dojo, date=date.today()).delete()

        self._set_session(dojo_id=self.dojo.id)
        response = self.client.post(reverse('kiosk_activate'), {'pin': '1234'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Session.objects.filter(dojo=self.dojo, date=date.today()).exists())

    def test_activate_with_no_sessions_shows_warning(self):
        Classes.objects.filter(dojo=self.dojo).delete()
        Session.objects.filter(dojo=self.dojo, date=date.today()).delete()
        self._set_session(dojo_id=self.dojo.id)
        response = self.client.post(reverse('kiosk_activate'), {'pin': '1234'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No class scheduled for today')

    def test_kiosk_home_disables_attendance_without_sessions(self):
        Classes.objects.filter(dojo=self.dojo).delete()
        Session.objects.filter(dojo=self.dojo, date=date.today()).delete()
        self._set_session(dojo_id=self.dojo.id, kiosk_mode=True)
        response = self.client.get(reverse('kiosk_home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No class scheduled today')
        self.assertNotContains(response, 'href="/kiosk/attendance"')

    def test_kiosk_home_enables_attendance_with_sessions(self):
        self._set_session(dojo_id=self.dojo.id, kiosk_mode=True)
        today_weekday = WEEKDAY_NAMES[date.today().weekday()]
        address = Address.objects.first()
        Classes.objects.create(
            dojo=self.dojo, address=address, name='Today Class',
            type='weekly', days_of_week=[today_weekday],
            starting_at=date.today(), time_from='18:00', time_to='20:00',
        )
        get_or_create_today_sessions(self.dojo.id)
        response = self.client.get(reverse('kiosk_home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/kiosk/attendance"')


class KioskAttendanceTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):
        self.client = Client()
        self.dojo = Dojo.objects.first()
        self.dojo.kiosk_pin = '1234'
        self.dojo.save()

        self.address = Address.objects.first()

        today_weekday = WEEKDAY_NAMES[date.today().weekday()]
        self.classes = Classes.objects.create(
            dojo=self.dojo,
            address=self.address,
            name='Today Class',
            type='weekly',
            days_of_week=[today_weekday],
            starting_at=date.today(),
            time_from='18:00',
            time_to='20:00',
        )

        self.student = Student.objects.create(
            dojo=self.dojo,
            status='active',
            name='Test Student',
            email='student@test.com',
            hours=0,
        )

    def _set_kiosk_session(self):
        session = self.client.session
        session['dojo_id'] = self.dojo.id
        session['kiosk_mode'] = True
        session.save()

    def test_get_or_create_today_sessions_auto_creates(self):
        Session.objects.filter(dojo=self.dojo, date=date.today()).delete()
        sessions = get_or_create_today_sessions(self.dojo.id)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].name, 'Today Class')

    def test_get_or_create_today_sessions_idempotent(self):
        get_or_create_today_sessions(self.dojo.id)
        sessions = get_or_create_today_sessions(self.dojo.id)
        self.assertEqual(len(sessions), 1)

    def test_attendance_email_lookup_not_found(self):
        self._set_kiosk_session()
        response = self.client.post(reverse('kiosk_attendance'), {'email': 'nobody@test.com'})
        self.assertEqual(response.status_code, 302)

    def test_attendance_registration_single_session(self):
        self._set_kiosk_session()
        response = self.client.post(reverse('kiosk_attendance'), {'email': 'student@test.com'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Attendance.objects.filter(student=self.student).exists())
        attendance = Attendance.objects.filter(student=self.student).first()
        self.assertEqual(attendance.session.date, date.today())

    def test_attendance_duplicate_prevention(self):
        self._set_kiosk_session()
        self.client.post(reverse('kiosk_attendance'), {'email': 'student@test.com'})
        response = self.client.post(reverse('kiosk_attendance'), {'email': 'student@test.com'})
        self.assertEqual(Attendance.objects.filter(student=self.student).count(), 1)

    def test_attendance_no_class_scheduled(self):
        Session.objects.filter(dojo=self.dojo, date=date.today()).delete()
        self.classes.days_of_week = ['sunday']
        if date.today().weekday() == 6:
            self.classes.days_of_week = ['monday']
        self.classes.save()
        self._set_kiosk_session()
        response = self.client.post(reverse('kiosk_attendance'), {'email': 'student@test.com'})
        self.assertEqual(response.status_code, 302)

    def test_attendance_without_waiver_redirects_to_register(self):
        self._set_kiosk_session()
        response = self.client.post(reverse('kiosk_attendance'), {'email': 'student@test.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('kiosk_register'))
        self.assertTrue(Attendance.objects.filter(student=self.student).exists())
        self.assertEqual(
            self.client.session.get('kiosk_waiver_pending_email'),
            'student@test.com',
        )

    def test_waiver_completed_post_attendance_shows_waiver_success(self):
        self._set_kiosk_session()
        self.client.post(reverse('kiosk_attendance'), {'email': 'student@test.com'})

        data = _valid_waiver_form_data(email='student@test.com')
        response = self.client.post(reverse('kiosk_register'), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Waiver Submitted!')
        self.assertNotIn('kiosk_waiver_pending_email', self.client.session)
        self.assertTrue(StudentWaiver.objects.filter(student=self.student).exists())

    def test_attendance_with_existing_waiver_goes_to_completed(self):
        StudentWaiver.objects.create(
            dojo=self.dojo,
            student=self.student,
            first_name='Test',
            last_name='Student',
            address='123 St',
            phone='0412345678',
            email='student@test.com',
            terms_accepted=True,
            applicant_name='Test Student',
            applicant_date=date.today(),
        )
        self._set_kiosk_session()
        response = self.client.post(reverse('kiosk_attendance'), {'email': 'student@test.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('kiosk_attendance_completed'))
        self.assertNotIn('kiosk_waiver_pending_email', self.client.session)

    def test_attendance_duplicate_without_waiver_still_redirects_to_register(self):
        self._set_kiosk_session()
        self.client.post(reverse('kiosk_attendance'), {'email': 'student@test.com'})
        response = self.client.post(reverse('kiosk_attendance'), {'email': 'student@test.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('kiosk_register'))
        self.assertEqual(Attendance.objects.filter(student=self.student).count(), 1)


class KioskRegisterTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):
        self.client = Client()
        self.dojo = Dojo.objects.first()
        self.dojo.kiosk_pin = '1234'
        self.dojo.save()

    def _set_kiosk_session(self):
        session = self.client.session
        session['dojo_id'] = self.dojo.id
        session['kiosk_mode'] = True
        session.save()

    def test_register_creates_student_and_waiver(self):
        self._set_kiosk_session()
        data = _valid_waiver_form_data()
        response = self.client.post(reverse('kiosk_register'), data)
        self.assertEqual(response.status_code, 302)

        student = Student.objects.filter(email='newstudent@test.com').first()
        self.assertIsNotNone(student)
        self.assertEqual(student.name, 'John Test')
        self.assertEqual(student.status, 'active')
        self.assertEqual(student.mobile, '0412345678')
        self.assertEqual(student.kyu, 10)

        waiver = StudentWaiver.objects.filter(student=student).first()
        self.assertIsNotNone(waiver)
        self.assertTrue(waiver.terms_accepted)
        self.assertEqual(waiver.questionnaire_responses['q1'], 'no')

    def test_register_duplicate_email_shows_message(self):
        existing_student = Student.objects.create(
            dojo=self.dojo,
            status='active',
            name='Existing Student',
            email='existing@test.com',
        )
        StudentWaiver.objects.create(
            dojo=self.dojo,
            student=existing_student,
            first_name='Existing',
            last_name='Student',
            address='123 St',
            phone='0412345678',
            email='existing@test.com',
            terms_accepted=True,
            applicant_name='Existing Student',
            applicant_date=date.today(),
        )
        self._set_kiosk_session()
        data = _valid_waiver_form_data(email='existing@test.com')
        response = self.client.post(reverse('kiosk_register'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Student.objects.filter(email='existing@test.com').count(), 1)

    def test_register_honeypot_rejected(self):
        self._set_kiosk_session()
        data = _valid_waiver_form_data()
        data['email2'] = 'bot@spam.com'
        response = self.client.post(reverse('kiosk_register'), data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Student.objects.filter(email='newstudent@test.com').exists())


class KioskAttendeesTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):
        self.client = Client()
        self.dojo = Dojo.objects.first()
        self.dojo.kiosk_pin = '1234'
        self.dojo.save()

        self.address = Address.objects.first()

        today_weekday = WEEKDAY_NAMES[date.today().weekday()]
        self.classes = Classes.objects.create(
            dojo=self.dojo,
            address=self.address,
            name='Today Class',
            type='weekly',
            days_of_week=[today_weekday],
            starting_at=date.today(),
            time_from='18:00',
            time_to='20:00',
        )
        self.session = get_or_create_today_sessions(self.dojo.id)[0]

    def _set_kiosk_session(self):
        session = self.client.session
        session['dojo_id'] = self.dojo.id
        session['kiosk_mode'] = True
        session.save()

    def _create_student_with_attendance(self, name, email, **waiver_kwargs):
        student = Student.objects.create(
            dojo=self.dojo,
            status='active',
            name=name,
            email=email,
        )
        Attendance.objects.create(
            dojo_id=self.dojo.id,
            session=self.session,
            date=self.session.date,
            duration=self.session.duration,
            student=student,
        )
        if waiver_kwargs:
            StudentWaiver.objects.create(
                dojo=self.dojo,
                student=student,
                first_name=name.split()[0],
                last_name=name.split()[-1],
                address='123 St',
                phone='0400000000',
                email=email,
                terms_accepted=True,
                applicant_name=name,
                applicant_date=date.today(),
                **waiver_kwargs,
            )
        return student

    def test_attendees_requires_kiosk_mode(self):
        response = self.client.get(reverse('kiosk_attendees'))
        self.assertEqual(response.status_code, 302)

    def test_attendees_shows_pin_form_on_get(self):
        self._set_kiosk_session()
        response = self.client.get(reverse('kiosk_attendees'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pin')

    def test_attendees_wrong_pin_rejected(self):
        self._set_kiosk_session()
        response = self.client.post(reverse('kiosk_attendees'), {'pin': '9999'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('kiosk_attendees_verified', self.client.session)

    def test_attendees_correct_pin_single_session_redirects_to_list(self):
        self._set_kiosk_session()
        response = self.client.post(reverse('kiosk_attendees'), {'pin': '1234'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('kiosk_attendees_session', args=[self.session.id]))
        self.assertTrue(self.client.session.get('kiosk_attendees_verified'))

    def test_attendees_session_requires_pin_verification(self):
        self._set_kiosk_session()
        response = self.client.get(reverse('kiosk_attendees_session', args=[self.session.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('kiosk_attendees'))

    def test_attendees_list_shows_registered_students(self):
        self._create_student_with_attendance('Alice Test', 'alice@test.com')
        self._create_student_with_attendance('Bob Test', 'bob@test.com')

        self._set_kiosk_session()
        self.client.post(reverse('kiosk_attendees'), {'pin': '1234'})
        response = self.client.get(reverse('kiosk_attendees_session', args=[self.session.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice Test')
        self.assertContains(response, 'Bob Test')
        self.assertContains(response, '2 attendees')

    def test_attendees_list_empty_when_no_registrations(self):
        self._set_kiosk_session()
        self.client.post(reverse('kiosk_attendees'), {'pin': '1234'})
        response = self.client.get(reverse('kiosk_attendees_session', args=[self.session.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No students registered yet')

    def test_attendees_list_shows_medical_info_from_waiver(self):
        self._create_student_with_attendance(
            'Medical Mike', 'mike@test.com',
            emergency_contact_name='Jane Mike',
            emergency_contact_relationship='Wife',
            emergency_contact_phone='0411111111',
            questionnaire_responses={'q9': 'yes', 'q11': 'yes'},
            allergies='Peanuts',
            medical_specify='Type 1 Diabetes',
        )

        self._set_kiosk_session()
        self.client.post(reverse('kiosk_attendees'), {'pin': '1234'})
        response = self.client.get(reverse('kiosk_attendees_session', args=[self.session.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Medical Mike')
        self.assertContains(response, 'Jane Mike')
        self.assertContains(response, 'Wife')
        self.assertContains(response, '0411111111')
        self.assertContains(response, 'Asthma')
        self.assertContains(response, 'Diabetes')
        self.assertContains(response, 'Peanuts')
        self.assertContains(response, 'Type 1 Diabetes')
        self.assertContains(response, 'Medical Alert')

    def test_attendees_list_shows_student_without_waiver(self):
        student = Student.objects.create(
            dojo=self.dojo,
            status='active',
            name='No Waiver Ned',
            email='ned@test.com',
            emergency_contact='Sally Ned (Mother) 0422222222',
            medical_conditions='Previous knee injury',
        )
        Attendance.objects.create(
            dojo_id=self.dojo.id,
            session=self.session,
            date=self.session.date,
            duration=self.session.duration,
            student=student,
        )

        self._set_kiosk_session()
        self.client.post(reverse('kiosk_attendees'), {'pin': '1234'})
        response = self.client.get(reverse('kiosk_attendees_session', args=[self.session.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No Waiver Ned')
        self.assertContains(response, 'Sally Ned')
        self.assertContains(response, 'Previous knee injury')
        self.assertContains(response, 'No waiver on file')


class KioskSecurityTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):
        self.client = Client()
        self.dojo = Dojo.objects.first()
        self.dojo.kiosk_pin = '1234'
        self.dojo.save()

    def _set_session(self, **kwargs):
        session = self.client.session
        for k, v in kwargs.items():
            session[k] = v
        session.save()

    def _set_kiosk_session(self):
        session = self.client.session
        session['dojo_id'] = self.dojo.id
        session['kiosk_mode'] = True
        session.save()

    def test_honeypot_on_activate_shows_fake_success(self):
        self._set_session(dojo_id=self.dojo.id)
        response = self.client.post(reverse('kiosk_activate'), {'pin': '1234', 'website': 'bot-spam.com'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login Completed!')
        self.assertNotIn('kiosk_mode', self.client.session)

    def test_honeypot_on_attendees_shows_fake_success(self):
        self._set_kiosk_session()
        response = self.client.post(reverse('kiosk_attendees'), {'pin': '1234', 'website': 'bot-spam.com'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login Completed!')
        self.assertNotIn('kiosk_attendees_verified', self.client.session)

    def test_wrong_pin_increments_counter(self):
        self._set_session(dojo_id=self.dojo.id)
        self.client.post(reverse('kiosk_activate'), {'pin': '9999'})
        self.dojo.refresh_from_db()
        self.assertEqual(self.dojo.kiosk_failed_attempts, 1)
        self.assertFalse(self.dojo.kiosk_locked)

    def test_correct_pin_resets_counter(self):
        self._set_session(dojo_id=self.dojo.id)
        self.dojo.kiosk_failed_attempts = 5
        self.dojo.save()
        self.client.post(reverse('kiosk_activate'), {'pin': '1234'})
        self.dojo.refresh_from_db()
        self.assertEqual(self.dojo.kiosk_failed_attempts, 0)

    def test_ninth_failure_does_not_lock(self):
        self._set_session(dojo_id=self.dojo.id)
        for _ in range(9):
            self.client.post(reverse('kiosk_activate'), {'pin': '9999'})
        self.dojo.refresh_from_db()
        self.assertFalse(self.dojo.kiosk_locked)
        self.assertEqual(self.dojo.kiosk_failed_attempts, 9)

    def test_ten_failures_lock_kiosk(self):
        self._set_session(dojo_id=self.dojo.id)
        for _ in range(10):
            response = self.client.post(reverse('kiosk_activate'), {'pin': '9999'})
        self.dojo.refresh_from_db()
        self.assertTrue(self.dojo.kiosk_locked)
        self.assertEqual(self.dojo.kiosk_failed_attempts, 10)
        self.assertContains(response, 'Kiosk Mode is locked')

    def test_locked_kiosk_shows_locked_message(self):
        self.dojo.kiosk_locked = True
        self.dojo.save()
        self._set_session(dojo_id=self.dojo.id)
        response = self.client.get(reverse('kiosk_activate'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kiosk Mode is locked')
        self.assertNotContains(response, 'name="pin"')

    def test_locked_kiosk_attendees_shows_locked_message(self):
        self.dojo.kiosk_locked = True
        self.dojo.save()
        self._set_kiosk_session()
        response = self.client.get(reverse('kiosk_attendees'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kiosk Mode is locked')

    def test_locked_kiosk_does_not_process_correct_pin(self):
        self.dojo.kiosk_locked = True
        self.dojo.kiosk_failed_attempts = 10
        self.dojo.save()
        self._set_session(dojo_id=self.dojo.id)
        response = self.client.post(reverse('kiosk_activate'), {'pin': '1234'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kiosk Mode is locked')
        self.assertNotIn('kiosk_mode', self.client.session)

    def test_failed_attendees_pin_contributes_to_same_counter(self):
        self._set_kiosk_session()
        self.client.post(reverse('kiosk_attendees'), {'pin': '9999'})
        self.dojo.refresh_from_db()
        self.assertEqual(self.dojo.kiosk_failed_attempts, 1)
