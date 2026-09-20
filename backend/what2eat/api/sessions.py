from uuid import UUID
from fastapi import APIRouter, Depends, Query
from what2eat.config import DEMO_USER
from what2eat.conversations.repository import ConversationRepository
from what2eat.conversations.schemas import SessionCreate, SessionPatch
from what2eat.errors import require_database

router = APIRouter(prefix='/api/sessions', tags=['sessions'])


@router.get('')
async def list_sessions(limit: int = Query(30, ge=1, le=100), pool=Depends(require_database)):
    items = await ConversationRepository(pool).list_sessions(DEMO_USER, limit)
    return {'items': items, 'next_cursor': None}


@router.post('', status_code=201)
async def create_session(body: SessionCreate, pool=Depends(require_database)):
    return await ConversationRepository(pool).create_session(DEMO_USER, body.title)


@router.get('/{session_id}')
async def get_session(session_id: UUID, pool=Depends(require_database)):
    return await ConversationRepository(pool).get_session(DEMO_USER, session_id)


@router.get('/{session_id}/messages')
async def messages(session_id: UUID, before_seq: int | None = None,
                   limit: int = Query(50, ge=1, le=100), pool=Depends(require_database)):
    return await ConversationRepository(pool).history(DEMO_USER, session_id, before_seq, limit)


@router.patch('/{session_id}')
async def rename_session(session_id: UUID, body: SessionPatch, pool=Depends(require_database)):
    return await ConversationRepository(pool).rename_session(DEMO_USER, session_id, body.title)


@router.delete('/{session_id}', status_code=204)
async def delete_session(session_id: UUID, pool=Depends(require_database)):
    await ConversationRepository(pool).delete_session(DEMO_USER, session_id)