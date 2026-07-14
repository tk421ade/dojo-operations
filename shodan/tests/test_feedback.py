from datetime import date, time, timedelta

from django.test import TestCase, Client
from django.urls import reverse

from dojoconf.models import Dojo, Address, Event
from dojoconf.tests.utils import login_verified
from shodan.models import (
    Session, SessionFeedbackLink, SessionFeedbackQuestion, SessionFeedback,
)
from web.forms import DEFAULT_FEEDBACK_QUESTIONS, build_feedback_form


class FeedbackModelTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):
        self.dojo = Dojo.objects.first()
        self.address = Address.objects.first()
        self.event = Event.objects.create(
            dojo=self.dojo, address=self.address, name='Seminar',
        )
        self.session = Session.objects.create(
            dojo=self.dojo, event=self.event,
            date=date.today() + timedelta(days=7),
            time_from=time.fromisoformat('10:00'),
            time_to=time.fromisoformat('12:00'),
            duration=timedelta(hours=2),
        )

    def test_token_auto_generated_on_creation(self):
        link = SessionFeedbackLink.objects.create(
            dojo=self.dojo, session=self.session,
        )
        self.assertTrue(link.token)
        self.assertGreater(len(link.token), 20)

    def test_token_is_unique(self):
        link1 = SessionFeedbackLink.objects.create(
            dojo=self.dojo, session=self.session,
        )
        session2 = Session.objects.create(
            dojo=self.dojo, event=self.event,
            date=date.today() + timedelta(days=14),
            time_from=time.fromisoformat('10:00'),
            time_to=time.fromisoformat('12:00'),
            duration=timedelta(hours=2),
        )
        link2 = SessionFeedbackLink.objects.create(
            dojo=self.dojo, session=session2,
        )
        self.assertNotEqual(link1.token, link2.token)

    def test_one_to_one_constraint(self):
        SessionFeedbackLink.objects.create(
            dojo=self.dojo, session=self.session,
        )
        with self.assertRaises(Exception):
            SessionFeedbackLink.objects.create(
                dojo=self.dojo, session=self.session,
            )

    def test_default_is_active(self):
        link = SessionFeedbackLink.objects.create(
            dojo=self.dojo, session=self.session,
        )
        self.assertTrue(link.is_active)

    def test_link_str(self):
        link = SessionFeedbackLink.objects.create(
            dojo=self.dojo, session=self.session,
        )
        self.assertIn('Feedback', str(link))
        self.assertIn(self.session.name, str(link))


class FeedbackViewTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):
        self.client = Client()
        self.dojo = Dojo.objects.first()
        self.address = Address.objects.first()
        self.event = Event.objects.create(
            dojo=self.dojo, address=self.address, name='Seminar',
        )
        self.session = Session.objects.create(
            dojo=self.dojo, event=self.event,
            date=date.today() + timedelta(days=7),
            time_from=time.fromisoformat('10:00'),
            time_to=time.fromisoformat('12:00'),
            duration=timedelta(hours=2),
        )
        s = self.client.session
        s['dojo_id'] = self.dojo.id
        s.save()

    def _create_feedback_link(self):
        link = SessionFeedbackLink.objects.create(
            dojo=self.dojo, session=self.session,
        )
        for q in DEFAULT_FEEDBACK_QUESTIONS:
            SessionFeedbackQuestion.objects.create(
                feedback_link=link,
                question_text=q['question_text'],
                question_type=q['question_type'],
                choices=q['choices'],
                order=q['order'],
                required=q['required'],
            )
        return link

    def _valid_post_data(self, link):
        data = {'email2': ''}
        for q in link.questions.all():
            field_name = f'q_{q.pk}'
            if q.question_type == 'rating':
                data[field_name] = '4'
            elif q.question_type == 'yes_no':
                data[field_name] = 'yes'
            elif q.question_type == 'text':
                data[field_name] = 'Great session!'
            elif q.question_type == 'choice':
                data[field_name] = '4 hours'
        return data

    def test_invalid_token_returns_404(self):
        response = self.client.get(reverse('session_feedback', args=['invalid-token']))
        self.assertEqual(response.status_code, 404)

    def test_valid_token_renders_form(self):
        link = self._create_feedback_link()
        response = self.client.get(reverse('session_feedback', args=[link.token]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Session Feedback')
        self.assertContains(response, self.session.name)

    def test_form_renders_all_questions(self):
        link = self._create_feedback_link()
        response = self.client.get(reverse('session_feedback', args=[link.token]))
        for q in link.questions.all():
            self.assertContains(response, q.question_text)

    def test_form_shows_anonymous_notice(self):
        link = self._create_feedback_link()
        response = self.client.get(reverse('session_feedback', args=[link.token]))
        self.assertContains(response, 'anonymous')

    def test_submission_creates_feedback(self):
        link = self._create_feedback_link()
        data = self._valid_post_data(link)
        response = self.client.post(
            reverse('session_feedback', args=[link.token]), data,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse('session_feedback_success', args=[link.token]),
        )
        self.assertEqual(SessionFeedback.objects.filter(feedback_link=link).count(), 1)

        feedback = SessionFeedback.objects.get(feedback_link=link)
        for q in link.questions.all():
            self.assertIn(str(q.pk), feedback.responses)

    def test_submission_sets_duplicate_cookie(self):
        link = self._create_feedback_link()
        data = self._valid_post_data(link)
        response = self.client.post(
            reverse('session_feedback', args=[link.token]), data,
        )
        cookie_key = f'feedback_done_{link.token}'
        self.assertIn(cookie_key, response.cookies)

    def test_duplicate_submission_blocked_by_cookie(self):
        link = self._create_feedback_link()
        data = self._valid_post_data(link)

        self.client.post(reverse('session_feedback', args=[link.token]), data)

        response = self.client.get(reverse('session_feedback', args=[link.token]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Already Submitted')

        response = self.client.post(
            reverse('session_feedback', args=[link.token]), data,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SessionFeedback.objects.filter(feedback_link=link).count(), 1)

    def test_honeypot_silently_succeeds_without_creating_record(self):
        link = self._create_feedback_link()
        data = self._valid_post_data(link)
        data['email2'] = 'bot@spam.com'
        response = self.client.post(
            reverse('session_feedback', args=[link.token]), data,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse('session_feedback_success', args=[link.token]),
        )
        self.assertEqual(SessionFeedback.objects.filter(feedback_link=link).count(), 0)

    def test_inactive_link_shows_closed_message(self):
        link = self._create_feedback_link()
        link.is_active = False
        link.save()
        response = self.client.get(reverse('session_feedback', args=[link.token]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Feedback Closed')

    def test_cross_dojo_token_returns_404(self):
        other_dojo = Dojo.objects.create(
            name='Other Dojo',
            email='other@test.com',
            timezone='Australia/Melbourne',
        )
        other_address = Address.objects.create(
            dojo=other_dojo, name='Other Addr',
            street='1 St', city='City', state='ST', zip_code='1234', country='AU',
        )
        other_event = Event.objects.create(
            dojo=other_dojo, address=other_address, name='Other Event',
        )
        other_session = Session.objects.create(
            dojo=other_dojo, event=other_event,
            date=date.today() + timedelta(days=7),
            time_from=time.fromisoformat('10:00'),
            time_to=time.fromisoformat('12:00'),
            duration=timedelta(hours=2),
        )
        link = SessionFeedbackLink.objects.create(
            dojo=other_dojo, session=other_session,
        )
        response = self.client.get(reverse('session_feedback', args=[link.token]))
        self.assertEqual(response.status_code, 404)

    def test_required_field_validation(self):
        link = self._create_feedback_link()
        data = {'email2': ''}
        response = self.client.post(
            reverse('session_feedback', args=[link.token]), data,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SessionFeedback.objects.filter(feedback_link=link).count(), 0)

    def test_success_page_renders(self):
        link = self._create_feedback_link()
        response = self.client.get(
            reverse('session_feedback_success', args=[link.token]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Thank You')

    def test_optional_questions_can_be_blank(self):
        link = self._create_feedback_link()
        data = {'email2': ''}
        for q in link.questions.all():
            field_name = f'q_{q.pk}'
            if q.required:
                if q.question_type == 'rating':
                    data[field_name] = '5'
                elif q.question_type == 'yes_no':
                    data[field_name] = 'yes'
            else:
                pass
        response = self.client.post(
            reverse('session_feedback', args=[link.token]), data,
        )
        self.assertEqual(response.status_code, 302)
        feedback = SessionFeedback.objects.get(feedback_link=link)
        for q in link.questions.all():
            if q.required:
                self.assertIn(str(q.pk), feedback.responses)


class FeedbackFormBuilderTest(TestCase):

    def test_build_form_with_no_questions(self):
        FormClass = build_feedback_form([])
        form = FormClass()
        self.assertIn('email2', form.fields)

    def test_build_form_generates_correct_field_types(self):
        class FakeQuestion:
            def __init__(self, pk, question_type, question_text='Test?', required=True, choices=None):
                self.pk = pk
                self.question_type = question_type
                self.question_text = question_text
                self.required = required
                self.choices = choices or []

        questions = [
            FakeQuestion(1, 'rating'),
            FakeQuestion(2, 'yes_no'),
            FakeQuestion(3, 'text'),
            FakeQuestion(4, 'choice', choices=['A', 'B']),
        ]
        FormClass = build_feedback_form(questions)
        form = FormClass()

        self.assertIn('q_1', form.fields)
        self.assertIn('q_2', form.fields)
        self.assertIn('q_3', form.fields)
        self.assertIn('q_4', form.fields)

        from django import forms as djforms
        self.assertIsInstance(form.fields['q_1'], djforms.ChoiceField)
        self.assertIsInstance(form.fields['q_3'], djforms.CharField)

        choice_field = form.fields['q_4']
        self.assertEqual(len(choice_field.choices), 2)


class FeedbackAdminActionTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):
        self.admin_client = Client()
        self.dojo = Dojo.objects.first()
        self.address = Address.objects.first()
        self.event = Event.objects.create(
            dojo=self.dojo, address=self.address, name='Seminar',
        )
        self.session = Session.objects.create(
            dojo=self.dojo, event=self.event,
            date=date.today() + timedelta(days=7),
            time_from=time.fromisoformat('10:00'),
            time_to=time.fromisoformat('12:00'),
            duration=timedelta(hours=2),
        )

    def test_admin_action_generates_link_with_default_questions(self):
        self.admin_client.login(username='admin', password='password')
        login_verified(self.admin_client)

        response = self.admin_client.post(
            reverse('admin:shodan_session_changelist'),
            {
                'action': 'generate_feedback_link',
                '_selected_action': [self.session.pk],
            },
        )
        self.assertEqual(response.status_code, 302)

        link = SessionFeedbackLink.objects.get(session=self.session)
        self.assertTrue(link.token)
        self.assertTrue(link.is_active)
        self.assertEqual(link.questions.count(), len(DEFAULT_FEEDBACK_QUESTIONS))

    def test_admin_action_skips_existing_link(self):
        self.admin_client.login(username='admin', password='password')
        login_verified(self.admin_client)

        existing = SessionFeedbackLink.objects.create(
            dojo=self.dojo, session=self.session,
        )
        original_token = existing.token

        response = self.admin_client.post(
            reverse('admin:shodan_session_changelist'),
            {
                'action': 'generate_feedback_link',
                '_selected_action': [self.session.pk],
            },
        )
        self.assertEqual(response.status_code, 302)

        link = SessionFeedbackLink.objects.get(session=self.session)
        self.assertEqual(link.token, original_token)

    def test_feedback_link_admin_list_view(self):
        self.admin_client.login(username='admin', password='password')
        login_verified(self.admin_client)

        link = SessionFeedbackLink.objects.create(
            dojo=self.dojo, session=self.session,
        )

        response = self.admin_client.get(
            reverse('admin:shodan_sessionfeedbacklink_changelist'),
        )
        self.assertEqual(response.status_code, 200)

    def test_feedback_admin_list_view(self):
        self.admin_client.login(username='admin', password='password')
        login_verified(self.admin_client)

        link = SessionFeedbackLink.objects.create(
            dojo=self.dojo, session=self.session,
        )
        SessionFeedback.objects.create(
            dojo=self.dojo, feedback_link=link,
            responses={'1': 'Great'},
        )

        response = self.admin_client.get(
            reverse('admin:shodan_sessionfeedback_changelist'),
        )
        self.assertEqual(response.status_code, 200)
