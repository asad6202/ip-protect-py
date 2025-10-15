#!/usr/bin/env python3
"""Test script to debug agent workflow output"""
import asyncio
import json
from app.ai.agent_workflow import get_agent_workflow

async def test_agent():
    agent = get_agent_workflow()
    
    prompt = "Need 4 outdor cameras"
    print(f"Testing prompt: {prompt}\n")
    
    result = await agent.process_quote_request(prompt)
    
    print("Agent workflow result:")
    print(json.dumps(result, indent=2))
    
    if result.get("status") == "success" and result.get("quote_data"):
        print("\n\nQuote data items:")
        for i, item in enumerate(result["quote_data"].get("items", [])):
            print(f"\nItem {i+1}:")
            print(f"  Family: {item.get('family')}")
            print(f"  Quantity: {item.get('quantity')}")
            print(f"  FormFactor: {item.get('formFactor')}")
            print(f"  Location: {item.get('location')}")
            print(f"  Features: {item.get('features')}")
            print(f"  Notes: {item.get('notes')}")

if __name__ == "__main__":
    asyncio.run(test_agent())
