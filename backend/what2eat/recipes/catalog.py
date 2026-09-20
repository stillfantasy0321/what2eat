import base64
import json
import math
from pathlib import Path
from uuid import UUID
from langchain_core.documents import Document
from what2eat.errors import AppError
from what2eat.recipes.parser import parse_recipe
from what2eat.knowledge.loaders import load_document


def _encode_cursor(title: str, recipe_id: UUID) -> str:
    payload = json.dumps([title, str(recipe_id)], ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip('=')


def _decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        padded = cursor + '=' * (-len(cursor) % 4)
        title, recipe_id = json.loads(base64.urlsafe_b64decode(padded).decode())
        UUID(recipe_id)
        return title, recipe_id
    except Exception as exc:
        raise AppError('invalid_cursor', '分页游标无效。', 422) from exc


class RecipeCatalog:
    def __init__(self, documents):
        self.documents = documents

    @staticmethod
    def _parse_record(record: dict):
        path = Path(record['source_path'])
        if not path.exists():
            raise AppError('recipe_source_missing', '菜谱原文文件缺失。', 409)
        loaded = load_document(path, record['id'])
        document = Document(page_content='\n\n'.join(item.page_content for item in loaded), metadata={
            'document_id': str(record['id']), 'title': record['title'],
            'category': record['category'], 'source_url': record['source_url'],
            'content_hash': record['content_hash'],
        })
        return parse_recipe(document)

    async def all(self):
        rows = await self.documents.by_state('ready')
        recipes = [self._parse_record(row) for row in rows]
        return sorted(recipes, key=lambda item: (item.title, str(item.id)))

    async def get(self, recipe_id: UUID):
        record = await self.documents.get(recipe_id)
        if record['state'] != 'ready':
            raise AppError('recipe_not_ready', '菜谱尚未完成索引。', 409)
        return self._parse_record(record)

    async def categories(self) -> list[str]:
        return sorted({recipe.category for recipe in await self.all()})

    async def list(self, category: str | None, cursor: str | None, limit: int = 20) -> dict:
        limit = max(1, min(limit, 50))
        recipes = await self.all()
        categories = sorted({recipe.category for recipe in recipes})
        if category and category not in categories:
            raise AppError('unknown_category', f'分类不存在，可选：{"、".join(categories)}', 422)
        if category:
            recipes = [recipe for recipe in recipes if recipe.category == category]
        if cursor:
            key = _decode_cursor(cursor)
            recipes = [recipe for recipe in recipes if (recipe.title, str(recipe.id)) > key]
        page = recipes[:limit]
        next_cursor = _encode_cursor(page[-1].title, page[-1].id) if len(recipes) > limit else None
        return {'items': page, 'next_cursor': next_cursor}

    async def page(self, category: str | None, page: int = 1, page_size: int = 12) -> dict:
        page = max(1, page)
        page_size = max(1, min(page_size, 50))
        recipes = await self.all()
        categories = sorted({recipe.category for recipe in recipes})
        if category and category not in categories:
            raise AppError('unknown_category', f'分类不存在，可选：{"、".join(categories)}', 422)
        if category:
            recipes = [recipe for recipe in recipes if recipe.category == category]
        total = len(recipes)
        start = (page - 1) * page_size
        return {
            'items': recipes[start:start + page_size],
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': math.ceil(total / page_size) if total else 0,
        }
