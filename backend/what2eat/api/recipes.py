from uuid import UUID
from fastapi import APIRouter, Query, Request
from what2eat.errors import AppError

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
