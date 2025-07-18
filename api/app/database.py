# /api/app/database.py
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from context_store import ContextStore # Assuming context_store.py is in the project root

DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'production_idis.db')

def get_context_store():
    db = ContextStore(DATABASE_PATH)
    try:
        yield db
    finally:
        pass