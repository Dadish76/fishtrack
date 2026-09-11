from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.templating import Jinja2Templates
from .database import engine, Base
from .routes import router as api_router
from .web import router as web_router

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FishTrack API",
    description="Система учета рыболовной фирмы",
    version="0.1.0"
)

# Подключаем API и веб-роуты
app.include_router(api_router, prefix="/api/v1")
app.include_router(web_router)

# Шаблоны для страниц ошибок
templates = Jinja2Templates(directory="backend/src/templates")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "FishTrack"}


# ОБРАБОТКА ОШИБОК
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """400 — некорректные данные"""
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "code": 400, "message": "Некорректные данные", "details": exc.errors()},
            status_code=400,
        )
    return JSONResponse(
        status_code=400,
        content={"error": "Validation error", "details": exc.errors()},
    )


from fastapi import HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """404, 409 и другие HTTP-ошибки"""
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "code": exc.status_code, "message": exc.detail, "details": None},
            status_code=exc.status_code,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """500 — внутренняя ошибка"""
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "code": 500, "message": "Внутренняя ошибка сервера", "details": str(exc)},
            status_code=500,
        )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "details": str(exc)},
    )