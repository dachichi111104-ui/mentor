from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, UserRole
from projects.models import Project, ProjectStatus, ProjectCategory
from datetime import date, timedelta

class ProjectPermissionTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Student 1 (Project Creator / Leader)
        self.student1 = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            password='password123',
            role=UserRole.STUDENT
        )
        
        # Student 2 (Non-member)
        self.student2 = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            password='password123',
            role=UserRole.STUDENT
        )
        
        # Mentor
        self.mentor = User.objects.create_user(
            username='mentor',
            email='mentor@test.com',
            password='password123',
            role=UserRole.MENTOR
        )

        # Create Project belonging to Student 1
        self.project = Project.objects.create(
            name='Test Project Alpha',
            code='PROJ-TEST-01',
            description='Test Description',
            category=ProjectCategory.WEB,
            technology='Django, Python',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status=ProjectStatus.IN_PROGRESS,
            created_by=self.student1,
            mentor=self.mentor
        )

    def test_public_registration_defaults_to_student(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username='newuser')
        self.assertEqual(new_user.role, UserRole.STUDENT)

    def test_project_member_can_access_project_detail(self):
        self.client.login(username='student1', password='password123')
        response = self.client.get(reverse('project_detail', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)

    def test_non_member_cannot_access_project_detail(self):
        self.client.login(username='student2', password='password123')
        response = self.client.get(reverse('project_detail', args=[self.project.id]))
        self.assertEqual(response.status_code, 403)

    def test_non_member_cannot_access_kanban(self):
        self.client.login(username='student2', password='password123')
        response = self.client.get(reverse('project_tasks', args=[self.project.id]))
        self.assertEqual(response.status_code, 403)

    def test_create_project_with_mentor_sets_pending_status(self):
        self.client.login(username='student1', password='password123')
        from projects.models import MentorStatus
        response = self.client.post(reverse('project_create'), {
            'name': 'New Project Beta',
            'code': 'PROJ-TEST-02',
            'description': 'Description Beta',
            'category': 'WEB',
            'technology': 'Python, Django',
            'start_date': str(date.today()),
            'end_date': str(date.today() + timedelta(days=30)),
            'status': 'PLANNING',
            'mentor': self.mentor.id
        })
        self.assertEqual(response.status_code, 302)
        created_p = Project.objects.get(code='PROJ-TEST-02')
        self.assertEqual(created_p.mentor, self.mentor)
        self.assertEqual(created_p.mentor_status, MentorStatus.PENDING)

    def test_mentor_pending_vs_accepted_projects_split(self):
        from projects.models import MentorStatus
        p_pending = Project.objects.create(
            name='Pending Mentor Project',
            code='PROJ-PENDING',
            description='Test',
            category=ProjectCategory.WEB,
            technology='Python',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status=ProjectStatus.PLANNING,
            created_by=self.student1,
            mentor=self.mentor,
            mentor_status=MentorStatus.PENDING
        )
        p_accepted = Project.objects.create(
            name='Accepted Mentor Project',
            code='PROJ-ACCEPTED',
            description='Test',
            category=ProjectCategory.WEB,
            technology='Python',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status=ProjectStatus.IN_PROGRESS,
            created_by=self.student1,
            mentor=self.mentor,
            mentor_status=MentorStatus.ACCEPTED
        )
        self.client.login(username='mentor', password='password123')
        
        # Test Mentor Dashboard context
        res_dash = self.client.get(reverse('dashboard'))
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(p_accepted, res_dash.context['mentored_projects_list'])
        self.assertNotIn(p_pending, res_dash.context['mentored_projects_list'])
        self.assertIn(p_pending, res_dash.context['pending_mentor_invites'])
        
        # Test Project List context
        res_list = self.client.get(reverse('project_list'))
        self.assertEqual(res_list.status_code, 200)
        self.assertIn(p_accepted, res_list.context['projects'])
        self.assertNotIn(p_pending, res_list.context['projects'])
        self.assertIn(p_pending, res_list.context['pending_invites'])
