"""
Agricultural Traceability Platform - Main Entry
农链溯源平台 - 主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.api import auth, producer, blockchain, processor, inspector, seller
from app.models.user import User, UserRole
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def init_test_users():
    """初始化测试用户"""
    db = SessionLocal()
    try:
        # 检查是否已有用户
        if db.query(User).first():
            print("✅ Users already exist, skipping initialization")
            return

        # 创建测试用户
        test_users = [
            {"username": "producer", "role": UserRole.PRODUCER, "real_name": "张三农场"},
            {"username": "processor", "role": UserRole.PROCESSOR, "real_name": "绿源加工厂"},
            {"username": "inspector", "role": UserRole.INSPECTOR, "real_name": "李质检"},
            {"username": "seller", "role": UserRole.SELLER, "real_name": "优鲜超市"},
            {"username": "consumer", "role": UserRole.CONSUMER, "real_name": "王小明"},
        ]

        for user_data in test_users:
            user = User(
                username=user_data["username"],
                password_hash=pwd_context.hash("123456"),
                role=user_data["role"],
                real_name=user_data["real_name"]
            )
            db.add(user)

        db.commit()
        print("✅ Test users created successfully")
    except Exception as e:
        print(f"❌ Failed to create test users: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup: Create database tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    # Initialize test users
    init_test_users()
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
