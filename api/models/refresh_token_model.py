from sqlalchemy import Boolean, Column, ForeignKey, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from db.database import Base
import uuid


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
