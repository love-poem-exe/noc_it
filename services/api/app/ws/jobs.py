from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from celery.result import AsyncResult
import asyncio

from app.tasks.celery_app import celery_app

router = APIRouter()


@router.websocket("/ws/jobs/{job_id}")
async def job_ws(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    try:
        while True:
            result = AsyncResult(job_id, app=celery_app)
            payload = result.result if result.ready() else None
            await websocket.send_json({
                "type": "job.status",
                "payload": {
                    "jobId": job_id,
                    "state": result.state,
                    "ready": result.ready(),
                    "result": payload,
                },
            })
            if result.ready():
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
