from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole, UserStatus
from projects.models import Project, ProjectStatus, MentorStatus
from tasks.models import Task, TaskStatus
from milestones.models import Milestone, MilestoneStatus
from reviews.models import Feedback, ReviewStatus
from tests.factories import create_test_user, create_test_project

class RegressionsVong3TestCase(TestCase):
    def setUp(self):
        self.admin = create_test_user("admin_user", role=UserRole.ADMIN)
        self.mentor = create_test_user("mentor_user", role=UserRole.MENTOR)
        self.leader = create_test_user("leader_user", role=UserRole.STUDENT)
        self.member = create_test_user("member_user", role=UserRole.STUDENT)

        self.project = create_test_project("PRJ-REG", created_by=self.leader, mentor=self.mentor)

    def test_p0_1_review_status_enum(self):
        """P0-1: ReviewStatus.NEED_REVISION exists and handles review feedback properly."""
        self.client.force_login(self.mentor)
        self.project.status = ProjectStatus.REVIEW
        self.project.save()

        url = reverse('submit_review', kwargs={'project_id': self.project.id})
        res = self.client.post(url, {
            'content': 'Cần bổ sung tài liệu kiến trúc',
            'rating': 3,
            'status': ReviewStatus.NEED_REVISION
        })
        self.assertEqual(res.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, ProjectStatus.IN_PROGRESS)
        self.assertEqual(Feedback.objects.count(), 1)

    def test_p0_3_strftime_in_context(self):
        """P0-3: context.py strftime uses %M without raising ValueError."""
        from ai_assistant.facts_builder import build_facts
        facts = build_facts(self.project)
        self.assertIn('project', facts)

    def test_p0_5_mentor_pending_permissions(self):
        """P0-5: Mentor PENDING status cannot manage tasks or approve reviews."""
        pending_project = create_test_project("PRJ-PEND", created_by=self.leader, mentor=self.mentor, mentor_status=MentorStatus.PENDING)
        from projects.permissions import can
        self.assertTrue(can(self.mentor, 'project.view', pending_project))
        self.assertTrue(can(self.mentor, 'project.accept_mentor', pending_project))
        self.assertFalse(can(self.mentor, 'task.create', pending_project))
        self.assertFalse(can(self.mentor, 'review.submit', pending_project))

    def test_p0_6_task_reorder_validation(self):
        """P0-6: task_reorder validates order_index and enforces state machine transitions."""
        t = Task.objects.create(project=self.project, title="Task Reorder Test", created_by=self.leader)
        self.client.force_login(self.member)
        url = reverse('task_reorder')

        # Regular member attempting invalid direct move to DONE -> 403 Forbidden
        res = self.client.post(url, {'task_id': t.id, 'status': TaskStatus.DONE, 'order_index': 'abc'})
        self.assertEqual(res.status_code, 403)

    def test_p0_8_no_login_backdoor(self):
        """P0-8: Fallback login map is completely removed."""
        res = self.client.post(reverse('login'), {'username': 'student1', 'password': 'invalidpassword999'})
        self.assertEqual(res.status_code, 200) # Re-renders login form with error
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_p0_11_avatar_file_not_found(self):
        """P0-11: Avatar view handles missing file gracefully."""
        self.client.force_login(self.leader)
        url = reverse('user_avatar', kwargs={'user_id': self.leader.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)

    def test_p0_15_post_required_for_data_mutations(self):
        """P0-15: GET request to delete milestone returns 405 Method Not Allowed."""
        ms = Milestone.objects.create(project=self.project, name="M1 Test", start_date=timezone.localdate(), due_date=timezone.localdate())
        self.client.force_login(self.leader)
        url = reverse('milestone_delete', kwargs={'milestone_id': ms.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 405)
        self.assertTrue(Milestone.objects.filter(id=ms.id).exists())
