"""
Agricultural Traceability Platform - Main Entry
农链溯源平台 - 主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.api import auth, producer, blockchain, processor, inspector, seller, ai
from app.models.user import User, UserRole
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup: Create database tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    yield
    # Shutdown
    print("👋 Application shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于 FISCO BCOS 区块链的农产品全程溯源平台 API",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],  # Vue dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix="/api")
app.include_router(producer.router, prefix="/api")
app.include_router(blockchain.router, prefix="/api")
app.include_router(processor.router, prefix="/api")
app.include_router(inspector.router, prefix="/api")
app.include_router(seller.router, prefix="/api")
app.include_router(ai.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "blockchain": "FISCO BCOS 3.0"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
