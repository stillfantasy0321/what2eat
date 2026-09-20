import hashlib
from uuid import UUID, uuid4
from langchain_core.messages import (
    AIMessage, BaseMessage, HumanMessage, message_to_dict, messages_from_dict,
)
from psycopg.types.json import Jsonb
from what2eat.errors import AppError


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _display(row: dict) -> dict:
    data = row['message'].get('data', {})
    return {
        'id': row['id'], 'seq': row['seq'], 'role': row['role'],
        'content': data.get('content', ''), 'message': row['message'],
        'sources': row['sources'], 'status': row['status'],
        'created_at': row['created_at'], 'updated_at': row['updated_at'],
    }


class ConversationRepository:
    def __init__(self, pool):
        self.pool = pool

    async def create_session(self, user_id: UUID, title: str) -> dict:
        title = title.strip()
        if not title or len(title) > 80:
            raise AppError('invalid_title', '会话标题须为1—80个字符。', 422)
        session_id = uuid4()
        async with self.pool.connection() as conn:
            row = await (await conn.execute(
                'INSERT INTO sessions(id,user_id,title) VALUES (%s,%s,%s) RETURNING *',
                (session_id, user_id, title),
            )).fetchone()
        return row

    async def begin_run(self, user_id: UUID, session_id: UUID, request_id: UUID, text: str) -> dict:
        text = text.strip()
        if not text:
            raise AppError('empty_message', '消息不能为空。', 422)
        input_hash = _hash(text)
        async with self.pool.connection() as conn, conn.transaction():
            session = await (await conn.execute(
                'SELECT * FROM sessions WHERE id=%s AND user_id=%s FOR UPDATE',
                (session_id, user_id),
            )).fetchone()
            if session is None:
                raise AppError('session_not_found', '会话不存在。', 404)
            existing = await (await conn.execute(
                'SELECT * FROM chat_runs WHERE request_id=%s', (request_id,),
            )).fetchone()
            if existing:
                if existing['session_id'] != session_id or existing['input_hash'] != input_hash:
                    raise AppError('idempotency_conflict', 'request_id 已用于另一条消息。', 409)
                return {'request_id': request_id, 'message_id': existing['assistant_message_id'],
                        'status': existing['status'], 'replayed': True}
            running = await (await conn.execute(
                "SELECT request_id FROM chat_runs WHERE session_id=%s AND status='running'", (session_id,),
            )).fetchone()
            if running:
                raise AppError('chat_in_progress', '该会话正在生成回答。', 409)
            user_message_id, assistant_message_id = uuid4(), uuid4()
            first_seq = session['next_seq']
            await conn.execute('UPDATE sessions SET next_seq=next_seq+2,updated_at=now() WHERE id=%s', (session_id,))
            await conn.execute(
                'INSERT INTO messages(id,session_id,request_id,seq,role,message,status) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                (user_message_id, session_id, request_id, first_seq, 'user',
                 Jsonb(message_to_dict(HumanMessage(content=text))), 'complete'),
            )
            await conn.execute(
                'INSERT INTO messages(id,session_id,request_id,seq,role,message,status) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                (assistant_message_id, session_id, request_id, first_seq + 1, 'assistant',
                 Jsonb(message_to_dict(AIMessage(content=''))), 'streaming'),
            )
            await conn.execute(
                'INSERT INTO chat_runs(request_id,session_id,assistant_message_id,input_hash,status) VALUES (%s,%s,%s,%s,%s)',
                (request_id, session_id, assistant_message_id, input_hash, 'running'),
            )
        return {'request_id': request_id, 'message_id': assistant_message_id,
                'status': 'running', 'replayed': False}

    async def save_draft(self, request_id: UUID, text: str) -> None:
        async with self.pool.connection() as conn:
            result = await conn.execute(
                "UPDATE messages m SET message=%s,status='streaming',updated_at=now() "
                'FROM chat_runs r WHERE r.request_id=%s AND m.id=r.assistant_message_id',
                (Jsonb(message_to_dict(AIMessage(content=text))), request_id),
            )
            if result.rowcount != 1:
                raise AppError('chat_run_not_found', '回答请求不存在。', 404)

    async def run_result(self, request_id: UUID) -> dict:
        async with self.pool.connection() as conn:
            row = await (await conn.execute(
                'SELECT r.status,r.assistant_message_id,m.message,m.sources '
                'FROM chat_runs r JOIN messages m ON m.id=r.assistant_message_id '
                'WHERE r.request_id=%s', (request_id,),
            )).fetchone()
        if row is None:
            raise AppError('chat_run_not_found', '回答请求不存在。', 404)
        return {'status': row['status'], 'message_id': row['assistant_message_id'],
                'text': row['message'].get('data', {}).get('content', ''),
                'sources': row['sources']}

    async def context_turns(self, user_id: UUID, session_id: UUID,
                            request_id: UUID) -> list[list[BaseMessage]]:
        async with self.pool.connection() as conn:
            owned = await (await conn.execute(
                'SELECT id FROM sessions WHERE id=%s AND user_id=%s', (session_id, user_id),
            )).fetchone()
            if owned is None:
                raise AppError('session_not_found', '会话不存在。', 404)
            rows = await (await conn.execute(
                'SELECT request_id,seq,role,message,visible FROM messages '
                'WHERE session_id=%s AND request_id<>%s ORDER BY seq',
                (session_id, request_id),
            )).fetchall()
        grouped: dict[UUID, list[dict]] = {}
        for row in rows:
            grouped.setdefault(row['request_id'], []).append(row)
        turns = []
        for group in grouped.values():
            ordered = ([row for row in group if row['visible'] and row['role'] == 'user']
                       + [row for row in group if not row['visible']]
                       + [row for row in group if row['visible'] and row['role'] == 'assistant'])
            turns.append(messages_from_dict([row['message'] for row in ordered]))
        return turns

    async def finish_run(self, request_id: UUID, text: str, sources: list[dict], status: str) -> None:
        if status not in {'complete', 'failed', 'cancelled', 'interrupted'}:
            raise ValueError(f'invalid final status: {status}')
        async with self.pool.connection() as conn, conn.transaction():
            run = await (await conn.execute(
                'SELECT * FROM chat_runs WHERE request_id=%s FOR UPDATE', (request_id,),
            )).fetchone()
            if run is None:
                raise AppError('chat_run_not_found', '回答请求不存在。', 404)
            await conn.execute(
                'UPDATE messages SET message=%s,sources=%s,status=%s,updated_at=now() WHERE id=%s',
                (Jsonb(message_to_dict(AIMessage(content=text))), Jsonb(sources), status,
                 run['assistant_message_id']),
            )
            await conn.execute(
                'UPDATE chat_runs SET status=%s,updated_at=now() WHERE request_id=%s', (status, request_id),
            )
            await conn.execute('UPDATE sessions SET updated_at=now() WHERE id=%s', (run['session_id'],))

    async def append_trace(self, request_id: UUID, messages: list[BaseMessage]) -> None:
        if not messages:
            return
        async with self.pool.connection() as conn, conn.transaction():
            run = await (await conn.execute(
                'SELECT * FROM chat_runs WHERE request_id=%s', (request_id,),
            )).fetchone()
            if run is None:
                raise AppError('chat_run_not_found', '回答请求不存在。', 404)
            session = await (await conn.execute(
                'SELECT next_seq FROM sessions WHERE id=%s FOR UPDATE', (run['session_id'],),
            )).fetchone()
            await conn.execute('UPDATE sessions SET next_seq=next_seq+%s WHERE id=%s',
                               (len(messages), run['session_id']))
            for offset, message in enumerate(messages):
                role = message.type
                await conn.execute(
                    'INSERT INTO messages(id,session_id,request_id,seq,role,message,status,visible) '
                    'VALUES (%s,%s,%s,%s,%s,%s,%s,false)',
                    (uuid4(), run['session_id'], request_id, session['next_seq'] + offset, role,
                     Jsonb(message_to_dict(message)), 'complete'),
                )

    async def history(self, user_id: UUID, session_id: UUID, before_seq: int | None, limit: int) -> dict:
        limit = max(1, min(limit, 100))
        async with self.pool.connection() as conn:
            owned = await (await conn.execute(
                'SELECT id FROM sessions WHERE id=%s AND user_id=%s', (session_id, user_id),
            )).fetchone()
            if owned is None:
                raise AppError('session_not_found', '会话不存在。', 404)
            rows = await (await conn.execute(
                'SELECT * FROM messages WHERE session_id=%s AND visible=true '
                'AND (%s::bigint IS NULL OR seq < %s) ORDER BY seq DESC LIMIT %s',
                (session_id, before_seq, before_seq, limit + 1),
            )).fetchall()
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = [_display(row) for row in reversed(rows)]
        source_ids = set()
        for item in items:
            for source in item['sources']:
                try:
                    source_ids.add(UUID(str(source.get('document_id') or source.get('recipe_id'))))
                except (ValueError, TypeError):
                    pass
        if source_ids:
            from what2eat.knowledge.repository import DocumentRepository
            ready = await DocumentRepository(self.pool).ready_ids(list(source_ids))
            for item in items:
                for source in item['sources']:
                    try:
                        source['source_available'] = UUID(str(source.get('document_id') or source.get('recipe_id'))) in ready
                    except (ValueError, TypeError):
                        pass
        return {'items': items, 'next_cursor': min(row['seq'] for row in rows) if has_more else None}

    async def recover_interrupted(self) -> int:
        async with self.pool.connection() as conn, conn.transaction():
            runs = await (await conn.execute(
                "UPDATE chat_runs SET status='interrupted',error_code='process_restart',updated_at=now() "
                "WHERE status='running' RETURNING assistant_message_id",
            )).fetchall()
            if runs:
                await conn.execute(
                    "UPDATE messages SET status='interrupted',updated_at=now() WHERE id=ANY(%s)",
                    ([row['assistant_message_id'] for row in runs],),
                )
        return len(runs)

    async def list_sessions(self, user_id: UUID, limit: int = 30) -> list[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                'SELECT id,title,status,created_at,updated_at FROM sessions WHERE user_id=%s '
                'ORDER BY updated_at DESC,id DESC LIMIT %s', (user_id, min(max(limit, 1), 100)),
            )).fetchall()

    async def get_session(self, user_id: UUID, session_id: UUID) -> dict:
        async with self.pool.connection() as conn:
            row = await (await conn.execute(
                'SELECT id,title,status,created_at,updated_at FROM sessions WHERE user_id=%s AND id=%s',
                (user_id, session_id),
            )).fetchone()
        if row is None:
            raise AppError('session_not_found', '会话不存在。', 404)
        return row

    async def rename_session(self, user_id: UUID, session_id: UUID, title: str) -> dict:
        title = title.strip()
        if not title or len(title) > 80:
            raise AppError('invalid_title', '会话标题须为1—80个字符。', 422)
        async with self.pool.connection() as conn:
            row = await (await conn.execute(
                'UPDATE sessions SET title=%s,updated_at=now() WHERE user_id=%s AND id=%s RETURNING *',
                (title, user_id, session_id),
            )).fetchone()
        if row is None:
            raise AppError('session_not_found', '会话不存在。', 404)
        return row

    async def delete_session(self, user_id: UUID, session_id: UUID) -> None:
        async with self.pool.connection() as conn, conn.transaction():
            session = await (await conn.execute(
                'SELECT id FROM sessions WHERE user_id=%s AND id=%s FOR UPDATE', (user_id, session_id),
            )).fetchone()
            if session is None:
                raise AppError('session_not_found', '会话不存在。', 404)
            await conn.execute(
                "UPDATE chat_runs SET status='cancelled',updated_at=now() WHERE session_id=%s AND status='running'",
                (session_id,),
            )
            await conn.execute(
                "UPDATE messages SET status='cancelled',updated_at=now() WHERE session_id=%s AND status='streaming'",
                (session_id,),
            )
            await conn.execute('DELETE FROM sessions WHERE id=%s', (session_id,))
