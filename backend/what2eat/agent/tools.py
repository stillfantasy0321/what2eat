import json
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, Field

from what2eat.recipes.shopping import build_shopping_list as compile_shopping_list
from what2eat.recipes.schemas import PlanRequest


@dataclass
class ToolState:
    read_recipe_ids: set[UUID] = field(default_factory=set)
    sources: list[dict] = field(default_factory=list)


_TOOL_STATE: ContextVar[ToolState | None] = ContextVar('what2eat_tool_state', default=None)


def set_tool_state() -> Token:
    return _TOOL_STATE.set(ToolState())


def reset_tool_state(token: Token) -> None:
    _TOOL_STATE.reset(token)


def current_tool_state() -> ToolState:
    state = _TOOL_STATE.get()
    if state is None:
        raise RuntimeError('tool state is only available while an agent run is active')
    return state


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, separators=(',', ':'))


def _recipe_compact(recipe) -> dict:
    return {'id': str(recipe.id), 'title': recipe.title, 'category': recipe.category}


def _grouped_recipes(items) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for recipe in items:
        groups.setdefault(recipe.category, []).append(_recipe_compact(recipe))
    return [{'category': category, 'recipes': groups[category]}
            for category in sorted(groups)]


def _recipe_summary(recipe) -> dict:
    return {'id': str(recipe.id), 'title': recipe.title, 'category': recipe.category,
            'ingredients': [item.model_dump(mode='json') for item in recipe.ingredients],
            'source_url': recipe.source_url, 'ingredient_status': recipe.ingredient_status}


def _record_source(source: dict) -> None:
    state = current_tool_state()
    key = (source.get('document_id'), source.get('chunk_id'), source.get('recipe_id'))
    if not any((item.get('document_id'), item.get('chunk_id'), item.get('recipe_id')) == key
               for item in state.sources):
        state.sources.append(source)


class ListArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    limit: int = Field(default=20, ge=1, le=50)
    cursor: str | None = None


class CategoryArgs(ListArgs):
    category: str = Field(min_length=1, max_length=50)


class PlanArgs(PlanRequest):
    pass


class SearchArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(min_length=1, max_length=300)
    limit: int = Field(default=5, ge=1, le=10)


class RecipeArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    recipe_id: UUID


class ShoppingArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    recipe_ids: list[UUID] = Field(min_length=1, max_length=21)
    diners: int = Field(ge=1, le=12)
    pantry: list[str] = Field(default_factory=list, max_length=100)


def create_tools(catalog, planner, retriever) -> list[StructuredTool]:
    async def get_all_recipes(limit: int = 20, cursor: str | None = None) -> str:
        recipes = await catalog.all()
        return _json({'groups': _grouped_recipes(recipes), 'total': len(recipes)})

    async def get_recipes_by_category(category: str, limit: int = 20,
                                      cursor: str | None = None) -> str:
        page = await catalog.list(category, cursor, limit)
        return _json({'items': [_recipe_summary(item) for item in page['items']],
                      'next_cursor': page['next_cursor']})

    async def what_to_eat(**kwargs) -> str:
        return _json(await planner.today(PlanRequest.model_validate(kwargs)))

    async def recommend_meals(**kwargs) -> str:
        return _json(await planner.weekly(PlanRequest.model_validate(kwargs)))

    async def search_recipes(query: str, limit: int = 5) -> str:
        if retriever is None:
            return _json({'error': {'code': 'retriever_unavailable', 'message': '知识库检索尚未配置。'}})
        documents = await retriever.search(query, limit)
        items = []
        for document in documents:
            metadata = document.metadata
            source = {key: str(metadata[key]) for key in
                      ('document_id', 'chunk_id', 'title', 'category', 'source_url', 'content_hash', 'index_version')
                      if metadata.get(key) is not None}
            source['content'] = document.page_content[:1800]
            _record_source(source)
            items.append({**source, 'content': document.page_content[:1800]})
        return _json({'items': items})

    async def get_recipe(recipe_id: UUID) -> str:
        recipe = await catalog.get(recipe_id)
        state = current_tool_state()
        state.read_recipe_ids.add(recipe.id)
        _record_source({'recipe_id': str(recipe.id), 'document_id': str(recipe.id), 'title': recipe.title,
                        'content': recipe.raw_text[:12000],
                        'source_url': recipe.source_url, 'content_hash': recipe.content_hash})
        return _json(recipe.model_dump(mode='json'))

    async def shopping(recipe_ids: list[UUID], diners: int, pantry: list[str]) -> str:
        state = current_tool_state()
        unread = [str(recipe_id) for recipe_id in recipe_ids if recipe_id not in state.read_recipe_ids]
        if unread:
            return _json({'error': {'code': 'recipe_not_read',
                                    'message': '请先调用 get_recipe 读取每道菜谱。',
                                    'recipe_ids': unread}})
        recipes = [await catalog.get(recipe_id) for recipe_id in recipe_ids]
        return _json({'items': compile_shopping_list(recipes, diners, pantry)})

    definitions = [
        ('get_all_recipes', '按分类返回全部菜谱名称目录，用于只列菜名的总览。', get_all_recipes, ListArgs),
        ('get_recipes_by_category', '按分类分页查询菜谱。', get_recipes_by_category, CategoryArgs),
        ('what_to_eat', '根据人数、忌口和现有食材推荐今日菜品。', what_to_eat, PlanArgs),
        ('recommend_meals', '根据约束生成最多七天、最多二十一餐的膳食计划。', recommend_meals, PlanArgs),
        ('search_recipes', '在可信菜谱知识库中混合检索原文证据。', search_recipes, SearchArgs),
        ('get_recipe', '按菜谱 ID 读取完整食材、步骤和来源。', get_recipe, RecipeArgs),
        ('build_shopping_list', '为本轮已读取的菜谱生成购物清单。', shopping, ShoppingArgs),
    ]
    return [StructuredTool.from_function(name=name, description=description,
                                         coroutine=coroutine, args_schema=schema)
            for name, description, coroutine, schema in definitions]
