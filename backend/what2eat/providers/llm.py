import httpx
from langchain_openai import ChatOpenAI

from what2eat.config import Settings
from what2eat.errors import AppError


def create_llm(settings: Settings) -> ChatOpenAI:
    if not settings.llm_api_key:
        raise AppError('llm_not_configured', '请先在本机 .env 配置大模型 API Key。', 503)
    return ChatOpenAI(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        extra_body={'thinking': {'type': 'disabled'}},
        use_responses_api=False,
        timeout=httpx.Timeout(settings.generation_timeout, connect=10.0),
        max_retries=0,
    )
