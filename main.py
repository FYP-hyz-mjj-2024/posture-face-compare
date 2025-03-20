# Basic
import os

# FastAPI server essentials
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# Routers
from CRUD.user.services import router as user_router
from CRUD.face.services import router as face_router

load_dotenv()

app = FastAPI()

SERVER_HOST = os.getenv("SERVER_HOST")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],    # Allow specific requests
    allow_credentials=True,
    allow_methods=["*"],    # Allow all HTTP methods
    allow_headers=["*"],    # Allow all HTTP headers
)

app.include_router(user_router, prefix="/user", tags=["User"])
app.include_router(face_router, prefix="/face", tags=["Face"])

if __name__ == "__main__":
    uvicorn.run(app, host=f"{SERVER_HOST}", port=8001)
