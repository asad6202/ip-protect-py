"""
NLP Rule parsing endpoints for converting natural language to rules.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from db import Database, get_database
from app.ai.rule_parser import RuleParser, ParsedRule
import json
import uuid

router = APIRouter()

# Pydantic models
class NLPRuleRequest(BaseModel):
    command: str
    rule_set_id: str

class NLPRuleResponse(BaseModel):
    name: str
    condition: Dict[str, Any]
    actions: Dict[str, Any]
    scope: str
    priority: int

class NLPSuggestionsRequest(BaseModel):
    partial_command: str

class NLPSuggestionsResponse(BaseModel):
    suggestions: List[str]

class CreateRuleFromNLPRequest(BaseModel):
    command: str
    rule_set_id: str
    name: str = None  # Optional override for rule name

# Initialize parser
rule_parser = RuleParser()

@router.post("/parse-nlp-rule", response_model=NLPRuleResponse)
async def parse_nlp_rule(request: NLPRuleRequest) -> NLPRuleResponse:
    """Parse a natural language command into rule format."""
    try:
        parsed_rule = rule_parser.parse_nlp_command(request.command)
        
        return NLPRuleResponse(
            name=parsed_rule.name,
            condition=parsed_rule.condition,
            actions=parsed_rule.actions,
            scope=parsed_rule.scope,
            priority=parsed_rule.priority
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse command: {str(e)}")

@router.post("/nlp-suggestions", response_model=NLPSuggestionsResponse)
async def get_nlp_suggestions(request: NLPSuggestionsRequest) -> NLPSuggestionsResponse:
    """Get suggestions for completing a natural language command."""
    try:
        suggestions = rule_parser.get_suggestions(request.partial_command)
        return NLPSuggestionsResponse(suggestions=suggestions)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get suggestions: {str(e)}")

@router.post("/create-rule-from-nlp", response_model=Dict[str, Any])
async def create_rule_from_nlp(
    request: CreateRuleFromNLPRequest,
    db: Database = Depends(get_database)
) -> Dict[str, Any]:
    """Create a rule directly from natural language command."""
    try:
        if not db._pool:
            await db.connect()

        # Parse the NLP command
        parsed_rule = rule_parser.parse_nlp_command(request.command)
        
        # Use provided name or parsed name
        rule_name = request.name or parsed_rule.name
        
        async with db._pool.acquire() as conn:
            # Check if rule set exists
            check_query = "SELECT id FROM rule_sets WHERE id = $1"
            existing = await conn.fetchrow(check_query, request.rule_set_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Rule set not found")
            
            # Create the rule
            rule_id = str(uuid.uuid4())
            insert_query = """
                INSERT INTO rules (id, rule_set_id, name, active, scope, priority, condition, actions, nlp_command)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id, name, active, scope, priority, condition, actions, nlp_command, created_at, updated_at
            """
            
            row = await conn.fetchrow(
                insert_query,
                rule_id,
                request.rule_set_id,
                rule_name,
                True,  # active
                parsed_rule.scope,
                parsed_rule.priority,
                json.dumps(parsed_rule.condition),
                json.dumps(parsed_rule.actions),
                request.command  # Store the original NLP command
            )
            
            return {
                "id": row['id'],
                "name": row['name'],
                "active": row['active'],
                "scope": row['scope'],
                "priority": row['priority'],
                "condition": row['condition'],
                "actions": row['actions'],
                "created_at": row['created_at'].isoformat(),
                "updated_at": row['updated_at'].isoformat(),
                "nlp_command": row['nlp_command']
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create rule from NLP: {str(e)}")

@router.get("/rule-templates", response_model=List[Dict[str, str]])
async def get_rule_templates() -> List[Dict[str, str]]:
    """Get common rule templates for users to choose from."""
    templates = [
        {
            "name": "Prefer Axis Brand",
            "command": "Prefer Axis cameras and equipment",
            "description": "Boosts Axis products in search results"
        },
        {
            "name": "Avoid PTZ Cameras", 
            "command": "Avoid PTZ cameras",
            "description": "Reduces preference for PTZ cameras"
        },
        {
            "name": "Outdoor Cameras Only",
            "command": "Require outdoor cameras only",
            "description": "Filters to only show outdoor-rated cameras"
        },
        {
            "name": "Budget Filter",
            "command": "Filter cameras under $500",
            "description": "Only shows cameras under $500"
        },
        {
            "name": "High Resolution Preference",
            "command": "Prefer 4K cameras",
            "description": "Boosts 4K cameras in results"
        },
        {
            "name": "Switch Port Requirement",
            "command": "Require switches with at least 24 ports",
            "description": "Filters switches to minimum 24 ports"
        },
        {
            "name": "POE Only",
            "command": "Require POE cameras only",
            "description": "Filters to only POE-powered cameras"
        },
        {
            "name": "Avoid Wireless",
            "command": "Avoid wireless cameras",
            "description": "Reduces preference for wireless cameras"
        }
    ]
    
    return templates
