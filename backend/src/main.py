from fastapi import FastAPI
from .database import engine, Base
from .routes import router

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FishTrack API",
    description="Система учета рыболовной фирмы",
    version="0.1.0"
)

# Подключаем роутеры
app.include_router(router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "FishTrack"}