# FastAPI server essentials
from fastapi import FastAPI
import uvicorn

# Routers
from CRUD.user.services import router as user_router
from CRUD.face.services import router as face_router

app = FastAPI()

app.include_router(user_router, prefix="/user", tags=["User"])
app.include_router(face_router, prefix="/face", tags=["Face"])

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
