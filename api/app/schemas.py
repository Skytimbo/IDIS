# /api/app/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# --- Base Models ---
class EntityBase(BaseModel):
    entity_name: str

class CaseBase(BaseModel):
    case_name: str
    status: Optional[str] = "Active"
    status_detail: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    deadline_date: Optional[datetime] = None

class DocumentBase(BaseModel):
    filename: str
    content_type: str

# --- Create Models (for POST/PUT requests) ---
class EntityCreate(EntityBase):
    pass

class CaseCreate(CaseBase):
    entity_id: int

# --- Full Models (for GET responses) ---
class Entity(EntityBase):
    id: int
    user_id: str
    creation_timestamp: datetime

    class Config:
        from_attributes = True

class Case(CaseBase):
    id: int
    entity_id: int
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Document(DocumentBase):
    id: int
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True