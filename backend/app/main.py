from fastapi import FastAPI
from app.db import connect_to_db, close_db, get_db
from contextlib import asynccontextmanager
from app.routers import payments

@asynccontextmanager
async def lifespan(app: FastAPI):
    connect_to_db()
    yield
    close_db()  

app = FastAPI(lifespan=lifespan)

app.include_router(payments.router)

@app.get("/health")
def health():
    db = get_db()
    db.command("ping")
    return {"status": "ok", "database": "connected"}

@app.get("/")
def root():
    return {"message": "Hello to the RecoverAI API World"}
