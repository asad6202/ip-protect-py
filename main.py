import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from db import Database
from gpt import generate_sql_from_nl
from schemas import QueryRequest, QueryResponse


app = FastAPI(title="NL2SQL API", version="1.0.0")

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

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
        # Normalize live schema to include 'status' for UI compatibility
        for row in results:
            if 'status' not in row:
                if 'active' in row:
                    row['status'] = 'active' if row.get('active') else 'inactive'
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    return QueryResponse(results=results, sql=sql)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "NL2SQL Demo",
        },
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


