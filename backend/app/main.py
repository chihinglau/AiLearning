from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    admin,
    auth,
    exams,
    family,
    health,
    learn,
    org,
    practice,
    public,
    textbooks,
    users,
)
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401  确保模型在 create_all / Alembic 前完成注册


@asynccontextmanager
async def lifespan(app: FastAPI):
    """本地开发可开启自动建表；生产环境请使用 Alembic 迁移。"""
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description="深爱学（AiLearning）—— 深圳中小学跨平台学习辅助应用后端服务",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(public.router, prefix=settings.api_prefix)
app.include_router(practice.router, prefix=settings.api_prefix)
app.include_router(learn.router, prefix=settings.api_prefix)
app.include_router(exams.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(family.router, prefix=settings.api_prefix)
app.include_router(org.router, prefix=settings.api_prefix)
app.include_router(textbooks.router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "docs": "/docs", "health": "/health"}
