import hashlib
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
import tiktoken

_ENCODING = tiktoken.get_encoding('cl100k_base')


def token_count(text: str) -> int:
    return len(_ENCODING.encode(text))


def source_hash(text: str) -> str:
    normalized = text.replace('\r\n', '\n').strip()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def _chunk_id(metadata: dict, index: int, text: str) -> str:
    seed = '|'.join((str(metadata['document_id']), str(metadata.get('index_version', 'v1')),
                     str(index), source_hash(text)))
    return hashlib.sha256(seed.encode('utf-8')).hexdigest()


def split_documents(documents: list[Document], chunk_size: int = 512,
                    overlap: int = 64) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=overlap, length_function=token_count,
        separators=['\n## ', '\n### ', '\n\n', '\n', '。', '；', ' ', ''],
    )
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[('#', 'h1'), ('##', 'h2'), ('###', 'h3')], strip_headers=False,
    )
    result: list[Document] = []
    for document in documents:
        metadata = dict(document.metadata)
        metadata.setdefault('index_version', 'v1')
        metadata.setdefault('content_hash', source_hash(document.page_content))
        if token_count(document.page_content) <= chunk_size:
            pieces = [Document(page_content=document.page_content, metadata=metadata)]
        else:
            sections = header_splitter.split_text(document.page_content)
            for section in sections:
                section.metadata = metadata | section.metadata
            pieces = splitter.split_documents(sections)
        for index, piece in enumerate(pieces):
            piece.metadata = metadata | piece.metadata
            piece.metadata['chunk_id'] = _chunk_id(piece.metadata, index, piece.page_content)
            piece.metadata['chunk_index'] = index
            result.append(piece)
    return result
