#!/usr/bin/env python3
"""Test NVR agent output"""
import asyncio
import json
from app.ai.agent_workflow import get_agent_workflow

async def test():
    agent = get_agent_workflow()
    result = await agent.process_quote_request("Need 2 cameras and an NVR")
    
    print("Agent result for 'Need 2 cameras and an NVR':")
    print(json.dumps(result.get("quote_data", {}), indent=2))

asyncio.run(test())
