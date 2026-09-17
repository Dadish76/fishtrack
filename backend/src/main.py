from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.templating import Jinja2Templates
from .database import engine, Base, SessionLocal, hash_password
from .models import User
from .routes import router as api_router
from .web import router as web_router

# Создать таблицы
Base.metadata.create_all(bind=engine)


def create_default_admin():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            admin = User(
                username="admin",
                hashed_password=hash_password("admin"),
                is_admin=True,
            )
            db.add(admin)
            db.commit()
            print("✅ Создан пользователь admin/admin")
    finally:
        db.close()


create_default_admin()

app = FastAPI(title="FishTrack API", version="0.1.0")

app.include_router(api_router, prefix="/api/v1")
app.include_router(web_router)

templates = Jinja2Templates(directory="backend/src/templates")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "FishTrack"}


# ОБРАБОТКА ОШИБОК

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"code": 400, "message": "Некорректные данные", "details": exc.errors()},
            status_code=400,
        )
    return JSONResponse(status_code=400, content={"error": "Validation error", "details": exc.errors()})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"code": exc.status_code, "message": exc.detail, "details": None},
            status_code=exc.status_code,
        )
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"code": 500, "message": "Внутренняя ошибка сервера", "details": str(exc)},
            status_code=500,
        )
    return JSONResponse(status_code=500, content={"error": "Internal server error", "details": str(exc)})
