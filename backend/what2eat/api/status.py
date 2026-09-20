from fastapi import APIRouter, Request

router = APIRouter(prefix='/api')


@router.get('/status')
async def status(request: Request):
    settings = request.app.state.settings
    return {
        'app_name': '吃神马', 'slug': 'what2eat', 'missing': settings.missing(),
        'capabilities': {
            'database': {'ready': request.app.state.pool is not None},
            'llm': {'configured': bool(settings.llm_api_key), 'model': settings.llm_model},
            'embedding': {'configured': bool(settings.embedding_api_key and settings.embedding_base_url),
                          'region_confirmed': settings.embedding_region_confirmed},
            'vector': {'ready': getattr(request.app.state, 'index', None) is not None},
        },
    }
