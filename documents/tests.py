from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User, UserRole
from projects.models import Project, ProjectMember, MemberRole, MentorStatus, MemberStatus
from documents.models import Document, FileCategory

class DocumentPermissionTests(TestCase):
    def setUp(self):
        self.student1 = User.objects.create_user(username='student1', password='password', role=UserRole.STUDENT)
        self.student2 = User.objects.create_user(username='student2', password='password', role=UserRole.STUDENT)
        self.mentor = User.objects.create_user(username='mentor', password='password', role=UserRole.MENTOR)
        
        self.project = Project.objects.create(
            name='Doc Project',
            code='PRJ-DOC',
            description='Test Desc',
            technology='Python',
            start_date='2026-01-01',
            end_date='2026-12-31',
            created_by=self.student1,
            mentor=self.mentor,
            mentor_status=MentorStatus.ACCEPTED
        )
        ProjectMember.objects.create(project=self.project, user=self.student1, role=MemberRole.LEADER, status=MemberStatus.ACCEPTED)
        ProjectMember.objects.create(project=self.project, user=self.student2, role=MemberRole.MEMBER, status=MemberStatus.ACCEPTED)
        
        dummy_file = SimpleUploadedFile("report.pdf", b"file_content", content_type="application/pdf")
        self.doc = Document.objects.create(
            project=self.project,
            uploaded_by=self.student1,
            title='SRS Document',
            file=dummy_file,
            file_type=FileCategory.PDF,
            file_size='1 MB',
            current_version=1
        )

    def test_non_uploader_cannot_delete_document(self):
        self.client.login(username='student2', password='password')
        url = reverse('document_delete', args=[self.doc.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Document.objects.filter(id=self.doc.id).exists())

    def test_uploader_can_delete_document(self):
        self.client.login(username='student1', password='password')
        url = reverse('document_delete', args=[self.doc.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Document.objects.filter(id=self.doc.id).exists())
