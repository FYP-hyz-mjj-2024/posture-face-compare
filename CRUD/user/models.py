from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import text

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True),
                primary_key=True,
                default=text("uuid_generate_v4()"),
                server_default=text("uuid_generate_v4()"),
                index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    name = Column(String)
    is_verified = Column(Boolean, default=False)
