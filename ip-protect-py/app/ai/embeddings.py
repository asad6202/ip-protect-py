"""
Text embedding utilities using OpenAI's text-embedding-3-small model.
"""

import os
from typing import List
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def get_embedding(text: str) -> List[float]:
    """
    Generate text embedding using OpenAI's text-embedding-3-small model.
    
    Args:
        text: Input text to embed
        
    Returns:
        List of 1536 float values representing the text embedding
        
    Raises:
        ValueError: If text is empty or None
        Exception: If OpenAI API call fails
    """
    if not text or not text.strip():
        return []
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    if not client.api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text.strip()
        )
        
        return response.data[0].embedding
        
    except Exception as e:
        raise Exception(f"OpenAI embedding API call failed: {e}")


def get_embedding_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in a single API call.
    
    Args:
        texts: List of input texts to embed
        
    Returns:
        List of embeddings, one for each input text
        
    Raises:
        Exception: If OpenAI API call fails
    """
    if not texts:
        return []
    
    # Filter out empty texts
    valid_texts = [text.strip() for text in texts if text and text.strip()]
    
    if not valid_texts:
        return []
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    if not client.api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=valid_texts
        )
        
        return [data.embedding for data in response.data]
        
    except Exception as e:
        raise Exception(f"OpenAI batch embedding API call failed: {e}")


def test_embeddings():
    """Test function for embedding generation."""
    test_texts = [
        "outdoor dome camera with IR night vision and PoE",
        "4K bullet camera with H.265 encoding",
        "16 channel NVR with 2TB storage",
        "24 port PoE switch for surveillance system"
    ]
    
    print("Testing single embedding:")
    try:
        embedding = get_embedding(test_texts[0])
        print(f"Embedding length: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\nTesting batch embeddings:")
    try:
        embeddings = get_embedding_batch(test_texts)
        print(f"Generated {len(embeddings)} embeddings")
        for i, emb in enumerate(embeddings):
            print(f"Text {i+1} embedding length: {len(emb)}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_embeddings()
