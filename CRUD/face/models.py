from sqlalchemy import Column, String, DateTime, LargeBinary, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import text

# Root reference
from database import Base


class Face(Base):
    __tablename__ = 'faces'

    id = Column(UUID(as_uuid=True),
                primary_key=True,
                default=text("uuid_generate_v4()"),
                server_default=text("uuid_generate_v4()"),
                index=True)

    uploaded_at = Column(DateTime(timezone=True),
                         default=func.now(),
                         server_default=func.now(),
                         nullable=False)

    uploaded_by = Column(UUID(as_uuid=True),
                         primary_key=False,
                         index=True,
                         nullable=False)

    blob = Column(LargeBinary, nullable=False)

    feature = Column(JSON, nullable=False)

    description = Column(String, nullable=True)
