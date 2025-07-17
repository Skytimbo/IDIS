# /api/app/routers/entities.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from .. import schemas, services, security, database
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from context_store import ContextStore

router = APIRouter(
    prefix="/entities",
    tags=["Entities"],
    dependencies=[Depends(security.get_api_key)]
)

# For MVP, we'll simulate a user_id
DUMMY_USER_ID = "user_a"

@router.get("/", response_model=List[schemas.Entity])
async def read_entities(db: ContextStore = Depends(database.get_context_store)):
    entities = services.get_all_entities_for_user(db, user_id=DUMMY_USER_ID)
    return entities

@router.post("/", response_model=schemas.Entity, status_code=201)
async def create_entity(entity: schemas.EntityCreate, db: ContextStore = Depends(database.get_context_store)):
    new_entity_id = services.create_new_entity(db, entity=entity, user_id=DUMMY_USER_ID)
    # Fetch the full entity object to return it
    new_entity = db.get_entity_by_id(new_entity_id)
    return new_entity