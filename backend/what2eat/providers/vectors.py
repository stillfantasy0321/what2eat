import asyncio
import hashlib
import importlib
import re
import threading
from uuid import UUID
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_milvus import Milvus
from pymilvus import MilvusClient as PymilvusClient, connections
from what2eat.config import Settings

_LITE_CONSTRUCTOR_LOCK = threading.Lock()


class _LiteAsyncUnavailable:
    def __init__(self, **kwargs):
        raise RuntimeError('Milvus Lite uses the synchronous client on Windows')


class _LiteLegacyConnectedClient(PymilvusClient):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not connections.has_connection(self._using):
            connections.connect(alias=self._using, **kwargs)


def _collection_name(settings: Settings) -> str:
    fingerprint = hashlib.sha256(
        f'{settings.embedding_model}|{settings.embedding_dimensions}|512|64'.encode()
    ).hexdigest()[:12]
    model = re.sub(r'[^a-zA-Z0-9_]', '_', settings.embedding_model)[:24]
    return f'what2eat_{model}_{fingerprint}'


class VectorIndex:
    def __init__(self, settings: Settings, embeddings: Embeddings):
        connection_args = {'uri': settings.milvus_uri}
        if settings.milvus_token:
            connection_args['token'] = settings.milvus_token.get_secret_value()
        kwargs = dict(
            embedding_function=embeddings, collection_name=_collection_name(settings),
            connection_args=connection_args, auto_id=False, drop_old=False,
            enable_dynamic_field=True,
            index_params={'index_type': 'FLAT', 'metric_type': 'COSINE', 'params': {}},
            search_params={'metric_type': 'COSINE', 'params': {}},
        )
        if not settings.milvus_uri.lower().startswith(('http://', 'https://')):
            module = importlib.import_module('langchain_milvus.vectorstores.milvus')
            with _LITE_CONSTRUCTOR_LOCK:
                original = module.AsyncMilvusClient
                original_client = module.MilvusClient
                module.AsyncMilvusClient = _LiteAsyncUnavailable
                module.MilvusClient = _LiteLegacyConnectedClient
                try:
                    self.store = Milvus(**kwargs)
                finally:
                    module.AsyncMilvusClient = original
                    module.MilvusClient = original_client
        else:
            self.store = Milvus(**kwargs)
        # langchain-milvus 0.3.3 creates both sync and async clients. With a
        # local Windows URI the async client removes the ORM alias created by
        # the sync client; restore that alias and run the proven sync path in
        # a worker thread.
        if not connections.has_connection(self.store.alias):
            connections.connect(alias=self.store.alias, **connection_args)

    async def upsert(self, chunks: list[Document]) -> None:
        if not chunks:
            return
        ids = [str(chunk.metadata['chunk_id']) for chunk in chunks]
        if self.store.client.has_collection(self.store.collection_name):
            await asyncio.to_thread(self.store.delete, ids=ids)
        await asyncio.to_thread(self.store.add_documents, chunks, ids=ids)

    async def search(self, query: str, limit: int) -> list[tuple[Document, float]]:
        return await asyncio.to_thread(
            self.store.similarity_search_with_score, query, max(1, min(limit, 50)))

    async def delete(self, document_id: UUID | str) -> None:
        safe = str(UUID(str(document_id)))
        await asyncio.to_thread(self.store.delete, expr=f'document_id == "{safe}"')

    async def close(self) -> None:
        async_client = getattr(self.store, '_async_milvus_client', None)
        if async_client:
            await async_client.close()
        await asyncio.to_thread(self.store.client.close)
        if connections.has_connection(self.store.alias):
            await asyncio.to_thread(connections.disconnect, self.store.alias)
