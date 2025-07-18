# /api/main.py
from fastapi import FastAPI
from app.routers import entities, cases
# from app.routers import documents # Add later

app = FastAPI(
    title="IDIS API",
    description="The official API for the Intelligent Document Insight System.",
    version="1.0.0"
)

# Include all the routers
app.include_router(entities.router)
app.include_router(cases.router)
# app.include_router(documents.router) # Uncomment when documents.py is created

@app.get("/", tags=["Health Check"])
async def read_root():
    return {"status": "IDIS API is running"}