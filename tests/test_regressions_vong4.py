from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, UserRole, UserStatus
from projects.models import Project, ProjectStatus, ProjectMember, MemberRole, MemberStatus, MentorStatus
from tasks.models import Task, TaskStatus, TaskPriority
from reviews.models import Feedback, ReviewStatus
from notifications.models import Notification, NotificationType

class PhaseARegressionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin_v4', email='admin_v4@vaa.edu.vn', password='password123',
            role=UserRole.ADMIN, status=UserStatus.ACTIVE
        )
        self.mentor_accepted = User.objects.create_user(
            username='mentor_acc', email='mentor_acc@vaa.edu.vn', password='password123',
            role=UserRole.MENTOR, status=UserStatus.ACTIVE
        )
        self.mentor_pending = User.objects.create_user(
            username='mentor_pen', email='mentor_pen@vaa.edu.vn', password='password123',
            role=UserRole.MENTOR, status=UserStatus.PENDING_APPROVAL
        )
        self.leader = User.objects.create_user(
            username='student_lead', email='lead@vaa.edu.vn', password='password123',
            role=UserRole.STUDENT, status=UserStatus.ACTIVE
        )
        self.member_accepted = User.objects.create_user(
            username='student_acc', email='acc@vaa.edu.vn', password='password123',
            role=UserRole.STUDENT, status=UserStatus.ACTIVE
        )
        self.member_pending = User.objects.create_user(
            username='student_pen', email='pen@vaa.edu.vn', password='password123',
            role=UserRole.STUDENT, status=UserStatus.ACTIVE
        )
        self.outsider = User.objects.create_user(
            username='student_out', email='out@vaa.edu.vn', password='password123',
            role=UserRole.STUDENT, status=UserStatus.ACTIVE
        )

        self.project = Project.objects.create(
            code='PRJ-V4-A',
            name='Test Project V4',
            description='Test description',
            category='WEB',
            status=ProjectStatus.IN_PROGRESS,
            created_by=self.leader,
            mentor=self.mentor_accepted,
            mentor_status=MentorStatus.ACCEPTED,
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + timezone.timedelta(days=30)
        )
        ProjectMember.objects.create(project=self.project, user=self.leader, role=MemberRole.LEADER, status=MemberStatus.ACCEPTED)
        ProjectMember.objects.create(project=self.project, user=self.member_accepted, role=MemberRole.MEMBER, status=MemberStatus.ACCEPTED)
        ProjectMember.objects.create(project=self.project, user=self.member_pending, role=MemberRole.MEMBER, status=MemberStatus.PENDING)

        self.task = Task.objects.create(
            project=self.project,
            title='Task V4 Initial',
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            created_by=self.leader
        )

    def test_a1_celery_task_import(self):
        """A1: Ensure ai_assistant.tasks can be imported cleanly without missing functions."""
        try:
            import ai_assistant.tasks as ai_tasks
            self.assertTrue(hasattr(ai_tasks, 'generate_weekly_summaries_task'))
        except ImportError as e:
            self.fail(f"ai_assistant.tasks import failed: {e}")

    def test_a2_pending_mentor_cannot_submit_review(self):
        """A2: Mentor in PENDING status or outsider mentor cannot submit review."""
        self.project.mentor = self.mentor_pending
        self.project.mentor_status = MentorStatus.PENDING
        self.project.save()

        self.client.login(username='mentor_pen', password='password123')
        url = reverse('submit_review', args=[self.project.id])
        res = self.client.post(url, {'content': 'Attempt review', 'rating': 5, 'status': ReviewStatus.APPROVED})
        self.assertIn(res.status_code, [302, 403])
        self.assertEqual(Feedback.objects.filter(project=self.project).count(), 0)

    def test_a3_in_progress_project_review_rejected(self):
        """A3: Sending APPROVED feedback on IN_PROGRESS project does not set project to COMPLETED."""
        self.client.login(username='mentor_acc', password='password123')
        url = reverse('submit_review', args=[self.project.id])
        res = self.client.post(url, {'content': 'Great work', 'rating': 5, 'status': ReviewStatus.APPROVED})
        self.project.refresh_from_db()
        self.assertNotEqual(self.project.status, ProjectStatus.COMPLETED)
        # Feedback saved as PENDING comment since project wasn't in REVIEW state
        fb = Feedback.objects.filter(project=self.project).first()
        self.assertIsNotNone(fb)
        self.assertEqual(fb.status, ReviewStatus.PENDING)

    def test_a5_pending_member_no_notification(self):
        """A5: Pending member does not receive review notification."""
        self.project.status = ProjectStatus.REVIEW
        self.project.save()

        self.client.login(username='mentor_acc', password='password123')
        url = reverse('submit_review', args=[self.project.id])
        self.client.post(url, {'content': 'Review for review state', 'rating': 5, 'status': ReviewStatus.APPROVED})

        notif_pending = Notification.objects.filter(recipient=self.member_pending).count()
        notif_accepted = Notification.objects.filter(recipient=self.member_accepted).count()
        self.assertEqual(notif_pending, 0)
        self.assertGreaterEqual(notif_accepted, 1)

    def test_a8_leader_submit_review_and_admin_archive(self):
        """A8: Leader submits review to set REVIEW status; Admin archives project."""
        self.client.login(username='student_lead', password='password123')
        url_submit = reverse('project_submit_review', args=[self.project.id])
        res_submit = self.client.post(url_submit)
        self.assertEqual(res_submit.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, ProjectStatus.REVIEW)

        self.client.login(username='admin_v4', password='password123')
        url_archive = reverse('project_archive', args=[self.project.id])
        res_archive = self.client.post(url_archive)
        self.assertEqual(res_archive.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, ProjectStatus.ARCHIVED)

    def test_a9_feedback_acknowledgement(self):
        """A9: Feedback acknowledgement endpoint marks acknowledged_at."""
        fb = Feedback.objects.create(
            project=self.project,
            mentor=self.mentor_accepted,
            content='Need revision details',
            rating=3,
            status=ReviewStatus.NEED_REVISION
        )
        self.client.login(username='student_lead', password='password123')
        url_ack = reverse('feedback_ack', args=[fb.id])
        res = self.client.post(url_ack)
        self.assertEqual(res.status_code, 200)
        fb.refresh_from_db()
        self.assertIsNotNone(fb.acknowledged_at)
        self.assertEqual(fb.acknowledged_by, self.leader)

    def test_a11_get_requests_on_modifying_routes_rejected(self):
        """A11: Modifying routes reject GET requests with 405 Method Not Allowed."""
        self.client.login(username='student_lead', password='password123')
        notif = Notification.objects.create(
            recipient=self.leader, sender=self.mentor_accepted, title='Test', message='Msg'
        )
        url = reverse('notification_mark_read', args=[notif.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 405)
