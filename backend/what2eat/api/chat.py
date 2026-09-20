from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from what2eat.agent.events import encode_sse
from what2eat.config import DEMO_USER
from what2eat.errors import AppError

router = APIRouter(prefix='/api/chat', tags=['chat'])


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    session_id: UUID
    request_id: UUID
    message: str = Field(min_length=1, max_length=4000)


@router.post('')
async def chat(body: ChatRequest, request: Request):
    runner = getattr(request.app.state, 'agent_runner', None)
    if runner is None:
        raise AppError('agent_unavailable', 'Agent 尚未就绪，请检查数据库和模型配置。', 503)

    async def stream():
        async for event in runner.run(DEMO_USER, body.session_id, body.request_id, body.message):
            yield encode_sse(event)

    return StreamingResponse(stream(), media_type='text/event-stream', headers={
        'Cache-Control': 'no-cache, no-transform', 'X-Accel-Buffering': 'no',
    })
