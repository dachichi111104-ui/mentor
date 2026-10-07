from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from reviews.models import Feedback, ReviewStatus
from projects.models import Project
from projects.permissions import user_can_access_project
from audit_log.models import ActionType
from audit_log.utils import log_action
from notifications.models import Notification, NotificationType

@login_required
def mentor_reviews_view(request):
    user = request.user
    if user.is_mentor:
        feedbacks = Feedback.objects.filter(mentor=user)
        mentored_projects = Project.objects.filter(mentor=user)
    elif user.is_admin_user:
        feedbacks = Feedback.objects.all()
        mentored_projects = Project.objects.all()
    else:
        feedbacks = Feedback.objects.filter(project__memberships__user=user)
        mentored_projects = []
        
    return render(request, 'reviews/review_list.html', {
        'feedbacks': feedbacks,
        'mentored_projects': mentored_projects,
    })

@login_required
def submit_review_view(request, project_id):
    from projects.models import ProjectStatus
    project = get_object_or_404(Project, id=project_id)
    if not (project.mentor == request.user or request.user.is_admin_user):
        return render(request, 'errors/403.html', status=403)

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        rating_raw = request.POST.get('rating', '5')
        status = request.POST.get('status', ReviewStatus.APPROVED)

        try:
            rating = int(rating_raw)
            if rating < 1:
                rating = 1
            elif rating > 5:
                rating = 5
        except (ValueError, TypeError):
            rating = 5

        if status not in ReviewStatus.values:
            status = ReviewStatus.APPROVED

        if not content:
            messages.error(request, 'Vui lòng nhập nội dung đánh giá.')
            return redirect('project_detail', project_id=project.id)

        fb = Feedback.objects.create(
            project=project,
            mentor=request.user,
            content=content,
            rating=rating,
            status=status
        )

        # Update Project Workflow based on review status
        if status == ReviewStatus.APPROVED:
            project.status = ProjectStatus.COMPLETED
            project.save()
        elif status == ReviewStatus.NEEDS_REVISION:
            project.status = ProjectStatus.IN_PROGRESS
            project.save()

        for m in project.memberships.all():
            Notification.objects.create(
                recipient=m.user,
                sender=request.user,
                title=f'Mentor đã gửi nhận xét Review đồ án [{project.code}]',
                message=f'{request.user.display_name} đã gửi đánh giá ({fb.get_status_display()}): "{content[:100]}..."',
                link=f'/projects/{project.id}/',
                notification_type=NotificationType.MENTOR_FEEDBACK
            )

        log_action(
            user=request.user,
            action=ActionType.SUBMIT_REVIEW,
            entity_type='Feedback',
            entity_id=fb.id,
            description=f'Mentor gửi nhận xét cho đồ án {project.name} [{status}] (Đánh giá: {rating} sao)',
            request=request
        )

        messages.success(request, 'Đã gửi đánh giá Review đồ án cho sinh viên!')
    return redirect('project_detail', project_id=project.id)
