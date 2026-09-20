from langchain_openai import OpenAIEmbeddings
from what2eat.config import Settings
from what2eat.errors import AppError


def create_embeddings(settings: Settings) -> OpenAIEmbeddings:
    if not settings.embedding_api_key or not settings.embedding_base_url:
        raise AppError('embedding_not_configured', '请先配置百炼 Embedding API Key 和地域端点。', 503)
    if not settings.embedding_region_confirmed:
        raise AppError('embedding_region_unconfirmed', '请先确认百炼 Key 所属地域。', 503)
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        api_key=settings.embedding_api_key.get_secret_value(),
        base_url=settings.embedding_base_url,
        chunk_size=10,
        check_embedding_ctx_length=False,
        max_retries=2,
        timeout=30,
    )
