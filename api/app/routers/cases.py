# /api/app/routers/cases.py
from fastapi import APIRouter, Depends
from typing import List
from .. import schemas, services, security, database
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from context_store import ContextStore

router = APIRouter(
    prefix="/cases",
    tags=["Cases"],
    dependencies=[Depends(security.get_api_key)]
)

DUMMY_USER_ID = "user_a"

@router.get("/by_entity/{entity_id}", response_model=List[schemas.Case])
async def read_cases_for_entity(entity_id: int, db: ContextStore = Depends(database.get_context_store)):
    cases = services.get_cases_for_entity(db, entity_id=entity_id, user_id=DUMMY_USER_ID)
    return cases

@router.post("/", response_model=schemas.Case, status_code=201)
async def create_case(case: schemas.CaseCreate, db: ContextStore = Depends(database.get_context_store)):
    new_case_id = services.create_new_case(db, case=case, user_id=DUMMY_USER_ID)
    # Fetch the full case object to return it
    new_case = db.get_case_by_id(new_case_id)
    return new_case