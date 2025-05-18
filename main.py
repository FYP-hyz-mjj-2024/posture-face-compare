# Basic
import os

# FastAPI server essentials
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Routers
from CRUD.user.services import router as user_router
from CRUD.face.services import router as face_router

load_dotenv()

app = FastAPI()

SERVER_HOST = os.getenv("SERVER_HOST")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://www.youfocusyourwalk.top",
        "https://youfocusyourwalk.top"
    ],    # Allow specific requests
    allow_credentials=True,
    allow_methods=["*"],    # Allow all HTTP methods
    allow_headers=["*"],    # Allow all HTTP headers
)

app.include_router(user_router, prefix="/user", tags=["User"])
app.include_router(face_router, prefix="/face", tags=["Face"])


# Serve static files from the "static" directory
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run(app, host=f"{SERVER_HOST}", port=8001)
