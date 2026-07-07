from datetime import date, timedelta

from django.test import TestCase, Client
from django.urls import reverse

from dojoconf.models import Dojo, Address, Event
from shodan.models import Session, EventWaiver


class EventWaiverLandingPageTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):
        self.client = Client()
        self.dojo = Dojo.objects.first()
        self.address = Address.objects.first()

    def _set_session(self):
        session = self.client.session
        session['dojo_id'] = self.dojo.id
        session.save()

    def _create_waiver_event(self, name='Seminar'):
        return Event.objects.create(
            dojo=self.dojo,
            address=self.address,
            name=name,
            requires_waiver=True,
        )

    def _create_future_session(self, event, days_ahead=7, time_from='10:00', time_to='12:00'):
        from datetime import time, timedelta as td
        return Session.objects.create(
            dojo=self.dojo,
            event=event,
            date=date.today() + timedelta(days=days_ahead),
            time_from=time.fromisoformat(time_from),
            time_to=time.fromisoformat(time_to),
            duration=td(hours=2),
        )

    def test_no_events_button_when_no_waiver_event(self):
        self._set_session()
        response = self.client.get(reverse('landing_page'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Events')

    def test_no_events_button_when_waiver_event_has_no_future_session(self):
        self._set_session()
        event = self._create_waiver_event()
        response = self.client.get(reverse('landing_page'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Events')

    def test_no_events_button_when_waiver_event_has_only_past_session(self):
        self._set_session()
        event = self._create_waiver_event()
        from datetime import time, timedelta as td
        Session.objects.create(
            dojo=self.dojo,
            event=event,
            date=date.today() - timedelta(days=7),
            time_from=time.fromisoformat('10:00'),
            time_to=time.fromisoformat('12:00'),
            duration=td(hours=2),
        )
        response = self.client.get(reverse('landing_page'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Events')

    def test_events_button_shown_when_waiver_event_has_future_session(self):
        self._set_session()
        event = self._create_waiver_event()
        self._create_future_session(event)
        response = self.client.get(reverse('landing_page'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Events')

    def test_events_button_links_directly_when_single_event(self):
        self._set_session()
        event = self._create_waiver_event()
        self._create_future_session(event)
        response = self.client.get(reverse('landing_page'))
        self.assertContains(response, f'/event/{event.id}/waiver')

    def test_events_button_links_to_list_when_multiple_events(self):
        self._set_session()
        event1 = self._create_waiver_event(name='Seminar A')
        event2 = self._create_waiver_event(name='Seminar B')
        self._create_future_session(event1)
        self._create_future_session(event2)
        response = self.client.get(reverse('landing_page'))
        self.assertContains(response, '/event/waiver/list')

    def test_event_without_waiver_ignored_even_with_future_session(self):
        self._set_session()
        event = Event.objects.create(
            dojo=self.dojo,
            address=self.address,
            name='No Waiver Event',
            requires_waiver=False,
        )
        self._create_future_session(event)
        response = self.client.get(reverse('landing_page'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Events')


class EventWaiverListTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):
        self.client = Client()
        self.dojo = Dojo.objects.first()
        self.address = Address.objects.first()

    def _set_session(self):
        session = self.client.session
        session['dojo_id'] = self.dojo.id
        session.save()

    def test_list_redirects_to_landing_when_no_future_session(self):
        self._set_session()
        Event.objects.create(
            dojo=self.dojo, address=self.address,
            name='Stale Event', requires_waiver=True,
        )
        response = self.client.get(reverse('event_waiver_list'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('landing_page'))

    def test_list_redirects_to_single_waiver_when_one_future_session(self):
        self._set_session()
        event = Event.objects.create(
            dojo=self.dojo, address=self.address,
            name='Seminar', requires_waiver=True,
        )
        from datetime import time, timedelta as td
        Session.objects.create(
            dojo=self.dojo, event=event,
            date=date.today() + timedelta(days=3),
            time_from=time.fromisoformat('10:00'),
            time_to=time.fromisoformat('12:00'),
            duration=td(hours=2),
        )
        response = self.client.get(reverse('event_waiver_list'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('event_waiver', args=[event.id]))


class EventWaiverSessionDetailsTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):
        self.client = Client()
        self.dojo = Dojo.objects.first()
        self.address = Address.objects.first()
        self.event = Event.objects.create(
            dojo=self.dojo, address=self.address,
            name='Grading Championship', requires_waiver=True,
        )

    def _set_session(self):
        session = self.client.session
        session['dojo_id'] = self.dojo.id
        session.save()

    def test_waiver_page_shows_session_date_and_time(self):
        self._set_session()
        from datetime import time, timedelta as td
        future = date.today() + timedelta(days=10)
        Session.objects.create(
            dojo=self.dojo, event=self.event,
            date=future,
            time_from=time.fromisoformat('14:00'),
            time_to=time.fromisoformat('16:30'),
            duration=td(hours=2, minutes=30),
        )
        response = self.client.get(reverse('event_waiver', args=[self.event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.event.name)
        self.assertContains(response, future.strftime('%-d'))
        self.assertContains(response, '2:00 PM')
        self.assertContains(response, '4:30 PM')

    def test_waiver_page_shows_nearest_session_when_multiple(self):
        self._set_session()
        from datetime import time, timedelta as td
        near_date = date.today() + timedelta(days=5)
        far_date = date.today() + timedelta(days=20)
        Session.objects.create(
            dojo=self.dojo, event=self.event,
            date=far_date,
            time_from=time.fromisoformat('09:00'),
            time_to=time.fromisoformat('11:00'),
            duration=td(hours=2),
        )
        Session.objects.create(
            dojo=self.dojo, event=self.event,
            date=near_date,
            time_from=time.fromisoformat('15:00'),
            time_to=time.fromisoformat('17:00'),
            duration=td(hours=2),
        )
        response = self.client.get(reverse('event_waiver', args=[self.event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, near_date.strftime('%-d'))
        self.assertContains(response, '3:00 PM')
        self.assertNotContains(response, '9:00 AM')

    def test_waiver_page_shows_message_when_no_future_session(self):
        self._set_session()
        response = self.client.get(reverse('event_waiver', args=[self.event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'does not have a scheduled session')

    def test_waiver_page_shows_message_when_only_past_session(self):
        self._set_session()
        from datetime import time, timedelta as td
        Session.objects.create(
            dojo=self.dojo, event=self.event,
            date=date.today() - timedelta(days=5),
            time_from=time.fromisoformat('10:00'),
            time_to=time.fromisoformat('12:00'),
            duration=td(hours=2),
        )
        response = self.client.get(reverse('event_waiver', args=[self.event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'does not have a scheduled session')


# A minimal valid 1x1 PNG as base64 (no data-URI prefix) for signature fields.
_PNG_B64 = (
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAA'
    'AAABJRU5ErkJggg=='
)


class EventWaiverSubmissionTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):
        self.client = Client()
        self.dojo = Dojo.objects.first()
        self.address = Address.objects.first()
        self.event = Event.objects.create(
            dojo=self.dojo, address=self.address,
            name='Grading Championship', requires_waiver=True,
        )
        session = self.client.session
        session['dojo_id'] = self.dojo.id
        session.save()

    def _valid_data(self, **overrides):
        data = {
            'first_name': 'Maxwell',
            'last_name': 'Watts',
            'address': '12 Seacliff Rd',
            'phone': '0412345678',
            'email': 'parent@example.com',
            'date_of_birth': '01/01/1990',
            'emergency_contact_name': 'Jane Watts',
            'emergency_contact_phone': '0498765432',
            'terms_accepted': 'on',
            **{f'q{i}': 'no' for i in range(1, 15)},
            'applicant_signature_data': _PNG_B64,
            'applicant_name': 'Maxwell Watts',
            'applicant_date': date.today().strftime('%d/%m/%Y'),
        }
        data.update(overrides)
        return data

    def test_first_submission_succeeds(self):
        response = self.client.post(
            reverse('event_waiver', args=[self.event.id]),
            self._valid_data(),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('event_waiver_success'))
        self.assertEqual(EventWaiver.objects.filter(event=self.event).count(), 1)

    def test_same_participant_blocked_from_resubmission(self):
        self.client.post(reverse('event_waiver', args=[self.event.id]), self._valid_data())
        # Same name + DOB (the same person) must be blocked.
        response = self.client.post(
            reverse('event_waiver', args=[self.event.id]),
            self._valid_data(email='different@example.com'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already signed the waiver')
        self.assertEqual(EventWaiver.objects.filter(event=self.event).count(), 1)

    def test_sibling_with_same_email_is_allowed(self):
        # Parent signs for the first participant.
        self.client.post(reverse('event_waiver', args=[self.event.id]), self._valid_data(
            first_name='Maxwell', last_name='Watts',
            date_of_birth='01/01/1990',
        ))
        # Parent signs for a second participant — same email, different identity.
        response = self.client.post(reverse('event_waiver', args=[self.event.id]), self._valid_data(
            first_name='Eli', last_name='Watts',
            date_of_birth='05/05/1985',
            applicant_name='Eli Watts',
        ))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('event_waiver_success'))
        self.assertEqual(EventWaiver.objects.filter(event=self.event).count(), 2)

    def test_honeypot_silently_succeeds_without_creating_record(self):
        response = self.client.post(
            reverse('event_waiver', args=[self.event.id]),
            self._valid_data(email2='bot@spam.com'),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('event_waiver_success'))
        self.assertEqual(EventWaiver.objects.filter(event=self.event).count(), 0)
