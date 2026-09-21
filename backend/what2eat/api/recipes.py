from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Query, Request
from what2eat.errors import AppError
from what2eat.knowledge.indexing import IndexingService

router = APIRouter(prefix='/api', tags=['recipes'])


def _catalog(request: Request):
    catalog = getattr(request.app.state, 'catalog', None)
    if catalog is None:
        raise AppError('database_unavailable', '菜谱目录尚未就绪。', 503)
    return catalog


@router.get('/recipes')
async def recipes(request: Request, category: str | None = None,
                  page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=50)):
    return await _catalog(request).page(category, page, page_size)


@router.get('/recipes/categories')
async def categories(request: Request):
    return {'items': await _catalog(request).categories()}


@router.get('/recipes/{recipe_id}')
async def recipe(recipe_id: UUID, request: Request):
    return await _catalog(request).get(recipe_id)


@router.delete('/recipes/{recipe_id}', status_code=202)
async def delete_recipe(recipe_id: UUID, request: Request, background: BackgroundTasks):
    catalog = _catalog(request)
    record = await catalog.documents.get(recipe_id)
    if record['state'] != 'ready':
        raise AppError('recipe_not_ready', '菜谱尚未完成索引，暂时无法删除。', 409)
    index = getattr(request.app.state, 'index', None)
    if index is None:
        raise AppError('vector_unavailable', '百炼 Embedding 或 Milvus 尚未就绪。', 503)
    await catalog.documents.set_state(recipe_id, 'deleting')
    service = IndexingService(catalog.documents, index, getattr(request.app.state, 'retriever', None))
    background.add_task(service.delete, recipe_id)
    return {'queued': True, 'recipe_id': recipe_id}
