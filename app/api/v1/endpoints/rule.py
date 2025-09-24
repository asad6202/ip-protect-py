"""
Rule management endpoints for the IP Protect system.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from db import Database, get_database
import uuid
import json

router = APIRouter()

# Pydantic models for request/response
class RuleSetResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    priority: int
    created_at: str
    updated_at: str

class CreateRuleSetRequest(BaseModel):
    name: str
    is_active: bool = True
    priority: int = 100

class UpdateRuleSetRequest(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None

class RuleResponse(BaseModel):
    id: str
    rule_set_id: str
    name: str
    active: bool
    scope: str
    priority: int
    condition: Dict[str, Any]
    actions: Dict[str, Any]
    nlp_command: Optional[str] = None
    created_at: str
    updated_at: str

class CreateRuleRequest(BaseModel):
    rule_set_id: str
    name: str
    active: bool = True
    scope: str
    priority: int = 100
    condition: Dict[str, Any]
    actions: Dict[str, Any]

class UpdateRuleRequest(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None
    scope: Optional[str] = None
    priority: Optional[int] = None
    condition: Optional[Dict[str, Any]] = None
    actions: Optional[Dict[str, Any]] = None

# Rule Sets endpoints
@router.get("/rule_sets", response_model=List[RuleSetResponse])
async def list_rule_sets(
    db: Database = Depends(get_database)
) -> List[RuleSetResponse]:
    """Get all rule sets."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            query = """
                SELECT id, name, is_active, priority, created_at, updated_at
                FROM rule_sets
                ORDER BY priority, created_at
            """
            rows = await conn.fetch(query)
            
            return [
                RuleSetResponse(
                    id=row['id'],
                    name=row['name'],
                    is_active=row['is_active'],
                    priority=row['priority'],
                    created_at=row['created_at'].isoformat(),
                    updated_at=row['updated_at'].isoformat()
                )
                for row in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rule sets: {str(e)}")

@router.get("/rule_sets/{rule_set_id}", response_model=RuleSetResponse)
async def get_rule_set(
    rule_set_id: str,
    db: Database = Depends(get_database)
) -> RuleSetResponse:
    """Get a specific rule set by ID."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            query = """
                SELECT id, name, is_active, priority, created_at, updated_at
                FROM rule_sets
                WHERE id = $1
            """
            row = await conn.fetchrow(query, rule_set_id)
            
            if not row:
                raise HTTPException(status_code=404, detail="Rule set not found")
            
            return RuleSetResponse(
                id=row['id'],
                name=row['name'],
                is_active=row['is_active'],
                priority=row['priority'],
                created_at=row['created_at'].isoformat(),
                updated_at=row['updated_at'].isoformat()
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rule set: {str(e)}")

@router.post("/rule_sets", response_model=RuleSetResponse)
async def create_rule_set(
    request: CreateRuleSetRequest,
    db: Database = Depends(get_database)
) -> RuleSetResponse:
    """Create a new rule set."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            rule_set_id = str(uuid.uuid4())
            query = """
                INSERT INTO rule_sets (id, name, is_active, priority)
                VALUES ($1, $2, $3, $4)
                RETURNING id, name, is_active, priority, created_at, updated_at
            """
            row = await conn.fetchrow(
                query, 
                rule_set_id, 
                request.name, 
                request.is_active, 
                request.priority
            )
            
            return RuleSetResponse(
                id=row['id'],
                name=row['name'],
                is_active=row['is_active'],
                priority=row['priority'],
                created_at=row['created_at'].isoformat(),
                updated_at=row['updated_at'].isoformat()
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create rule set: {str(e)}")

@router.patch("/rule_sets/{rule_set_id}", response_model=RuleSetResponse)
async def update_rule_set(
    rule_set_id: str,
    request: UpdateRuleSetRequest,
    db: Database = Depends(get_database)
) -> RuleSetResponse:
    """Update a rule set."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # Check if rule set exists
            check_query = "SELECT id FROM rule_sets WHERE id = $1"
            existing = await conn.fetchrow(check_query, rule_set_id)
            
            if not existing:
                raise HTTPException(status_code=404, detail="Rule set not found")
            
            # Build update query dynamically
            update_data = request.dict(exclude_unset=True)
            if not update_data:
                # If no fields to update, just return the existing rule set
                query = """
                    SELECT id, name, is_active, priority, created_at, updated_at
                    FROM rule_sets WHERE id = $1
                """
                row = await conn.fetchrow(query, rule_set_id)
            else:
                set_clauses = []
                values = []
                param_count = 1
                
                for field, value in update_data.items():
                    set_clauses.append(f"{field} = ${param_count}")
                    values.append(value)
                    param_count += 1
                
                values.append(rule_set_id)  # Add rule_set_id as last parameter
                
                query = f"""
                    UPDATE rule_sets 
                    SET {', '.join(set_clauses)}, updated_at = now()
                    WHERE id = ${param_count}
                    RETURNING id, name, is_active, priority, created_at, updated_at
                """
                row = await conn.fetchrow(query, *values)
            
            return RuleSetResponse(
                id=row['id'],
                name=row['name'],
                is_active=row['is_active'],
                priority=row['priority'],
                created_at=row['created_at'].isoformat(),
                updated_at=row['updated_at'].isoformat()
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update rule set: {str(e)}")

@router.delete("/rule_sets/{rule_set_id}")
async def delete_rule_set(
    rule_set_id: str,
    db: Database = Depends(get_database)
):
    """Delete a rule set."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # Check if rule set exists
            check_query = "SELECT id FROM rule_sets WHERE id = $1"
            existing = await conn.fetchrow(check_query, rule_set_id)
            
            if not existing:
                raise HTTPException(status_code=404, detail="Rule set not found")
            
            # Delete rule set (cascade will handle rules)
            delete_query = "DELETE FROM rule_sets WHERE id = $1"
            await conn.execute(delete_query, rule_set_id)
            
            return {"message": "Rule set deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete rule set: {str(e)}")

# Rules endpoints
@router.get("/rule_sets/{rule_set_id}/rules", response_model=List[RuleResponse])
async def list_rules(
    rule_set_id: str,
    db: Database = Depends(get_database)
) -> List[RuleResponse]:
    """Get all rules for a specific rule set."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            query = """
                SELECT id, rule_set_id, name, active, scope, priority, condition, actions, nlp_command, created_at, updated_at
                FROM rules
                WHERE rule_set_id = $1
                ORDER BY priority, created_at
            """
            rows = await conn.fetch(query, rule_set_id)
            
            return [
                RuleResponse(
                    id=row['id'],
                    rule_set_id=row['rule_set_id'],
                    name=row['name'],
                    active=row['active'],
                    scope=row['scope'],
                    priority=row['priority'],
                    condition=row['condition'] if isinstance(row['condition'], dict) else json.loads(row['condition']),
                    actions=row['actions'] if isinstance(row['actions'], dict) else json.loads(row['actions']),
                    nlp_command=row.get('nlp_command'),
                    created_at=row['created_at'].isoformat(),
                    updated_at=row['updated_at'].isoformat()
                )
                for row in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rules: {str(e)}")

@router.post("/rules", response_model=RuleResponse)
async def create_rule(
    request: CreateRuleRequest,
    db: Database = Depends(get_database)
) -> RuleResponse:
    """Create a new rule."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # Check if rule set exists
            check_query = "SELECT id FROM rule_sets WHERE id = $1"
            rule_set = await conn.fetchrow(check_query, request.rule_set_id)
            
            if not rule_set:
                raise HTTPException(status_code=404, detail="Rule set not found")
            
            rule_id = str(uuid.uuid4())
            query = """
                INSERT INTO rules (id, rule_set_id, name, active, scope, priority, condition, actions, nlp_command)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id, rule_set_id, name, active, scope, priority, condition, actions, nlp_command, created_at, updated_at
            """
            row = await conn.fetchrow(
                query,
                rule_id,
                request.rule_set_id,
                request.name,
                request.active,
                request.scope,
                request.priority,
                json.dumps(request.condition),
                json.dumps(request.actions),
                getattr(request, 'nlp_command', None)
            )
            
            return RuleResponse(
                id=row['id'],
                rule_set_id=row['rule_set_id'],
                name=row['name'],
                active=row['active'],
                scope=row['scope'],
                priority=row['priority'],
                condition=row['condition'] if isinstance(row['condition'], dict) else json.loads(row['condition']),
                actions=row['actions'] if isinstance(row['actions'], dict) else json.loads(row['actions']),
                nlp_command=row.get('nlp_command'),
                created_at=row['created_at'].isoformat(),
                updated_at=row['updated_at'].isoformat()
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create rule: {str(e)}")

@router.patch("/rules/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: str,
    request: UpdateRuleRequest,
    db: Database = Depends(get_database)
) -> RuleResponse:
    """Update a rule."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # Check if rule exists
            check_query = "SELECT id FROM rules WHERE id = $1"
            existing = await conn.fetchrow(check_query, rule_id)
            
            if not existing:
                raise HTTPException(status_code=404, detail="Rule not found")
            
            # Build update query dynamically
            update_data = request.dict(exclude_unset=True)
            if not update_data:
                # If no fields to update, just return the existing rule
                query = """
                    SELECT id, rule_set_id, name, active, scope, priority, condition, actions, created_at, updated_at
                    FROM rules WHERE id = $1
                """
                row = await conn.fetchrow(query, rule_id)
            else:
                set_clauses = []
                values = []
                param_count = 1
                
                for field, value in update_data.items():
                    if field in ['condition', 'actions']:
                        # JSON fields need to be serialized
                        set_clauses.append(f"{field} = ${param_count}")
                        values.append(json.dumps(value))
                    else:
                        set_clauses.append(f"{field} = ${param_count}")
                        values.append(value)
                    param_count += 1
                
                values.append(rule_id)  # Add rule_id as last parameter
                
                query = f"""
                    UPDATE rules 
                    SET {', '.join(set_clauses)}, updated_at = now()
                    WHERE id = ${param_count}
                    RETURNING id, rule_set_id, name, active, scope, priority, condition, actions, created_at, updated_at
                """
                row = await conn.fetchrow(query, *values)
            
            return RuleResponse(
                id=row['id'],
                rule_set_id=row['rule_set_id'],
                name=row['name'],
                active=row['active'],
                scope=row['scope'],
                priority=row['priority'],
                condition=row['condition'] if isinstance(row['condition'], dict) else json.loads(row['condition']),
                actions=row['actions'] if isinstance(row['actions'], dict) else json.loads(row['actions']),
                nlp_command=row.get('nlp_command'),
                created_at=row['created_at'].isoformat(),
                updated_at=row['updated_at'].isoformat()
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update rule: {str(e)}")

@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    db: Database = Depends(get_database)
):
    """Delete a rule."""
    try:
        if not db._pool:
            await db.connect()

        async with db._pool.acquire() as conn:
            # Check if rule exists
            check_query = "SELECT id FROM rules WHERE id = $1"
            existing = await conn.fetchrow(check_query, rule_id)
            
            if not existing:
                raise HTTPException(status_code=404, detail="Rule not found")
            
            # Delete rule
            delete_query = "DELETE FROM rules WHERE id = $1"
            await conn.execute(delete_query, rule_id)
            
            return {"message": "Rule deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete rule: {str(e)}")
