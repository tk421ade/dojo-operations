from datetime import date, time, timedelta

from django.contrib import admin as django_admin
from django.contrib.auth.models import User
from django.test import TestCase, Client, RequestFactory, override_settings
from django.urls import reverse

from dojoconf.models import Dojo, Address, Event
from dojoconf.tests.utils import login_verified
from shodan.models import (
    Session, SessionFeedbackLink, SessionFeedbackQuestion, SessionFeedback,
)
from shodan.admin import SessionFeedbackAdmin
from web.forms import DEFAULT_FEEDBACK_QUESTIONS, build_feedback_form, sync_default_questions


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


class FeedbackWizardTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):
        self.client = Client()
        self.dojo = Dojo.objects.first()
        self.address = Address.objects.first()
        self.event = Event.objects.create(
            dojo=self.dojo, address=self.address, name='Fight Seminar',
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
        sync_default_questions(link)
        return link

    # --- Intro page tests ---

    def test_invalid_token_returns_404(self):
        response = self.client.get(reverse('session_feedback', args=['invalid-token']))
        self.assertEqual(response.status_code, 404)

    def test_intro_page_shows_dojo_and_session_info(self):
        link = self._create_feedback_link()
        response = self.client.get(reverse('session_feedback', args=[link.token]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.dojo.name)
        self.assertContains(response, self.session.name)
        self.assertContains(response, 'Start Feedback')

    def test_intro_shows_question_count(self):
        link = self._create_feedback_link()
        response = self.client.get(reverse('session_feedback', args=[link.token]))
        self.assertContains(response, str(link.questions.count()))

    def test_intro_shows_anonymous_notice(self):
        link = self._create_feedback_link()
        response = self.client.get(reverse('session_feedback', args=[link.token]))
        self.assertContains(response, 'anonymous')

    def test_intro_inactive_link_shows_closed(self):
        link = self._create_feedback_link()
        link.is_active = False
        link.save()
        response = self.client.get(reverse('session_feedback', args=[link.token]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Feedback Closed')

    def test_intro_already_submitted_shows_message(self):
        link = self._create_feedback_link()
        self.client.cookies['feedback_done_' + link.token] = '1'
        response = self.client.get(reverse('session_feedback', args=[link.token]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Already Submitted')

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

    # --- Step rendering tests ---

    def test_step_renders_question(self):
        link = self._create_feedback_link()
        first_q = link.questions.order_by('order').first()
        response = self.client.get(reverse('session_feedback_step', args=[link.token, 1]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, first_q.question_text)

    def test_step_shows_progress_bar(self):
        link = self._create_feedback_link()
        response = self.client.get(reverse('session_feedback_step', args=[link.token, 1]))
        self.assertContains(response, 'Question 1 of')
        # Before the branching question is answered, two conditional questions are
        # hidden, so the visible total is 9 (not 11). 1/9 = 11%.
        self.assertContains(response, '11%')

    def test_step_back_button_hidden_on_step_1(self):
        link = self._create_feedback_link()
        response = self.client.get(reverse('session_feedback_step', args=[link.token, 1]))
        self.assertNotContains(response, 'Back')

    def test_step_back_button_shown_on_step_2(self):
        link = self._create_feedback_link()
        response = self.client.get(reverse('session_feedback_step', args=[link.token, 2]))
        self.assertContains(response, 'Back')

    def test_step_out_of_range_redirects_to_intro(self):
        link = self._create_feedback_link()
        total = link.questions.count()
        response = self.client.get(reverse('session_feedback_step', args=[link.token, total + 1]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('session_feedback', args=[link.token]))

    def test_step_redirects_when_already_done(self):
        link = self._create_feedback_link()
        self.client.cookies['feedback_done_' + link.token] = '1'
        response = self.client.get(reverse('session_feedback_step', args=[link.token, 1]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('session_feedback', args=[link.token]))

    def test_step_redirects_when_inactive(self):
        link = self._create_feedback_link()
        link.is_active = False
        link.save()
        response = self.client.get(reverse('session_feedback_step', args=[link.token, 1]))
        self.assertEqual(response.status_code, 302)

    # --- Wizard flow tests ---

    def test_step1_post_creates_progress_record_and_saves_answer(self):
        link = self._create_feedback_link()
        q = link.questions.order_by('order').first()
        response = self.client.post(
            reverse('session_feedback_step', args=[link.token, 1]),
            {f'q_{q.pk}': '4', 'email2': ''},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('session_feedback_step', args=[link.token, 2]))

        feedback = SessionFeedback.objects.get(feedback_link=link)
        self.assertEqual(feedback.responses[str(q.pk)], '4')

        progress_cookie = f'feedback_progress_{link.token}'
        self.assertIn(progress_cookie, response.cookies)

    def test_required_question_validation_on_step(self):
        link = self._create_feedback_link()
        q = link.questions.filter(required=True).order_by('order').first()
        response = self.client.post(
            reverse('session_feedback_step', args=[link.token, q.order]),
            {'email2': ''},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SessionFeedback.objects.filter(feedback_link=link).count(), 0)

    def test_optional_question_can_be_blank(self):
        link = self._create_feedback_link()
        q = link.questions.filter(required=False).order_by('order').first()
        response = self.client.post(
            reverse('session_feedback_step', args=[link.token, q.order]),
            {'email2': ''},
        )
        self.assertEqual(response.status_code, 302)

    def test_last_step_sets_done_cookie_and_redirects_to_success(self):
        link = self._create_feedback_link()
        attend_q = link.questions.get(question_text='Would you attend another session like this?')
        comments_q = link.questions.get(question_text='Any other comments or feedback?')

        # Create a progress record with Q8 answered "yes" so that the comments
        # question is the last visible step (step 10 of 10).
        feedback = SessionFeedback.objects.create(
            dojo=self.dojo, feedback_link=link,
            responses={str(attend_q.pk): 'yes'},
        )
        self.client.cookies['feedback_progress_' + link.token] = str(feedback.pk)

        response = self.client.post(
            reverse('session_feedback_step', args=[link.token, 10]),
            {f'q_{comments_q.pk}': 'Great!', 'email2': ''},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('session_feedback_success', args=[link.token]))
        done_cookie = f'feedback_done_{link.token}'
        self.assertIn(done_cookie, response.cookies)

    def test_honeypot_creates_bot_record(self):
        link = self._create_feedback_link()
        q = link.questions.order_by('order').first()
        response = self.client.post(
            reverse('session_feedback_step', args=[link.token, 1]),
            {f'q_{q.pk}': '4', 'email2': 'bot@spam.com'},
            REMOTE_ADDR='203.0.113.9',
            HTTP_USER_AGENT='SpamBot/2.0',
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('session_feedback_success', args=[link.token]))
        feedback = SessionFeedback.objects.get(feedback_link=link)
        self.assertTrue(feedback.is_bot)
        self.assertEqual(feedback.honeypot_value, 'bot@spam.com')
        self.assertEqual(feedback.ip_address, '203.0.113.9')
        self.assertEqual(feedback.user_agent, 'SpamBot/2.0')
        self.assertEqual(feedback.responses, {})

    def test_step1_post_captures_ip_and_user_agent(self):
        link = self._create_feedback_link()
        q = link.questions.order_by('order').first()
        self.client.post(
            reverse('session_feedback_step', args=[link.token, 1]),
            {f'q_{q.pk}': '4', 'email2': ''},
            REMOTE_ADDR='203.0.113.5',
            HTTP_USER_AGENT='Mozilla/5.0 (Test Browser)',
        )
        feedback = SessionFeedback.objects.get(feedback_link=link)
        self.assertFalse(feedback.is_bot)
        self.assertEqual(feedback.ip_address, '203.0.113.5')
        self.assertEqual(feedback.user_agent, 'Mozilla/5.0 (Test Browser)')

    def test_subsequent_step_does_not_overwrite_ip_or_user_agent(self):
        link = self._create_feedback_link()
        questions = list(link.questions.order_by('order').all())
        q1 = questions[0]
        q2 = questions[1]
        self.client.post(
            reverse('session_feedback_step', args=[link.token, 1]),
            {f'q_{q1.pk}': '4', 'email2': ''},
            REMOTE_ADDR='203.0.113.5', HTTP_USER_AGENT='BrowserA',
        )
        feedback = SessionFeedback.objects.get(feedback_link=link)
        pk = feedback.pk
        self.assertEqual(feedback.ip_address, '203.0.113.5')
        self.assertEqual(feedback.user_agent, 'BrowserA')
        # Step 2 from a different IP/UA — must not overwrite
        self.client.post(
            reverse('session_feedback_step', args=[link.token, 2]),
            {f'q_{q2.pk}': '4', 'email2': ''},
            REMOTE_ADDR='198.51.100.7', HTTP_USER_AGENT='BrowserB',
        )
        feedback.refresh_from_db()
        self.assertEqual(feedback.pk, pk)
        self.assertEqual(feedback.ip_address, '203.0.113.5')
        self.assertEqual(feedback.user_agent, 'BrowserA')

    def test_full_wizard_flow_creates_complete_feedback(self):
        link = self._create_feedback_link()
        attend_q = link.questions.get(question_text='Would you attend another session like this?')
        duration_q = link.questions.get(question_text='If yes, what would be the ideal duration?')
        comments_q = link.questions.get(question_text='Any other comments or feedback?')

        # Steps 1-7: rating/text questions (always visible before the branch point)
        for order in range(1, 8):
            q = link.questions.get(order=order)
            data = {'email2': '', f'q_{q.pk}': '5' if q.question_type == 'rating' else 'Great'}
            response = self.client.post(
                reverse('session_feedback_step', args=[link.token, order]), data)
            self.assertEqual(response.status_code, 302)

        # Step 8: answer "yes" → reveals the ideal-duration branch
        response = self.client.post(
            reverse('session_feedback_step', args=[link.token, 8]),
            {f'q_{attend_q.pk}': 'yes', 'email2': ''})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('session_feedback_step', args=[link.token, 9]))

        # Step 9: ideal duration (visible because Q8="yes")
        response = self.client.post(
            reverse('session_feedback_step', args=[link.token, 9]),
            {f'q_{duration_q.pk}': '4 hours', 'email2': ''})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('session_feedback_step', args=[link.token, 10]))

        # Step 10: comments (last visible step → success)
        response = self.client.post(
            reverse('session_feedback_step', args=[link.token, 10]),
            {f'q_{comments_q.pk}': 'Great session!', 'email2': ''})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('session_feedback_success', args=[link.token]))

        feedback = SessionFeedback.objects.get(feedback_link=link)
        self.assertEqual(feedback.responses[str(duration_q.pk)], '4 hours')
        self.assertEqual(feedback.responses[str(comments_q.pk)], 'Great session!')
        why_not_q = link.questions.get(question_text='Why not? (cost, travel time, etc)')
        self.assertNotIn(str(why_not_q.pk), feedback.responses)

    def test_back_button_prefills_saved_answer(self):
        link = self._create_feedback_link()
        q = link.questions.order_by('order').first()

        # Answer step 1
        self.client.post(
            reverse('session_feedback_step', args=[link.token, 1]),
            {f'q_{q.pk}': '5', 'email2': ''},
        )

        # Go back to step 1 — should show the saved answer pre-selected
        response = self.client.get(reverse('session_feedback_step', args=[link.token, 1]))
        self.assertEqual(response.status_code, 200)

        feedback = SessionFeedback.objects.get(feedback_link=link)
        self.assertEqual(feedback.responses[str(q.pk)], '5')

    # --- Conditional question tests ---

    def test_why_not_in_default_questions(self):
        texts = [q['question_text'] for q in DEFAULT_FEEDBACK_QUESTIONS]
        self.assertIn('Why not? (cost, travel time, etc)', texts)

    def test_sync_default_questions_resolves_conditionals(self):
        link = SessionFeedbackLink.objects.create(dojo=self.dojo, session=self.session)
        sync_default_questions(link)
        attend_q = link.questions.get(question_text='Would you attend another session like this?')
        duration_q = link.questions.get(question_text='If yes, what would be the ideal duration?')
        why_not_q = link.questions.get(question_text='Why not? (cost, travel time, etc)')
        self.assertEqual(duration_q.conditional_parent_id, attend_q.pk)
        self.assertEqual(duration_q.conditional_answer, 'yes')
        self.assertEqual(why_not_q.conditional_parent_id, attend_q.pk)
        self.assertEqual(why_not_q.conditional_answer, 'no')

    def test_conditional_branch_hidden_before_parent_answered(self):
        link = self._create_feedback_link()
        why_not_q = link.questions.get(question_text='Why not? (cost, travel time, etc)')
        duration_q = link.questions.get(question_text='If yes, what would be the ideal duration?')
        comments_q = link.questions.get(question_text='Any other comments or feedback?')
        # No Q8 answer yet — step 9 is the comments question, not a branch question
        response = self.client.get(reverse('session_feedback_step', args=[link.token, 9]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, comments_q.question_text)
        self.assertNotContains(response, why_not_q.question_text)
        self.assertNotContains(response, duration_q.question_text)

    def test_conditional_why_not_shown_when_attend_no(self):
        link = self._create_feedback_link()
        attend_q = link.questions.get(question_text='Would you attend another session like this?')
        why_not_q = link.questions.get(question_text='Why not? (cost, travel time, etc)')
        # Answer Q8 with "no" via step 8
        self.client.post(
            reverse('session_feedback_step', args=[link.token, 8]),
            {f'q_{attend_q.pk}': 'no', 'email2': ''})
        # Step 9 should now show "Why not?" (visible because Q8="no")
        response = self.client.get(reverse('session_feedback_step', args=[link.token, 9]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, why_not_q.question_text)

    def test_conditional_ideal_duration_shown_when_attend_yes(self):
        link = self._create_feedback_link()
        attend_q = link.questions.get(question_text='Would you attend another session like this?')
        duration_q = link.questions.get(question_text='If yes, what would be the ideal duration?')
        self.client.post(
            reverse('session_feedback_step', args=[link.token, 8]),
            {f'q_{attend_q.pk}': 'yes', 'email2': ''})
        response = self.client.get(reverse('session_feedback_step', args=[link.token, 9]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, duration_q.question_text)

    def test_stale_answer_cleared_when_branch_changes(self):
        link = self._create_feedback_link()
        attend_q = link.questions.get(question_text='Would you attend another session like this?')
        duration_q = link.questions.get(question_text='If yes, what would be the ideal duration?')
        # Answer Q8 with "yes"
        self.client.post(
            reverse('session_feedback_step', args=[link.token, 8]),
            {f'q_{attend_q.pk}': 'yes', 'email2': ''})
        # Answer ideal duration
        self.client.post(
            reverse('session_feedback_step', args=[link.token, 9]),
            {f'q_{duration_q.pk}': '4 hours', 'email2': ''})
        feedback = SessionFeedback.objects.get(feedback_link=link)
        self.assertEqual(feedback.responses[str(duration_q.pk)], '4 hours')
        # Go back and change Q8 to "no"
        self.client.post(
            reverse('session_feedback_step', args=[link.token, 8]),
            {f'q_{attend_q.pk}': 'no', 'email2': ''})
        feedback.refresh_from_db()
        self.assertNotIn(str(duration_q.pk), feedback.responses)

    # --- Success page ---

    def test_success_page_renders(self):
        link = self._create_feedback_link()
        response = self.client.get(
            reverse('session_feedback_success', args=[link.token]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Thank You')


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

    def test_manual_create_auto_populates_questions(self):
        self.admin_client.login(username='admin', password='password')
        login_verified(self.admin_client)

        response = self.admin_client.post(
            reverse('admin:shodan_sessionfeedbacklink_add'),
            {
                'dojo': self.dojo.pk,
                'session': self.session.pk,
                'is_active': 'on',
                'questions-TOTAL_FORMS': '0',
                'questions-INITIAL_FORMS': '0',
            },
        )
        self.assertEqual(response.status_code, 302)
        link = SessionFeedbackLink.objects.get(session=self.session)
        self.assertEqual(link.questions.count(), len(DEFAULT_FEEDBACK_QUESTIONS))

    def test_admin_queryset_hides_bots_by_default(self):
        link = SessionFeedbackLink.objects.create(
            dojo=self.dojo, session=self.session,
        )
        real = SessionFeedback.objects.create(
            dojo=self.dojo, feedback_link=link, responses={'1': 'Great'},
        )
        SessionFeedback.objects.create(
            dojo=self.dojo, feedback_link=link, responses={},
            is_bot=True, honeypot_value='x@y.com',
        )

        admin_user = User.objects.get(username='admin')
        factory = RequestFactory()
        ma = SessionFeedbackAdmin(SessionFeedback, django_admin.site)

        # Default (no is_bot filter) → only the real submission
        request = factory.get(reverse('admin:shodan_sessionfeedback_changelist'))
        request.user = admin_user
        qs = ma.get_queryset(request)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, real.pk)

        # With is_bot filter present → both visible
        request = factory.get(reverse('admin:shodan_sessionfeedback_changelist'), {'is_bot': '1'})
        request.user = admin_user
        qs = ma.get_queryset(request)
        self.assertEqual(qs.count(), 2)
