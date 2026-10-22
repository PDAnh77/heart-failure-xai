from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID

class BatchPredictionBase(BaseModel):
    source_dataset_id: Optional[str] = None
    result_dataset_id: str
    summary: Dict[str, Any]

class BatchPredictionList(BatchPredictionBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True) 

class BatchPredictionDetail(BatchPredictionList):
    batch_xai: Dict[str, Any]
    model_config = ConfigDict(from_attributes=True)