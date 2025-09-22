import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from db import Database
from gpt import generate_sql_from_nl
from schemas import QueryRequest, QueryResponse
from app.api.v1.router import api_router


app = FastAPI(title="IP Protect API", version="1.0.0")

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=False,  # Set to False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes BEFORE static file mounting
app.include_router(api_router, prefix="/api/v1")

# Mount the built React app for production (AFTER API routes)
import os
import sys

# Check if we're in production mode
is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"

# Only serve the frontend dist files in production mode
if is_production and os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
    print("🚀 Production mode: Serving frontend from dist/")
else:
    print("🔧 Development mode: Frontend served separately (not from dist/)")

db = Database()


@app.on_event("startup")
async def startup_event() -> None:
    await db.connect()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await db.disconnect()


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(payload: QueryRequest) -> QueryResponse:
    # Generate SQL from GPT
    try:
        sql = generate_sql_from_nl(payload.query)
    except Exception as e:
        # Surface auth errors clearly
        raise HTTPException(status_code=401, detail=f"OpenAI error: {e}")

    if not sql:
        raise HTTPException(status_code=400, detail="Failed to generate SQL from query")

    # Execute SQL and return results
    try:
        results = await db.fetch(sql)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    return QueryResponse(results=results, sql=sql)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)


