import logging
from django.contrib.auth.models import Group

from django.contrib.auth.handlers.modwsgi import groups_for_user
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from sqlparse.engine.grouping import group

from dojoconf.models import Dojo
from dojoconf.tests.utils import print_form_errors_from_response


class DojoTest(TestCase):

    # TODO fix bad dependency. 
    # fixtures = ['fixtures/auth_groups_data.json']

    def setUp(self):
        logging.basicConfig(level=logging.INFO)


    #     # Create a superuser
    #     self.superuser = get_user_model().objects.create_superuser(
    #         username='admin',
    #         email='admin@example.com',
    #         password='password'
    #     )
    #
    #     # Create a client instance
    #     self.admin_client = Client()
    #     self.staff_user1_client = Client()
    #     self.staff_user2_client = Client()
    #
    #     staff_group = Group.objects.get(name='dojostaff')
    #
    #     # Create a staff user
    #     self.staff_user1 = get_user_model().objects.create_user(
    #         username='dojo1staff',
    #         email='dojo1staff@dojo1.com',
    #         password='dojo1staffpwd',
    #         is_staff=True
    #     )
    #     self.staff_user1.groups.set([staff_group])
    #
    #     # Create a another user
    #     self.staff_user2 = get_user_model().objects.create_user(
    #         username='dojo2staff',
    #         email='dojo2staff@dojo2.com',
    #         password='dojo2staffpwd',
    #         is_staff=True
    #     )
    #     self.staff_user2.groups.set([staff_group])
    #
    # def test_admin_create_dojo(self):
    #     self.admin_client.login(username='admin', password='password')
    #
    #     # access to dojo add
    #     response = self.admin_client.get(reverse('admin:dojoconf_dojo_add'))
    #     self.assertEqual(response.status_code, 200)
    #
    #     # Create a dojo
    #     # Prepare form data
    #     data = {
    #         'name': 'Dojo1',
    #         'email': 'dojo1@dojo1.com',
    #         'timezone': 'Australia/Adelaide',
    #         'users': self.staff_user1.pk
    #     }
    #
    #     # Post form data to book add page
    #     response = self.admin_client.post(reverse('admin:dojoconf_dojo_add'), data)
    #
    #     if response.context:
    #         print_form_errors_from_response(response)
    #         self.assertEqual(len(response.context['adminform'].errors.items()), 0)
    #
    #     # Check response status code
    #     self.assertEqual(response.status_code, 302)
    #
    #
    #     # Check book instance created
    #     self.assertTrue(Dojo.objects.filter(name='Dojo1').exists())
    #
    # def test_staff_list_dojo(self):
    #
    #     self.admin_client.login(username='admin', password='password')
    #     self.staff_user1_client.login(username='dojo1staff', password='dojo1staffpwd')
    #     self.staff_user2_client.login(username='dojo2staff', password='dojo2staffpwd')
    #
    #     logging.info(f"Number of dojos: {len(Dojo.objects.all())}")
    #
    #     # check dojo list, admin see no dojo
    #     response = self.admin_client.get(reverse('admin:dojoconf_dojo_changelist'))
    #     self.assertEqual(response.context['cl'].paginator.count, 0)
    #
    #
    #     # admin adds dojo
    #     data = {
    #         'name': 'Dojo1',
    #         'email': 'dojo1@dojo1.com',
    #         'timezone': 'Australia/Adelaide',
    #         'users': self.staff_user1.pk
    #     }
    #     response = self.admin_client.post(reverse('admin:dojoconf_dojo_add'), data)
    #     self.assertEqual(response.status_code, 302)
    #
    #     # admin see one dojo now
    #     response = self.admin_client.get(reverse('admin:dojoconf_dojo_changelist'))
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(response.context['cl'].paginator.count, 1)
    #
    #     # staff user1 sees one dojo
    #     response = self.staff_user1_client.get(reverse('admin:dojoconf_dojo_changelist'))
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(response.context['cl'].paginator.count, 1)
    #
    #     # staff user2 sees no dojo
    #     response = self.staff_user2_client.get(reverse('admin:dojoconf_dojo_changelist'))
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(response.context['cl'].paginator.count, 0)

