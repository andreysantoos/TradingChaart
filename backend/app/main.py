import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import init_db
from app.api.routes import router as api_router
from app.services.ingestion import ingestion_service
from app.providers.binance_futures import binance_provider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing REA Trading Platform database...")
    init_db()
    
    # Start background ingestion loop
    ingestion_task = asyncio.create_task(ingestion_service.start())
    logger.info("Ingestion service background task spawned.")
    
    yield
    
    # Shutdown logic
    logger.info("Shutting down services...")
    ingestion_service.stop()
    if not ingestion_task.done():
        ingestion_task.cancel()
    await binance_provider.close()
    logger.info("Services safely closed.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_PREFIX)

@app.get("/")
def root():
    return {
        "platform": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs": "/docs"
    }
