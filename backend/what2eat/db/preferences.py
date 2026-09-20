from uuid import UUID
from langgraph.store.postgres import AsyncPostgresStore
from pydantic import BaseModel, ConfigDict, Field


class Preferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    diners: int = Field(default=2, ge=1, le=12)
    tastes: list[str] = Field(default_factory=list, max_length=20)
    allergens: list[str] = Field(default_factory=list, max_length=30)
    excluded_ingredients: list[str] = Field(default_factory=list, max_length=50)
    pantry: list[str] = Field(default_factory=list, max_length=100)


class PreferenceRepository:
    def __init__(self, pool):
        self.store = AsyncPostgresStore(pool, index=None)

    @staticmethod
    def namespace(user_id: UUID):
        return ('what2eat', str(user_id), 'preferences')

    async def get(self, user_id: UUID) -> dict:
        item = await self.store.aget(self.namespace(user_id), 'profile')
        return item.value if item else {}

    async def put(self, user_id: UUID, value: dict) -> dict:
        value = Preferences.model_validate(value).model_dump()
        await self.store.aput(self.namespace(user_id), 'profile', value)
        return value

    async def clear(self, user_id: UUID) -> None:
        await self.store.adelete(self.namespace(user_id), 'profile')
