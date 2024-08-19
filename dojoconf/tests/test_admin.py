import logging

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

class AdminTest(TestCase):
    def setUp(self):
        # Create a superuser
        self.superuser = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password'
        )

        # Create a client instance
        self.client = Client()
        logging.basicConfig(level=logging.INFO)

    def test_admin_login(self):
        # Login as superuser
        self.client.login(username='admin', password='password')

        # Access admin index page
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)

    def test_admin_change_password(self):
        # Login as superuser
        self.client.login(username='admin', password='password')

        # Access change password page
        response = self.client.get(reverse('admin:password_change'))
        self.assertEqual(response.status_code, 200)

        # Change password
        data = {
            'old_password': 'password',
            'new_password1': 'newpassword',
            'new_password2': 'newpassword'
        }
        response = self.client.post(reverse('admin:password_change'), data)
        logging.info("Password changed. Status code: %s", response.status_code)
        self.assertEqual(response.status_code, 200)

    def test_admin_add_user(self):
        # Login as superuser
        self.admin_client.login(username='admin', password='password')

        # Access add user page
        response = self.admin_client.get(reverse('admin:auth_user_add'))
        self.assertEqual(response.status_code, 200)

        # Add user
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'password',
            'password2': 'password'
        }
        response = self.admin_client.post(reverse('admin:auth_user_add'), data)
        self.assertEqual(response.status_code, 200)