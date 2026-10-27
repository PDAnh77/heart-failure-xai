from sqlalchemy import Column, ForeignKey, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from db.database import Base
import uuid

class BatchPrediction(Base):
    __tablename__ = "batch_predictions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    source_dataset_id = Column(String, nullable=True)
    result_dataset_id = Column(String, nullable=False)
    summary = Column(JSONB, nullable=False)
    batch_xai = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())