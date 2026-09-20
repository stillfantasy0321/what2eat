from pathlib import Path
from uuid import UUID
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
DEMO_USER = UUID('00000000-0000-0000-0000-000000000001')


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore', env_ignore_empty=True)
    database_url: SecretStr | None = None
    llm_api_key: SecretStr | None = None
    llm_base_url: str = 'https://api.deepseek.com'
    llm_model: str = 'deepseek-flash'
    embedding_api_key: SecretStr | None = None
    embedding_base_url: str | None = None
    embedding_region_confirmed: bool = False
    embedding_model: str = 'text-embedding-v4'
    embedding_dimensions: int = Field(default=1024, gt=0)
    milvus_uri: str = str(ROOT / 'var' / 'milvus.db')
    milvus_token: SecretStr | None = None
    data_dir: Path = ROOT / 'var'
    generation_timeout: float = 90
    context_budget: int = 8000
    upload_limit: int = 10 * 1024 * 1024
    extracted_limit: int = 1_000_000

    def missing(self) -> list[str]:
        required = ('database_url', 'llm_api_key', 'embedding_api_key', 'embedding_base_url')
        return [name.upper() for name in required if not getattr(self, name)]
