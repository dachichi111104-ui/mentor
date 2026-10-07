import logging
try:
    from celery import shared_task
except ImportError:
    def shared_task(func=None, **kwargs):
        if func is None:
            return lambda f: f
        return func
from django.utils import timezone
from django.db import transaction
from projects.models import Project, ProjectStatus
from milestones.models import Milestone, MilestoneStatus
from ai_assistant.models import WeeklySummary, AIRequest
from ai_assistant.engine.service import run_task
from notifications.services import notify
from notifications.models import NotificationType

logger = logging.getLogger(__name__)

@shared_task
def generate_weekly_summaries_task():
    """
    Celery task to compile weekly progress summaries for active projects (IN_PROGRESS, REVIEW).
    Idempotent per (project, iso_year, iso_week).
    """
    now = timezone.now()
    iso_year, iso_week, _ = now.isocalendar()
    active_projects = Project.objects.filter(status__in=[ProjectStatus.IN_PROGRESS, ProjectStatus.REVIEW])

    processed_count = 0
    for project in active_projects:
        try:
            if WeeklySummary.objects.filter(project=project, year=iso_year, week_number=iso_week).exists():
                continue

            # Run AI task to generate summary
            result = run_task('weekly-summary', project=project)
            summary_text = result.get('data', {}).get('summary_text', '')

            if not summary_text:
                summary_text = (
                    f"Tóm tắt tiến độ Tuần {iso_week}/{iso_year} - Đồ án [{project.code}]:\n"
                    f"- Tiến độ chung: {project.progress}%\n"
                    f"- Tổng số công việc: {project.tasks.count()}\n"
                    f"- Công việc hoàn thành: {project.tasks.filter(status='DONE').count()}"
                )

            with transaction.atomic():
                ws = WeeklySummary.objects.create(
                    project=project,
                    week_number=iso_week,
                    year=iso_year,
                    summary_text=summary_text
                )
                processed_count += 1

                # Notify Leader & Mentor
                recipients = set()
                if project.created_by:
                    recipients.add(project.created_by)
                if project.mentor and project.mentor_status == 'ACCEPTED':
                    recipients.add(project.mentor)

                for r in recipients:
                    notify(
                        recipient=r,
                        title=f"Báo cáo tóm tắt tuần {iso_week}/{iso_year} [{project.code}]",
                        message=f"Hệ thống đã tự động tạo báo cáo tóm tắt tiến độ tuần {iso_week} cho đồ án {project.name}.",
                        link=f"/ai/assistant/?project_id={project.id}",
                        notification_type=NotificationType.WEEKLY_SUMMARY,
                        project=project,
                        dedupe_key=f"weekly_summary:{project.id}:{iso_year}:{iso_week}:{r.id}"
                    )
        except Exception as exc:
            logger.error(f"Error generating weekly summary for project {project.code}: {exc}")

    return f"Weekly summaries generated for {processed_count} projects."

@shared_task
def daily_risk_scan_task():
    """
    Daily scan task for risks and overdue items across all active projects.
    Sets overdue milestones to OVERDUE status and sends notifications for CRITICAL risks.
    """
    today = timezone.localdate()
    # Check overdue milestones
    overdue_milestones = Milestone.objects.filter(due_date__lt=today).exclude(status=MilestoneStatus.COMPLETED)
    for m in overdue_milestones:
        m.status = MilestoneStatus.OVERDUE
        m.save()

    active_projects = Project.objects.filter(status__in=[ProjectStatus.IN_PROGRESS, ProjectStatus.REVIEW])
    risk_count = 0

    for project in active_projects:
        try:
            res = run_task('risk-detection', project=project)
            risks = res.get('data', {}).get('risks', [])
            for r in risks:
                severity = r.get('severity', 'LOW')
                if severity == 'CRITICAL':
                    risk_id = r.get('rule_id', 'R0')
                    recipients = set()
                    if project.created_by:
                        recipients.add(project.created_by)
                    if project.mentor and project.mentor_status == 'ACCEPTED':
                        recipients.add(project.mentor)

                    for rec in recipients:
                        notify(
                            recipient=rec,
                            title=f"⚠️ Cảnh báo Rủi ro Rất cao [{project.code}]",
                            message=f"{r.get('title', 'Phát hiện rủi ro nghiêm trọng')}: {r.get('description', '')}",
                            link=f"/ai/assistant/?project_id={project.id}",
                            notification_type=NotificationType.TASK_OVERDUE,
                            project=project,
                            dedupe_key=f"risk_scan:{project.id}:{risk_id}:{today}:{rec.id}"
                        )
                    risk_count += 1
        except Exception as exc:
            logger.error(f"Error scanning risks for project {project.code}: {exc}")

    return f"Daily risk scan complete. Processed {active_projects.count()} projects, flagged {risk_count} critical risks."
