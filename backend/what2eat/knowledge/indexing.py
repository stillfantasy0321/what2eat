from pathlib import Path
from uuid import UUID
from what2eat.knowledge.chunking import split_documents
from what2eat.knowledge.loaders import load_document


class IndexingService:
    def __init__(self, documents, index, retriever=None):
        self.documents = documents
        self.index = index
        self.retriever = retriever

    async def rebuild_lexical(self) -> None:
        if self.retriever is None:
            return
        all_documents = []
        for item in await self.documents.by_state('ready'):
            try:
                docs = load_document(Path(item['source_path']), item['id'])
                for doc in docs:
                    doc.metadata.update({key: item[key] for key in (
                        'title', 'category', 'source_url', 'source_path', 'content_hash', 'index_version')})
                all_documents.extend(split_documents(docs))
            except Exception:
                await self.documents.set_state(item['id'], 'failed', '原文读取失败，请重新上传。')
        self.retriever.replace_lexical_documents(all_documents)

    async def run_background(self, document_id: UUID) -> None:
        # One failed document must not cancel the rest of a BackgroundTasks batch.
        try:
            await self.run(document_id)
        except Exception:
            pass  # run() already records a retryable failure.

    async def run(self, document_id: UUID) -> None:
        record = await self.documents.get(document_id)
        await self.documents.set_state(document_id, 'indexing')
        try:
            loaded = load_document(Path(record['source_path']), document_id)
            for document in loaded:
                document.metadata.update({
                    'title': record['title'], 'category': record['category'],
                    'source_url': record['source_url'], 'source_path': record['source_path'],
                    'content_hash': record['content_hash'], 'index_version': record['index_version'],
                })
            chunks = split_documents(loaded)
            await self.index.delete(document_id)
            await self.index.upsert(chunks)
            await self.documents.set_state(document_id, 'ready')
            await self.rebuild_lexical()
        except Exception as exc:
            await self.documents.set_state(document_id, 'failed', '索引失败，请检查模型配置、额度和文档格式后重试。')
            raise

    async def delete(self, document_id: UUID) -> None:
        record = await self.documents.get(document_id)
        await self.documents.set_state(document_id, 'deleting')
        try:
            await self.index.delete(document_id)
            path = Path(record['source_path'])
            if path.exists():
                path.unlink()
            await self.documents.delete_metadata(document_id)
            await self.rebuild_lexical()
        except Exception as exc:
            await self.documents.set_state(document_id, 'deleting', str(exc)[:1000])
            raise

    async def recover(self) -> None:
        for state in ('pending', 'indexing'):
            for record in await self.documents.by_state(state):
                await self.documents.set_state(record['id'], 'failed', '服务重启中断了索引，可安全重试。')
        await self.rebuild_lexical()
