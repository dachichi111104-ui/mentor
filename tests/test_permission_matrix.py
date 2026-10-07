from django.test import TestCase
from accounts.models import UserRole, UserStatus
from projects.models import ProjectStatus, MentorStatus
from projects.permissions import can, PERMISSION_MATRIX
from tests.factories import create_test_user, create_test_project

class PermissionMatrixTestCase(TestCase):
    def setUp(self):
        self.admin = create_test_user("admin_perm", role=UserRole.ADMIN)
        self.mentor = create_test_user("mentor_perm", role=UserRole.MENTOR)
        self.leader = create_test_user("leader_perm", role=UserRole.STUDENT)
        self.member = create_test_user("member_perm", role=UserRole.STUDENT)
        self.outsider = create_test_user("outsider_perm", role=UserRole.STUDENT)

        self.project = create_test_project("PRJ-PERM", created_by=self.leader, mentor=self.mentor)

        # Add member to project
        from projects.models import ProjectMember, MemberRole, MemberStatus
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

    def test_outsider_isolation(self):
        """Outsider cannot perform any project action."""
        self.assertFalse(can(self.outsider, 'project.view', self.project))
        self.assertFalse(can(self.outsider, 'task.create', self.project))
        self.assertFalse(can(self.outsider, 'document.upload', self.project))

    def test_admin_self_demote_protection(self):
        """Admin cannot demote or lock self."""
        self.assertFalse(can(self.admin, 'user.demote_self'))
        self.assertFalse(can(self.admin, 'user.lock_self'))
