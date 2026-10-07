from django.test import TestCase
from accounts.models import UserRole, UserStatus
from projects.models import ProjectStatus, MentorStatus, ProjectMember, MemberRole, MemberStatus
from projects.permissions import can, PERMISSION_MATRIX
from tests.factories import create_test_user, create_test_project

class PermissionMatrixTestCase(TestCase):
    def setUp(self):
        self.admin = create_test_user("admin_perm", role=UserRole.ADMIN)
        self.mentor_accepted = create_test_user("mentor_perm", role=UserRole.MENTOR)
        self.mentor_pending = create_test_user("mentor_pen_perm", role=UserRole.MENTOR, status=UserStatus.PENDING_APPROVAL)
        self.leader = create_test_user("leader_perm", role=UserRole.STUDENT)
        self.member = create_test_user("member_perm", role=UserRole.STUDENT)
        self.outsider = create_test_user("outsider_perm", role=UserRole.STUDENT)

        self.project = create_test_project("PRJ-PERM", created_by=self.leader, mentor=self.mentor_accepted)
        ProjectMember.objects.create(
            project=self.project,
            user=self.member,
            role=MemberRole.MEMBER,
            status=MemberStatus.ACCEPTED
        )

    def test_permission_matrix_integrity(self):
        """Verifies every action in PERMISSION_MATRIX yields valid boolean answers."""
        for action in PERMISSION_MATRIX:
            res_admin = can(self.admin, action, self.project)
            res_leader = can(self.leader, action, self.project)
            res_member = can(self.member, action, self.project)
            res_outsider = can(self.outsider, action, self.project)

            self.assertIsInstance(res_admin, bool)
            self.assertIsInstance(res_leader, bool)
            self.assertIsInstance(res_member, bool)
            self.assertIsInstance(res_outsider, bool)

    def test_unknown_action_returns_false(self):
        """Typo or unknown action string returns False without crashing."""
        self.assertFalse(can(self.admin, 'non_existent_action_xyz', self.project))
        self.assertFalse(can(self.leader, 'task.unknown', self.project))

    def test_outsider_isolation(self):
        """Outsider cannot perform any project action."""
        self.assertFalse(can(self.outsider, 'project.view', self.project))
        self.assertFalse(can(self.outsider, 'task.create', self.project))
        self.assertFalse(can(self.outsider, 'document.upload', self.project))

    def test_admin_self_demote_protection(self):
        """Admin cannot demote or lock self."""
        self.assertFalse(can(self.admin, 'user.demote_self'))
        self.assertFalse(can(self.admin, 'user.lock_self'))

    def test_mentor_approval_permissions(self):
        """Admin can approve mentor; students and mentors cannot."""
        self.assertTrue(can(self.admin, 'user.approve_mentor'))
        self.assertFalse(can(self.leader, 'user.approve_mentor'))
        self.assertFalse(can(self.mentor_accepted, 'user.approve_mentor'))

    def test_project_archive_permissions(self):
        """Only admin can archive project."""
        self.assertTrue(can(self.admin, 'project.archive', self.project))
        self.assertFalse(can(self.leader, 'project.archive', self.project))
        self.assertFalse(can(self.member, 'project.archive', self.project))
        self.assertFalse(can(self.outsider, 'project.archive', self.project))
