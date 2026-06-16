from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from django_otp.plugins.otp_static.models import StaticDevice
from two_factor.views.mixins import OTPRequiredMixin

from dojoconf.tests.utils import login_verified

User = get_user_model()


class TwoFactorEnforcementTest(TestCase):
    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(username='admin')

    def test_anonymous_admin_redirects_to_two_factor_login(self):
        resp = self.client.get('/admin/', follow=True)
        # Django admin redirects via /admin/login/ which then redirects to the
        # two_factor login (the patched AdminSite.login). Follow the chain.
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            any('/account/login/' in url for url, _ in resp.redirect_chain),
            resp.redirect_chain,
        )

    def test_unverified_staff_is_blocked_from_admin(self):
        # Authenticated but not OTP-verified must be funnelled to two_factor login.
        self.client.login(username='admin', password='password')
        resp = self.client.get('/admin/', follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            any('/account/login/' in url for url, _ in resp.redirect_chain),
            resp.redirect_chain,
        )

    def test_admin_is_recognized_as_otp_view(self):
        # This is what makes the login wizard funnel a no-device user to setup.
        self.assertTrue(OTPRequiredMixin.is_otp_view('/admin/'))

    def test_setup_wizard_renders_for_unverified_user(self):
        # Authenticated but unverified staff must be able to open the setup page.
        self.client.login(username='admin', password='password')
        resp = self.client.get(reverse('two_factor:setup'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'two_factor/core/setup.html')

    def test_verified_staff_can_access_admin(self):
        login_verified(self.client)
        resp = self.client.get('/admin/')
        self.assertEqual(resp.status_code, 200)

    def test_backup_reveal_requires_verification(self):
        self.client.login(username='admin', password='password')
        resp = self.client.get(reverse('backup_reveal'))
        self.assertEqual(resp.status_code, 302)

    def test_backup_reveal_generates_and_shows_codes(self):
        login_verified(self.client)
        resp = self.client.get(reverse('backup_reveal'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'two_factor/backup_reveal.html')
        device = StaticDevice.objects.get(user=self.user)
        self.assertEqual(device.token_set.count(), 10)
        self.assertContains(resp, device.token_set.first().token)

    def test_backup_reveal_is_idempotent(self):
        login_verified(self.client)
        self.client.get(reverse('backup_reveal'))
        self.client.get(reverse('backup_reveal'))
        # Revisiting must not keep minting new codes.
        self.assertEqual(StaticDevice.objects.get(user=self.user).token_set.count(), 10)

    def test_protected_file_requires_verification(self):
        self.client.login(username='admin', password='password')
        resp = self.client.get(reverse('protected_file', args=['dojo_1/fake.png']))
        self.assertEqual(resp.status_code, 302)

    def test_protected_file_accessible_when_verified(self):
        login_verified(self.client)
        resp = self.client.get(reverse('protected_file', args=['dojo_1/fake.png']))
        # No file on disk -> 404, but the OTP gate itself passed (not a 302).
        self.assertEqual(resp.status_code, 404)


class StudentPortalUnaffectedTest(TestCase):
    """Student and kiosk tracks are passwordless/PIN by design (HLD M5, U9)
    and must never be funnelled into the staff two-factor flow."""

    fixtures = ['fixtures/auth_test_data.json', 'fixtures/dojoconf_test_data.json']

    def setUp(self):
        self.client = Client()

    def test_student_login_not_behind_two_factor(self):
        resp = self.client.get(reverse('student_login'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('/account/', getattr(resp, 'url', ''))
