from pymongo import MongoClient
from dotenv import load_dotenv
import os
from pymongo.database import Database

load_dotenv(".env.local")

client : MongoClient | None = None
db : Database | None = None


def connect_to_db():
    global client, db
    url = os.getenv("MONGO_URL")
    if not url:
        raise RuntimeError("MONGO_URL is not set")
    client = MongoClient(url, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[os.getenv("MONGO_DB","recoverai")]
    return client, db


def close_db():
    global db, client
    if client:
        client.close()
    client = None
    db = None


def get_db():
    if db is None:
        raise RuntimeError("Database not connected")
    return db