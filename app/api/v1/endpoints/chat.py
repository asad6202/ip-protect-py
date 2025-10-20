"""
Chat endpoint for interactive quote modifications with file attachments.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from pydantic import BaseModel
import json
from app.services.chat_service import ChatService
from db import Database

router = APIRouter()

# Global database instance
db_instance = None


def get_database() -> Database:
    """Get database instance."""
    global db_instance
    if db_instance is None:
        db_instance = Database()
    return db_instance


class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    attachments: Optional[List[Dict[str, Any]]] = None


class ChatRequest(BaseModel):
    quote_id: str
    message: str
    chat_history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    message: str
    updated_items: Optional[List[Dict[str, Any]]] = None
    modifications: Optional[Dict[str, Any]] = None


@router.post("/chat/modify-quote")
async def modify_quote_with_chat(
    quote_id: str = Form(...),
    message: str = Form(...),
    chat_history: str = Form("[]"),
    files: List[UploadFile] = File(default=[]),
    db: Database = Depends(get_database)
):
    """
    Process chat message to modify a quote.
    Supports file attachments (images, PDFs, etc.) for context.
    """
    try:
        if not db._pool:
            await db.connect()

        # Parse chat history
        history = json.loads(chat_history) if chat_history else []
        
        # Process uploaded files
        file_contents = []
        for file in files:
            content = await file.read()
            file_contents.append({
                'filename': file.filename,
                'content_type': file.content_type,
                'data': content
            })

        async with db._pool.acquire() as conn:
            chat_service = ChatService(conn)
            result = await chat_service.process_chat_message(
                quote_id=quote_id,
                message=message,
                chat_history=history,
                attachments=file_contents
            )
            return result
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@router.get("/chat/{quote_id}/history")
async def get_chat_history(
    quote_id: str,
    db: Database = Depends(get_database)
):
    """Get chat history for a quote."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            chat_service = ChatService(conn)
            history = await chat_service.get_chat_history(quote_id)
            return {"history": history}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat history: {str(e)}")
