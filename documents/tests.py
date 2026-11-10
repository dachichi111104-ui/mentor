from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User, UserRole
from projects.models import Project, ProjectMember, MemberRole, MentorStatus, MemberStatus
from documents.models import Document, DocumentVersion, FileCategory

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
        
        dummy_file = SimpleUploadedFile("report.pdf", b"%PDF-1.4 initial content", content_type="application/pdf")
        self.doc = Document.objects.create(
            project=self.project,
            uploaded_by=self.student1,
            title='SRS Document',
            file=dummy_file,
            file_type=FileCategory.PDF,
            file_size='1 MB',
            current_version=1
        )
        self.v1 = DocumentVersion.objects.create(
            document=self.doc,
            file=dummy_file,
            version_number=1,
            uploaded_by=self.student1,
            change_log="Khởi tạo ban đầu"
        )

    def test_non_uploader_cannot_delete_document(self):
        self.client.login(username='student2', password='password')
        url = reverse('document_delete', args=[self.doc.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Document.objects.filter(id=self.doc.id).exists())

    def test_uploader_can_delete_document(self):
        self.client.login(username='student1', password='password')
        url = reverse('document_delete', args=[self.doc.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Document.objects.filter(id=self.doc.id).exists())

    def test_upload_new_version_success(self):
        self.client.login(username='student1', password='password')
        url = reverse('document_version_upload', args=[self.doc.id])
        v2_file = SimpleUploadedFile("report_v2.pdf", b"%PDF-1.5 v2 content", content_type="application/pdf")
        response = self.client.post(url, {
            'file': v2_file,
            'change_log': 'Cập nhật sơ đồ kiến trúc v2',
            'title': 'SRS Document Updated',
            'description': 'Mô tả mới'
        })
        self.assertEqual(response.status_code, 302)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.current_version, 2)
        self.assertEqual(self.doc.title, 'SRS Document Updated')
        self.assertEqual(self.doc.description, 'Mô tả mới')
        self.assertEqual(DocumentVersion.objects.filter(document=self.doc).count(), 2)

        v2 = DocumentVersion.objects.get(document=self.doc, version_number=2)
        self.assertEqual(v2.change_log, 'Cập nhật sơ đồ kiến trúc v2')
        self.assertEqual(v2.uploaded_by, self.student1)

    def test_edit_document_metadata(self):
        self.client.login(username='student1', password='password')
        url = reverse('document_edit', args=[self.doc.id])
        response = self.client.post(url, {
            'title': 'SRS Document Final',
            'description': 'Phiên bản cuối cùng nộp hội đồng',
            'file_type': FileCategory.WORD
        })
        self.assertEqual(response.status_code, 302)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.title, 'SRS Document Final')
        self.assertEqual(self.doc.description, 'Phiên bản cuối cùng nộp hội đồng')
        self.assertEqual(self.doc.file_type, FileCategory.WORD)

    def test_mentor_can_edit_document_metadata(self):
        self.client.login(username='mentor', password='password')
        url = reverse('document_edit', args=[self.doc.id])
        response = self.client.post(url, {
            'title': 'SRS Document Mentor Reviewed',
            'description': 'GVHD đã duyệt',
            'file_type': FileCategory.PDF
        })
        self.assertEqual(response.status_code, 302)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.title, 'SRS Document Mentor Reviewed')

    def test_unauthorized_user_cannot_edit_document_metadata(self):
        unauthorized = User.objects.create_user(username='other_student', password='password', role=UserRole.STUDENT)
        self.client.login(username='other_student', password='password')
        url = reverse('document_edit', args=[self.doc.id])
        response = self.client.post(url, {
            'title': 'Hacked Title',
        })
        self.assertEqual(response.status_code, 403)
        self.doc.refresh_from_db()
        self.assertNotEqual(self.doc.title, 'Hacked Title')

    def test_rollback_version(self):
        # First upload v2
        self.client.login(username='student1', password='password')
        url = reverse('document_version_upload', args=[self.doc.id])
        v2_file = SimpleUploadedFile("report_v2.pdf", b"%PDF-1.5 v2 content", content_type="application/pdf")
        self.client.post(url, {
            'file': v2_file,
            'change_log': 'Cập nhật v2'
        })
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.current_version, 2)

        # Leader rolls back to v1
        rollback_url = reverse('document_rollback', args=[self.doc.id, self.v1.id])
        response = self.client.post(rollback_url)
        self.assertEqual(response.status_code, 302)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.current_version, 1)

    def test_preview_and_download_version(self):
        self.client.login(username='student1', password='password')
        preview_url = reverse('document_version_preview', args=[self.v1.id])
        response = self.client.get(preview_url)
        self.assertEqual(response.status_code, 200)

        raw_url = reverse('document_version_raw', args=[self.v1.id])
        response = self.client.get(raw_url)
        self.assertEqual(response.status_code, 200)

        download_url = reverse('document_version_download', args=[self.v1.id])
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, 200)

    def test_document_embed_and_version_embed(self):
        self.client.login(username='student1', password='password')
        embed_url = reverse('document_embed', args=[self.doc.id])
        response = self.client.get(embed_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SRS Document')

        v_embed_url = reverse('document_version_embed', args=[self.v1.id])
        response = self.client.get(v_embed_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SRS Document')

