from django.test import TestCase
from django.utils import timezone
from accounts.models import User, UserRole, UserStatus
from projects.models import Project, ProjectStatus, ProjectMember, MemberRole, MemberStatus

class ProjectWorkflowTestCase(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.student = User.objects.create_user(username='leader1', email='l1@vaa.edu.vn', role=UserRole.STUDENT, status=UserStatus.ACTIVE)
        self.mentor = User.objects.create_user(username='mentor1', email='m1@vaa.edu.vn', role=UserRole.MENTOR, status=UserStatus.ACTIVE)

    def _make_project(self, code, **kwargs):
        return Project.objects.create(
            code=code,
            start_date=self.today - timezone.timedelta(days=10),
            end_date=self.today + timezone.timedelta(days=80),
            created_by=self.student,
            **kwargs
        )

    def test_p0_p0_16_project_creation(self):
        proj = self._make_project('PRJ-2026-TEST1', name='Project Test WF', mentor=self.mentor)
        self.assertEqual(proj.code, 'PRJ-2026-TEST1')
        self.assertEqual(proj.mentor, self.mentor)

    def test_project_member_addition(self):
        proj = self._make_project('PRJ-2026-TEST2', name='Project Test Mem')
        mem_user = User.objects.create_user(username='mem1', email='mem1@vaa.edu.vn', role=UserRole.STUDENT)
        pm = ProjectMember.objects.create(project=proj, user=mem_user, role=MemberRole.MEMBER, status=MemberStatus.ACCEPTED)
        self.assertEqual(proj.memberships.count(), 1)
        self.assertEqual(pm.user, mem_user)

    def test_project_progress_calculation(self):
        proj = self._make_project('PRJ-2026-TEST3', name='Project Progress')
        proj.tasks.create(title='T1', status='DONE', created_by=self.student)
        proj.tasks.create(title='T2', status='TODO', created_by=self.student)
        self.assertEqual(proj.progress, 50)
