from database import engine
from CRUD.face.models import Base

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
