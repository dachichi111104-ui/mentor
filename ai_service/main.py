import os
import hmac
from fastapi import FastAPI, HTTPException, Header, Depends, status
from pydantic import BaseModel
from typing import Optional

# Import pure Python engine
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai_assistant.engine.service import run_task

app = FastAPI(
    title="ProjectHub AI Microservice",
    description="Microservice phụ trợ phục vụ tính năng AI cho ProjectHub AI",
    version="2.0.0"
)

AI_SERVICE_TOKEN = os.getenv("AI_SERVICE_TOKEN", "secret-token")

def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Thiếu Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Định dạng Token không hợp lệ. Sử dụng 'Bearer <token>'")
    token = parts[1]
    if not hmac.compare_digest(token, AI_SERVICE_TOKEN):
        raise HTTPException(status_code=403, detail="Xác thực Service Token thất bại")
    return token

class AITaskRequest(BaseModel):
    facts: dict
    user_message: Optional[str] = ""

@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "ProjectHub AI Microservice"}

@app.post("/v1/breakdown", dependencies=[Depends(verify_token)])
def breakdown_endpoint(req: AITaskRequest):
    return run_task("breakdown", req.facts)

@app.post("/v1/risks", dependencies=[Depends(verify_token)])
def risks_endpoint(req: AITaskRequest):
    return run_task("risks", req.facts)

@app.post("/v1/weekly", dependencies=[Depends(verify_token)])
def weekly_endpoint(req: AITaskRequest):
    return run_task("weekly", req.facts)

@app.post("/v1/questions", dependencies=[Depends(verify_token)])
def questions_endpoint(req: AITaskRequest):
    return run_task("questions", req.facts)

@app.post("/v1/chat", dependencies=[Depends(verify_token)])
def chat_endpoint(req: AITaskRequest):
    return run_task("chat", req.facts, user_message=req.user_message)
