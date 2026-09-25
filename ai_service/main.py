from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(
    title="ProjectHub AI Microservice",
    description="Microservice phụ trợ phục vụ tính năng AI nặng độc lập cho ProjectHub AI platform",
    version="1.0.0"
)

class ProjectInfo(BaseModel):
    name: str
    code: str
    technology: str
    category: str

class BreakdownRequest(BaseModel):
    project_name: str
    category: Optional[str] = "Web"
    technology: Optional[str] = "Python, Django"

@app.get("/")
def read_root():
    return {"status": "online", "service": "ProjectHub AI Microservice", "version": "1.0.0"}

@app.post("/api/ai/breakdown")
def ai_breakdown_endpoint(req: BreakdownRequest):
    tasks = [
        {
            "title": f"Phân tích Yêu cầu & ERD CSDL cho {req.project_name}",
            "description": f"Xây dựng đặc tả yêu cầu và sơ đồ CSDL cho thể loại {req.category}.",
            "priority": "CRITICAL",
            "labels": "SRS, ERD"
        },
        {
            "title": "Phát triển Auth & Phân quyền RBAC",
            "description": "Đăng ký, Đăng nhập và Session Security.",
            "priority": "HIGH",
            "labels": "Security, Auth"
        },
        {
            "title": f"Thiết kế Frontend UI/UX với {req.technology}",
            "description": "Giao diện responsive tương thích thiết bị di động.",
            "priority": "HIGH",
            "labels": "UI/UX, Frontend"
        },
        {
            "title": "Tích hợp Bảng công việc Kanban & Realtime Status",
            "description": "Kéo thả công việc và cập nhật trạng thái tức thì.",
            "priority": "CRITICAL",
            "labels": "Kanban, Core"
        }
    ]
    return {"status": "success", "suggested_tasks": tasks}

@app.post("/api/ai/weekly-summary")
def ai_weekly_summary_endpoint(project: ProjectInfo, done_count: int, total_count: int):
    progress = int((done_count / total_count * 100)) if total_count > 0 else 0
    return {
        "status": "success",
        "summary": f"Đồ án {project.code} ({project.name}): Đã hoàn thành {done_count}/{total_count} tasks (Tiến độ {progress}%). Đảm bảo đúng thời hạn tiến độ mốc milestone."
    }
