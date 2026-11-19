import logging
import os
import time
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging_config import setup_logging
from .routes import router as api_router
from .web import router as web_router

app = FastAPI(
    title="FishTrack API",
    version="0.1.0",
)

logger = setup_logging()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)


# ============================================
# MIDDLEWARE: REQUEST ID + JSON LOGGING
# ============================================


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id

    started = time.perf_counter()
    exception_type = None

    try:
        response = await call_next(request)

    except Exception as exc:
        exception_type = type(exc).__name__

        response = await generic_exception_handler(request, exc)

    duration_ms = round(
        (time.perf_counter() - started) * 1000,
        2,
    )

    status_code = response.status_code

    route = request.scope.get("route")

    path = route.path if route is not None else "unmatched"

    if status_code >= 500:
        result = "server_error"
        level = logging.ERROR

    elif status_code >= 400:
        result = "client_error"
        level = logging.WARNING

    else:
        result = "success"
        level = logging.INFO

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Instance-ID"] = os.getenv("INSTANCE_ID", "unknown")

    logger.log(
        level,
        "http_request",
        extra={
            "event": "http_request",
            "method": request.method,
            "path": path,
            "status_code": status_code,
            "result": result,
            "duration_ms": duration_ms,
            "request_id": request_id,
            "exception_type": exception_type,
        },
    )

    return response


# ============================================
# ROUTERS
# ============================================

app.include_router(
    api_router,
    prefix="/api/v1",
)

app.include_router(web_router)


# ============================================
# SYSTEM ENDPOINTS
# ============================================


@app.get("/version", tags=["system"])
def get_version():
    return {
        "app": "fishtrack",
        "version": os.getenv("IMAGE_TAG", "unknown"),
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "FishTrack",
    }


# ============================================
# ERROR HANDLERS
# ============================================


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    # Не возвращаем input и ctx из ошибок Pydantic:
    # они могут содержать переданные пользователем секреты.
    safe_errors = [
        {
            "field": ".".join(str(part) for part in error.get("loc", [])),
            "code": error.get("type", "invalid"),
        }
        for error in exc.errors()
    ]

    accept = request.headers.get("accept", "")

    if "text/html" in accept:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "code": 400,
                "message": "Некорректные данные",
                "details": safe_errors,
            },
            status_code=400,
        )

    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation error",
            "details": safe_errors,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
):
    accept = request.headers.get("accept", "")

    if "text/html" in accept:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "code": exc.status_code,
                "message": exc.detail,
                "details": None,
            },
            status_code=exc.status_code,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request,
    exc: Exception,
):
    # Не возвращаем str(exc):
    # сообщение исключения может содержать секреты.
    accept = request.headers.get("accept", "")

    if "text/html" in accept:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "code": 500,
                "message": "Внутренняя ошибка сервера",
                "details": None,
            },
            status_code=500,
        )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": getattr(
                request.state,
                "request_id",
                None,
            ),
        },
    )
