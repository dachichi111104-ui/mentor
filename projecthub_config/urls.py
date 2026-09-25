from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from accounts import views as account_views
from dashboard import views as dashboard_views
from projects import views as project_views
from tasks import views as task_views
from milestones import views as milestone_views
from documents import views as document_views
from reviews import views as review_views
from notifications import views as notification_views
from ai_assistant import views as ai_views

from django.contrib.auth import views as auth_views

urlpatterns = [
    path('django-admin/', admin.site.urls),

    # Dashboard & Landing
    path('', dashboard_views.landing_view, name='landing'),
    path('dashboard/', dashboard_views.dashboard_view, name='dashboard'),
    path('admin/users/', dashboard_views.admin_users_view, name='admin_users'),
    path('admin/users/<int:user_id>/toggle-status/', dashboard_views.admin_toggle_user_status_view, name='admin_toggle_user_status'),
    path('admin/audit-logs/', dashboard_views.admin_audit_log_view, name='admin_audit_log'),
    path('search/', dashboard_views.global_search_view, name='global_search'),

    # Accounts & Auth
    path('login/', account_views.login_view, name='login'),
    path('register/', account_views.register_view, name='register'),
    path('logout/', account_views.logout_view, name='logout'),
    path('profile/', account_views.profile_view, name='profile'),
    path('profile/change-password/', account_views.change_password_view, name='change_password'),
    path('users/<int:user_id>/avatar/', account_views.avatar_view, name='user_avatar'),
    path('forgot-password/', account_views.forgot_password_view, name='forgot_password'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url='/password-reset/complete/'
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),

    # Projects
    path('projects/', project_views.project_list_view, name='project_list'),
    path('projects/create/', project_views.project_create_view, name='project_create'),
    path('projects/<int:project_id>/', project_views.project_detail_view, name='project_detail'),
    path('projects/<int:project_id>/edit/', project_views.project_edit_view, name='project_edit'),
    path('projects/<int:project_id>/members/add/', project_views.project_add_member_view, name='project_add_member'),
    path('projects/<int:project_id>/member-accept/', project_views.project_member_accept_view, name='project_member_accept'),
    path('projects/<int:project_id>/mentor-accept/', project_views.project_mentor_accept_view, name='project_mentor_accept'),
    path('projects/<int:project_id>/mentor-reject/', project_views.project_mentor_reject_view, name='project_mentor_reject'),

    # Tasks & Kanban Board
    path('projects/<int:project_id>/tasks/', task_views.project_tasks_view, name='project_tasks'),
    path('my-tasks/', task_views.my_tasks_view, name='my_tasks'),
    path('projects/<int:project_id>/tasks/create/', task_views.task_create_view, name='task_create'),
    path('tasks/<int:task_id>/update-status/', task_views.task_update_status_view, name='task_update_status'),
    path('tasks/<int:task_id>/comment/', task_views.task_comment_view, name='task_comment'),

    # Milestones
    path('projects/<int:project_id>/milestones/', milestone_views.project_milestones_view, name='project_milestones'),
    path('projects/<int:project_id>/milestones/create/', milestone_views.milestone_create_view, name='milestone_create'),
    path('milestones/<int:milestone_id>/delete/', milestone_views.milestone_delete_view, name='milestone_delete'),

    # Documents
    path('projects/<int:project_id>/documents/', document_views.project_documents_view, name='project_documents'),
    path('documents/all/', document_views.all_documents_view, name='document_list'),
    path('projects/<int:project_id>/documents/upload/', document_views.document_upload_view, name='document_upload'),
    path('documents/<int:document_id>/version/upload/', document_views.document_version_upload_view, name='document_version_upload'),
    path('documents/<int:document_id>/delete/', document_views.document_delete_view, name='document_delete'),
    path('documents/<int:document_id>/download/', document_views.document_download_view, name='document_download'),
    path('documents/<int:document_id>/view/', document_views.document_preview_view, name='document_preview'),
    path('documents/<int:document_id>/raw/', document_views.document_raw_view, name='document_raw'),
    path('documents/version/<int:version_id>/download/', document_views.document_version_download_view, name='document_version_download'),
    path('documents/version/<int:version_id>/view/', document_views.document_version_preview_view, name='document_version_preview'),
    path('documents/version/<int:version_id>/raw/', document_views.document_version_raw_view, name='document_version_raw'),

    # Reviews & Feedbacks
    path('reviews/', review_views.mentor_reviews_view, name='mentor_reviews'),
    path('projects/<int:project_id>/reviews/create/', review_views.submit_review_view, name='submit_review'),

    # Notifications
    path('notifications/', notification_views.notification_center_view, name='notification_center'),
    path('notifications/unread-count/', notification_views.unread_count_ajax, name='notification_unread_count'),
    path('notifications/<int:notif_id>/read/', notification_views.notification_mark_read_view, name='notification_mark_read'),
    path('notifications/read-all/', notification_views.notification_mark_all_read_view, name='notification_mark_all_read'),

    # AI Assistant
    path('ai/assistant/', ai_views.ai_assistant_page_view, name='ai_assistant_page'),
    path('ai/task-breakdown/', ai_views.ai_task_breakdown_ajax, name='ai_task_breakdown'),
    path('ai/accept-tasks/', ai_views.ai_accept_tasks_ajax, name='ai_accept_tasks'),
    path('ai/weekly-summary/', ai_views.ai_weekly_summary_ajax, name='ai_weekly_summary'),
    path('ai/risk-detection/', ai_views.ai_risk_detection_ajax, name='ai_risk_detection'),
    path('ai/mentor-questions/', ai_views.ai_mentor_questions_ajax, name='ai_mentor_questions'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
