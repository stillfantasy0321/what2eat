import shutil
from pathlib import Path
from uuid import UUID, uuid4
from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, Request, UploadFile
from what2eat.config import Settings
from what2eat.errors import AppError, require_database
from what2eat.knowledge.chunking import source_hash
from what2eat.knowledge.corpus import verify_corpus
from what2eat.knowledge.indexing import IndexingService
from what2eat.knowledge.repository import DocumentRepository
from what2eat.knowledge.schemas import DocumentContent, DocumentCreate

router = APIRouter(prefix='/api', tags=['documents'])


def _service(request: Request, pool):
    index = getattr(request.app.state, 'index', None)
    if index is None:
        raise AppError('vector_unavailable', '百炼 Embedding 或 Milvus 尚未就绪。', 503)
    return IndexingService(DocumentRepository(pool), index, getattr(request.app.state, 'retriever', None))


@router.get('/documents')
async def documents(page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=50),
                    pool=Depends(require_database)):
    return await DocumentRepository(pool).page(page, page_size)


@router.get('/documents/{document_id}/content', response_model=DocumentContent)
async def document_content(document_id: UUID, pool=Depends(require_database)):
    return await DocumentRepository(pool).content(document_id)


@router.get('/documents/{document_id}')
async def document(document_id: UUID, pool=Depends(require_database)):
    record = await DocumentRepository(pool).get(document_id)
    path = Path(record['source_path'])
    record['content'] = path.read_text(encoding='utf-8', errors='replace') if path.suffix.lower() in {'.md', '.txt'} else None
    return record


@router.post('/documents', status_code=202)
async def upload(request: Request, background: BackgroundTasks, file: UploadFile = File(...),
                 pool=Depends(require_database)):
    service = _service(request, pool)
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in {'.md', '.txt', '.pdf', '.docx'}:
        raise AppError('unsupported_file', '不支持该文件格式。', 415)
    settings: Settings = request.app.state.settings
    document_id = uuid4()
    directory = settings.data_dir / 'uploads'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f'{document_id}{suffix}'
    size = 0
    with path.open('wb') as output:
        while chunk := await file.read(64 * 1024):
            size += len(chunk)
            if size > settings.upload_limit:
                output.close(); path.unlink(missing_ok=True)
                raise AppError('upload_too_large', '单个文件不能超过10 MiB。', 413)
            output.write(chunk)
    digest = source_hash(path.read_text(encoding='utf-8-sig')) if suffix in {'.md', '.txt'} else __import__('hashlib').sha256(path.read_bytes()).hexdigest()
    repo = DocumentRepository(pool)
    record = await repo.create(DocumentCreate(id=document_id, content_hash=digest,
        source_path=str(path), title=Path(file.filename or '文档').stem,
        index_version=request.app.state.index_version))
    if record['id'] != document_id:
        path.unlink(missing_ok=True)
    if record['state'] not in {'ready', 'indexing', 'deleting'}:
        background.add_task(service.run_background, record['id'])
    return record


@router.post('/knowledge/import', status_code=202)
async def import_corpus(request: Request, background: BackgroundTasks, pool=Depends(require_database)):
    service = _service(request, pool)
    manifest_path = Path('data/corpus/manifest.json').resolve()
    verify_corpus(manifest_path)
    import json
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    repo = DocumentRepository(pool)
    created = []
    destination = request.app.state.settings.data_dir / 'corpus'
    destination.mkdir(parents=True, exist_ok=True)
    for recipe in data['recipes']:
        source = manifest_path.parent / recipe['local_path']
        document_id = uuid4()
        target = destination / f'{document_id}.md'
        shutil.copy2(source, target)
        record = await repo.create(DocumentCreate(id=document_id, content_hash=recipe['sha256'],
            source_path=str(target), source_url=recipe['source_url'], title=recipe['title'],
            category=recipe['category'], index_version=request.app.state.index_version,
            metadata={'upstream_path': recipe['upstream_path']}))
        created.append(record['id'])
        if record['id'] != document_id:
            target.unlink(missing_ok=True)
        if record['state'] not in {'ready', 'indexing', 'deleting'}:
            background.add_task(service.run_background, record['id'])
    return {'queued': len(created), 'document_ids': created}


@router.post('/documents/{document_id}/retry', status_code=202)
async def retry(document_id: UUID, request: Request, background: BackgroundTasks,
                pool=Depends(require_database)):
    record = await DocumentRepository(pool).get(document_id)
    if record['state'] == 'deleting':
        background.add_task(_service(request, pool).delete, document_id)
    else:
        background.add_task(_service(request, pool).run_background, document_id)
    return {'queued': True, 'document_id': document_id}


@router.delete('/documents/{document_id}', status_code=202)
async def delete_document(document_id: UUID, request: Request, background: BackgroundTasks,
                          pool=Depends(require_database)):
    await DocumentRepository(pool).set_state(document_id, 'deleting')
    background.add_task(_service(request, pool).delete, document_id)
    return {'queued': True, 'document_id': document_id}
