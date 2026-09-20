from __future__ import annotations

import math
from pathlib import Path
from uuid import UUID
from psycopg.types.json import Jsonb
from what2eat.errors import AppError
from what2eat.knowledge.loaders import load_document
from what2eat.knowledge.schemas import DocumentCreate, DocumentState


class DocumentRepository:
    def __init__(self, pool):
        self.pool = pool

    async def create(self, item: DocumentCreate) -> dict:
        async with self.pool.connection() as conn:
            row = await (await conn.execute(
                'INSERT INTO documents(id,content_hash,source_path,source_url,title,category,index_version,state,metadata) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(content_hash,index_version) '
                'DO UPDATE SET updated_at=now() RETURNING *',
                (item.id, item.content_hash, item.source_path, item.source_url, item.title,
                 item.category, item.index_version, DocumentState.pending.value, Jsonb(item.metadata)),
            )).fetchone()
        return row

    async def get(self, document_id: UUID) -> dict:
        async with self.pool.connection() as conn:
            row = await (await conn.execute('SELECT * FROM documents WHERE id=%s', (document_id,))).fetchone()
        if row is None:
            raise AppError('document_not_found', '文档不存在。', 404)
        return row

    async def list(self, limit: int = 100) -> list[dict]:
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                'SELECT * FROM documents ORDER BY created_at DESC,id DESC LIMIT %s',
                (min(max(limit, 1), 200),),
            )).fetchall()

    async def page(self, page: int = 1, page_size: int = 12) -> dict:
        page = max(1, page)
        page_size = max(1, min(page_size, 50))
        async with self.pool.connection() as conn:
            total = (await (await conn.execute('SELECT COUNT(*) AS total FROM documents')).fetchone())['total']
            items = await (await conn.execute(
                'SELECT * FROM documents ORDER BY created_at DESC,id DESC LIMIT %s OFFSET %s',
                (page_size, (page - 1) * page_size),
            )).fetchall()
        return {'items': items, 'page': page, 'page_size': page_size, 'total': total,
                'total_pages': math.ceil(total / page_size) if total else 0}

    async def content(self, document_id: UUID) -> dict:
        record = await self.get(document_id)
        path = Path(record['source_path'])
        if not path.is_file():
            raise AppError('document_source_missing', '文档原文文件不存在。', 404)
        loaded = load_document(path, document_id)
        return {
            'id': record['id'],
            'title': record['title'],
            'format': path.suffix.lower().lstrip('.'),
            'content': '\n\n'.join(item.page_content for item in loaded),
            'source_url': record['source_url'],
        }

    async def ready_ids(self, ids: list[UUID | str]) -> set[UUID]:
        if not ids:
            return set()
        normalized = [UUID(str(value)) for value in ids]
        async with self.pool.connection() as conn:
            rows = await (await conn.execute(
                "SELECT id FROM documents WHERE id=ANY(%s) AND state='ready'", (normalized,),
            )).fetchall()
        return {row['id'] for row in rows}

    async def set_state(self, document_id: UUID, state: str, error: str | None = None) -> None:
        state = DocumentState(state).value
        async with self.pool.connection() as conn:
            result = await conn.execute(
                'UPDATE documents SET state=%s,error=%s,updated_at=now() WHERE id=%s',
                (state, error, document_id),
            )
        if result.rowcount != 1:
            raise AppError('document_not_found', '文档不存在。', 404)

    async def delete_metadata(self, document_id: UUID) -> None:
        async with self.pool.connection() as conn:
            await conn.execute('DELETE FROM documents WHERE id=%s', (document_id,))

    async def by_state(self, state: str) -> list[dict]:
        state = DocumentState(state).value
        async with self.pool.connection() as conn:
            return await (await conn.execute(
                'SELECT * FROM documents WHERE state=%s ORDER BY created_at,id', (state,),
            )).fetchall()
