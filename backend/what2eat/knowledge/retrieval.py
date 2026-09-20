from uuid import UUID
import jieba
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi


def rrf(rankings: list[list[str]], k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, key in enumerate(dict.fromkeys(ranking), start=1):
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda key: (-scores[key], key))


def _tokens(text: str) -> list[str]:
    return [token.strip().lower() for token in jieba.cut_for_search(text) if token.strip()]


class Retriever:
    def __init__(self, index, documents):
        self.index = index
        self.documents = documents
        self._lexical_documents: list[Document] = []
        self._bm25: BM25Okapi | None = None

    def replace_lexical_documents(self, documents: list[Document]) -> None:
        self._lexical_documents = list(documents)
        corpus = [_tokens(document.page_content) or [''] for document in documents]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def _lexical_ranking(self, query: str, limit: int) -> list[Document]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(_tokens(query))
        order = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), i))
        return [self._lexical_documents[index] for index in order[:limit] if scores[index] > 0]

    async def search(self, query: str, limit: int = 5, mode: str = 'hybrid') -> list[Document]:
        limit = max(1, min(limit, 20))
        vector_pairs = await self.index.search(query, max(limit * 3, 10))
        vector_documents = [document for document, _ in vector_pairs]
        lexical_documents = self._lexical_ranking(query, max(limit * 3, 10)) if mode == 'hybrid' else []
        all_documents = vector_documents + lexical_documents
        by_chunk = {str(doc.metadata['chunk_id']): doc for doc in all_documents}
        rankings = [[str(doc.metadata['chunk_id']) for doc in vector_documents]]
        if lexical_documents:
            rankings.append([str(doc.metadata['chunk_id']) for doc in lexical_documents])
        ranked_keys = rrf(rankings)
        document_ids = [UUID(str(by_chunk[key].metadata['document_id'])) for key in ranked_keys]
        ready = await self.documents.ready_ids(document_ids)
        result: list[Document] = []
        seen: set[str] = set()
        for key in ranked_keys:
            document = by_chunk[key]
            if UUID(str(document.metadata['document_id'])) not in ready or key in seen:
                continue
            seen.add(key)
            result.append(document)
            if len(result) == limit:
                break
        return result
