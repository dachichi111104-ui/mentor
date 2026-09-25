from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from accounts.models import User, UserRole

class PasswordResetTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='reset_user',
            email='reset@test.com',
            password='old_password123',
            role=UserRole.STUDENT
        )

    def test_forgot_password_flow(self):
        # 1. Submit email to forgot-password
        response = self.client.post(reverse('forgot_password'), {'email': 'reset@test.com'})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('password_reset_done'))
        
        # 2. Verify mail was sent
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        self.assertIn('/password-reset/confirm/', email_body)

        # 3. Extract confirm URL from email
        confirm_link = None
        for line in email_body.splitlines():
            if '/password-reset/confirm/' in line:
                confirm_link = line.strip()
                break
        self.assertIsNotNone(confirm_link)

        # 4. Get confirm page (Django 5 redirects token URL to .../set-password/)
        from urllib.parse import urlparse
        confirm_path = urlparse(confirm_link).path
        res_get = self.client.get(confirm_path, follow=True)
        self.assertEqual(res_get.status_code, 200)

        # 5. Submit new password
        set_password_path = res_get.redirect_chain[0][0]
        res_post = self.client.post(set_password_path, {
            'new_password1': 'new_password123',
            'new_password2': 'new_password123'
        })
        self.assertEqual(res_post.status_code, 302)
        self.assertRedirects(res_post, reverse('password_reset_complete'))

        # 6. Verify user can login with new password
        login_res = self.client.post(reverse('login'), {
            'username': 'reset_user',
            'password': 'new_password123'
        })
        self.assertEqual(login_res.status_code, 302)
        self.assertRedirects(login_res, reverse('dashboard'))


class RegistrationRoleTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_as_mentor(self):
        res = self.client.post(reverse('register'), {
            'username': 'new_mentor',
            'email': 'mentor_reg@test.com',
            'first_name': 'Mentor',
            'last_name': 'Test',
            'role': UserRole.MENTOR,
            'password': 'password123',
            'confirm_password': 'password123'
        })
        self.assertEqual(res.status_code, 302)
        created_user = User.objects.get(username='new_mentor')
        self.assertEqual(created_user.role, UserRole.MENTOR)

    def test_register_attempt_admin_role_fails_or_defaults_to_student(self):
        res = self.client.post(reverse('register'), {
            'username': 'fake_admin',
            'email': 'fake_admin@test.com',
            'first_name': 'Fake',
            'last_name': 'Admin',
            'role': 'ADMIN',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        if res.status_code == 302:
            created_user = User.objects.get(username='fake_admin')
            self.assertNotEqual(created_user.role, UserRole.ADMIN)
        else:
            self.assertEqual(res.status_code, 200)
            self.assertFalse(User.objects.filter(username='fake_admin').exists())


class PasswordChangeAndProfileCompletionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='user_change_pass',
            email='change_pass@test.com',
            password='old_password123',
            role=UserRole.STUDENT,
            phone='0912345678',
            department='CNTT'
        )

    def test_change_password_flow(self):
        self.client.login(username='user_change_pass', password='old_password123')
        res = self.client.post(reverse('change_password'), {
            'old_password': 'old_password123',
            'new_password1': 'new_pass_456',
            'new_password2': 'new_pass_456'
        })
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, reverse('profile'))

        # Verify login with new password works
        self.client.logout()
        login_res = self.client.post(reverse('login'), {
            'username': 'user_change_pass',
            'password': 'new_pass_456'
        })
        self.assertEqual(login_res.status_code, 302)

    def test_profile_completion_formula(self):
        comp = self.user.profile_completion
        self.assertEqual(comp['total'], 6)
        self.assertIn('filled', comp)
        self.assertIn('percent', comp)
        self.assertIn('missing', comp)

