from uuid import uuid4
from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


async def error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={'error': {
        'code': exc.code, 'message': exc.message,
        'request_id': getattr(request.state, 'request_id', str(uuid4())),
    }})


def require_database(request: Request):
    pool = getattr(request.app.state, 'pool', None)
    if pool is None:
        raise AppError('database_unavailable', 'PostgreSQL 尚未就绪，请检查本机配置。', 503)
    return pool
