from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from what2eat.config import Settings
from what2eat.errors import AppError, error_handler
from what2eat.api.status import router as status_router
from what2eat.api.sessions import router as session_router
from what2eat.api.documents import router as document_router
from what2eat.api.recipes import router as recipe_router
from what2eat.api.chat import router as chat_router
from what2eat.api.diagnostics import router as diagnostics_router
from what2eat.db.pool import open_pool


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.pool = None
        app.state.index = None
        app.state.retriever = None
        app.state.catalog = None
        app.state.agent_runner = None
        app.state.index_version = f'{settings.embedding_model}-{settings.embedding_dimensions}-512-64'
        if settings.database_url:
            try:
                app.state.pool = await open_pool(settings.database_url.get_secret_value())
                async with app.state.pool.connection() as conn:
                    await conn.execute('SELECT id FROM users LIMIT 1')
            except Exception:
                if app.state.pool:
                    await app.state.pool.close()
                app.state.pool = None
        if app.state.pool:
            from what2eat.knowledge.repository import DocumentRepository
            from what2eat.recipes.catalog import RecipeCatalog
            from what2eat.conversations.repository import ConversationRepository
            app.state.catalog = RecipeCatalog(DocumentRepository(app.state.pool))
            await ConversationRepository(app.state.pool).recover_interrupted()
        if settings.embedding_api_key and settings.embedding_base_url and settings.embedding_region_confirmed:
            try:
                from what2eat.providers.embeddings import create_embeddings
                from what2eat.providers.vectors import VectorIndex
                from what2eat.knowledge.repository import DocumentRepository
                from what2eat.knowledge.retrieval import Retriever
                app.state.index = VectorIndex(settings, create_embeddings(settings))
                if app.state.pool:
                    app.state.retriever = Retriever(app.state.index, DocumentRepository(app.state.pool))
                    from what2eat.knowledge.indexing import IndexingService
                    await IndexingService(DocumentRepository(app.state.pool), app.state.index,
                                          app.state.retriever).recover()
            except Exception:
                app.state.index = None
        if app.state.pool and app.state.catalog and settings.llm_api_key:
            from what2eat.agent.runner import AgentRunner
            from what2eat.agent.tools import create_tools
            from what2eat.conversations.repository import ConversationRepository
            from what2eat.db.preferences import PreferenceRepository
            from what2eat.providers.llm import create_llm
            from what2eat.recipes.planning import Planner
            planner = Planner(app.state.catalog, app.state.retriever)
            tools = create_tools(app.state.catalog, planner, app.state.retriever)
            app.state.agent_runner = AgentRunner(
                ConversationRepository(app.state.pool), create_llm(settings), tools,
                preferences=PreferenceRepository(app.state.pool),
                context_budget=settings.context_budget, timeout=settings.generation_timeout,
            )
        try:
            yield
        finally:
            if app.state.pool:
                await app.state.pool.close()
            if app.state.index:
                await app.state.index.close()

    app = FastAPI(title='吃神马 · what2eat', lifespan=lifespan)
    app.add_exception_handler(AppError, error_handler)
    app.include_router(status_router)
    app.include_router(session_router)
    app.include_router(document_router)
    app.include_router(recipe_router)
    app.include_router(chat_router)
    app.include_router(diagnostics_router)
    frontend_dist = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
    if frontend_dist.exists():
        assets = frontend_dist / 'assets'
        if assets.exists():
            app.mount('/assets', StaticFiles(directory=assets), name='frontend-assets')
        @app.get('/{spa_path:path}', include_in_schema=False)
        async def spa_fallback(spa_path: str):
            if spa_path == 'api' or spa_path.startswith('api/'):
                return JSONResponse(status_code=404, content={'error': {
                    'code': 'not_found', 'message': 'API 路由不存在。',
                }})
            return FileResponse(frontend_dist / 'index.html')
    return app


app = create_app()
