from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django.core.cache import cache
from django.utils import timezone
from django.http import JsonResponse

from reviews.models import Feedback, ReviewStatus
from projects.models import Project, ProjectStatus, MentorStatus, MemberStatus
from projects.permissions import visible_projects, can, require_can
from projects.workflow import apply_project_review
from audit_log.models import ActionType
from audit_log.utils import log_action
from notifications.services import notify
from notifications.models import NotificationType

@login_required
def mentor_reviews_view(request):
    user = request.user
    feedbacks = Feedback.objects.filter(project__in=visible_projects(user)).select_related('project', 'mentor', 'task', 'milestone').distinct()
    
    if user.is_mentor:
        mentored_projects = Project.objects.filter(mentor=user, mentor_status=MentorStatus.ACCEPTED)
    elif user.is_admin_user:
        mentored_projects = Project.objects.all()
    else:
        mentored_projects = []
        
    return render(request, 'reviews/review_list.html', {
        'feedbacks': feedbacks,
        'mentored_projects': mentored_projects,
    })

@login_required
@require_POST
def submit_review_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if not can(request.user, 'review.submit', project):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền đánh giá đồ án này.'}, status=403)
        return render(request, 'errors/403.html', status=403)

    if not (project.mentor == request.user and project.mentor_status == MentorStatus.ACCEPTED) and not request.user.is_admin_user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'status': 'error', 'message': 'Chỉ Mentor đã chấp nhận hướng dẫn hoặc Admin mới được gửi review.'}, status=403)
        messages.error(request, 'Chỉ Mentor đã chấp nhận hướng dẫn hoặc Admin mới được gửi review.')
        return redirect('project_detail', project_id=project.id)

    # Anti-double submission lock (5 seconds)
    lock_key = f"review_lock:{project.id}:{request.user.id}"
    if not cache.add(lock_key, "1", timeout=5):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Thao tác quá nhanh. Vui lòng thử lại sau vài giây.'}, status=400)
        messages.warning(request, 'Thao tác quá nhanh. Vui lòng thử lại sau vài giây.')
        return redirect('project_detail', project_id=project.id)

    try:
        content = request.POST.get('content', '').strip()
        rating_raw = request.POST.get('rating', '5')
        review_result_status = request.POST.get('status', ReviewStatus.APPROVED)

        # A6: Validate rating explicitly
        try:
            rating = int(rating_raw)
            if rating < 1 or rating > 5:
                messages.error(request, 'Đánh giá phải từ 1 đến 5 sao.')
                return redirect('project_detail', project_id=project.id)
        except (ValueError, TypeError):
            messages.error(request, 'Điểm đánh giá không hợp lệ.')
            return redirect('project_detail', project_id=project.id)

        if review_result_status not in ReviewStatus.values:
            messages.error(request, 'Kết quả đánh giá không hợp lệ.')
            return redirect('project_detail', project_id=project.id)

        if not content:
            messages.error(request, 'Vui lòng nhập nội dung đánh giá.')
            return redirect('project_detail', project_id=project.id)

        with transaction.atomic():
            # Save feedback
            fb = Feedback.objects.create(
                project=project,
                mentor=request.user,
                content=content,
                rating=rating,
                status=review_result_status
            )

            # Apply project status workflow via apply_project_review
            if project.status == ProjectStatus.REVIEW:
                if review_result_status == ReviewStatus.APPROVED:
                    apply_project_review(project, ProjectStatus.COMPLETED, request.user, content=content, rating=rating)
                elif review_result_status == ReviewStatus.NEED_REVISION:
                    apply_project_review(project, ProjectStatus.IN_PROGRESS, request.user, content=content, rating=rating)
            else:
                # If not in REVIEW state, feedback is saved as PENDING comment without altering project status
                fb.status = ReviewStatus.PENDING
                fb.save()

            # A5: Send notification only to ACCEPTED members via notify()
            accepted_members = project.memberships.filter(status=MemberStatus.ACCEPTED).select_related('user')
            for mem in accepted_members:
                if mem.user != request.user:
                    notify(
                        recipient=mem.user,
                        sender=request.user,
                        title=f'Mentor nhận xét đồ án [{project.code}]',
                        message=f'{request.user.display_name} đã đánh giá: "{content[:80]}..."',
                        link=f'/projects/{project.id}/',
                        notification_type=NotificationType.MENTOR_FEEDBACK,
                        project=project,
                        dedupe_key=f"feedback:{fb.id}:{mem.user.id}"
                    )

            log_action(
                user=request.user,
                action=ActionType.SUBMIT_REVIEW,
                entity_type='Feedback',
                entity_id=fb.id,
                description=f'Mentor gửi nhận xét cho đồ án {project.name} [{review_result_status}] ({rating} sao)',
                project=project,
                request=request
            )
    finally:
        cache.delete(lock_key)

    messages.success(request, 'Đã gửi đánh giá Review đồ án thành công!')
    return redirect('project_detail', project_id=project.id)

@login_required
@require_POST
def feedback_ack_view(request, feedback_id):
    feedback = get_object_or_404(Feedback, id=feedback_id)
    if not can(request.user, 'review.ack', feedback.project):
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền xác nhận phản hồi này.'}, status=403)

    feedback.acknowledged_at = timezone.now()
    feedback.acknowledged_by = request.user
    feedback.save()

    log_action(
        user=request.user,
        action=ActionType.UPDATE_TASK,
        entity_type='Feedback',
        entity_id=feedback.id,
        description=f'Xác nhận đã xử lý phản hồi của Mentor cho đồ án {feedback.project.code}',
        project=feedback.project,
        request=request
    )

    return JsonResponse({'status': 'success', 'message': 'Đã xác nhận xử lý phản hồi từ Mentor.'})
