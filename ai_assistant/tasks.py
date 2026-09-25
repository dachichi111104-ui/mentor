from celery import shared_task
from django.utils import timezone
from projects.models import Project
from ai_assistant.models import WeeklySummary
from ai_assistant.views import call_llm_api

@shared_task
def generate_weekly_summaries_task():
    """
    Celery Beat task to compile weekly progress summaries for active projects
    and store them into WeeklySummary models.
    """
    now = timezone.now()
    year, week_num, _ = now.isocalendar()
    active_projects = Project.objects.exclude(status='COMPLETED').exclude(status='ARCHIVED')

    processed_count = 0
    for project in active_projects:
        # Avoid duplicate generation for the same week
        if WeeklySummary.objects.filter(project=project, week_number=week_num, year=year).exists():
            continue

        done_tasks = project.tasks.filter(status='DONE')
        in_progress = project.tasks.filter(status='IN_PROGRESS')
        overdue_count = sum(1 for t in project.tasks.all() if t.is_overdue)

        prompt = (
            f"Tổng hợp báo cáo tuần {week_num}/{year} cho đồ án [{project.code}] '{project.name}'. "
            f"Thống kê: {done_tasks.count()} tasks hoàn thành, {in_progress.count()} đang làm, {overdue_count} quá hạn. "
            f"Viết bản tóm tắt tiến độ 4-5 dòng súc tích phục vụ mentor."
        )

        llm_res = call_llm_api(prompt)
        if not llm_res:
            llm_res = (
                f"Tóm tắt tiến độ Tuần {week_num}/{year} - Đồ án [{project.code}]:\n"
                f"- Số công việc đã hoàn tất: {done_tasks.count()} tasks.\n"
                f"- Số công việc đang triển khai: {in_progress.count()} tasks.\n"
                f"- Số công việc bị trễ hạn: {overdue_count} tasks.\n"
                f"- Đánh giá chung: Đồ án đang chạy đúng tiến độ cần đẩy nhanh nghiệm thu milestone."
            )

        WeeklySummary.objects.create(
            project=project,
            week_number=week_num,
            year=year,
            summary_text=llm_res
        )
        processed_count += 1

    return f"Weekly summaries generated for {processed_count} projects."
