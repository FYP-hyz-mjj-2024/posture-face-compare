from database import engine
from user.models import Base

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
