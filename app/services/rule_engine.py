"""
Rule Engine for applying business rules during quote generation.
"""

import json
import asyncpg
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RuleExecution:
    rule_id: str
    rule_name: str
    fired: bool
    details: Dict[str, Any]
    applied_at: datetime

class RuleEngine:
    """Engine for evaluating and applying business rules during quote generation."""
    
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
    
    async def get_active_rules(self) -> List[Dict[str, Any]]:
        """Get all active rules from the database."""
        query = """
            SELECT r.id, r.name, r.scope, r.priority, r.condition, r.actions, rs.name as rule_set_name
            FROM rules r
            JOIN rule_sets rs ON r.rule_set_id = rs.id
            WHERE r.active = true AND rs.is_active = true
            ORDER BY r.priority ASC, r.created_at ASC
        """
        rows = await self.conn.fetch(query)
        
        # Parse JSON strings to dictionaries
        rules = []
        for row in rows:
            rule_dict = dict(row)
            # Parse condition and actions from JSON strings
            if isinstance(rule_dict['condition'], str):
                rule_dict['condition'] = json.loads(rule_dict['condition'])
            if isinstance(rule_dict['actions'], str):
                rule_dict['actions'] = json.loads(rule_dict['actions'])
            rules.append(rule_dict)
        
        return rules
    
    async def apply_rules_to_candidates(
        self, 
        candidates: List[Dict[str, Any]], 
        item_want: Dict[str, Any],
        quote_context: Dict[str, Any] = None
    ) -> Tuple[List[Dict[str, Any]], List[RuleExecution]]:
        """
        Apply all active rules to product candidates and return filtered/scored candidates.
        
        Args:
            candidates: List of product candidates from search
            item_want: The item requirements from intent extraction
            quote_context: Additional context about the quote (optional)
        
        Returns:
            Tuple of (filtered_candidates, rule_executions)
        """
        if not candidates:
            return candidates, []
        
        # Get active rules
        rules = await self.get_active_rules()
        if not rules:
            return candidates, []
        
        rule_executions = []
        filtered_candidates = []
        
        for candidate in candidates:
            candidate_score = 1.0  # Base score
            candidate_passed = True
            applied_rules = []
            
            for rule in rules:
                # Check if rule applies to this candidate
                if self._rule_applies(rule, candidate, item_want, quote_context):
                    # Apply rule actions
                    score_modifier, passed, details = self._apply_rule_actions(
                        rule, candidate, item_want, quote_context
                    )
                    
                    # Update candidate score
                    candidate_score *= score_modifier
                    
                    # Check if candidate should be filtered out
                    if not passed:
                        candidate_passed = False
                        break
                    
                    # Record rule execution
                    applied_rules.append({
                        'rule_id': rule['id'],
                        'rule_name': rule['name'],
                        'score_modifier': score_modifier,
                        'details': details
                    })
            
            # Only include candidates that passed all filter rules
            if candidate_passed:
                # Add score to candidate metadata
                candidate['rule_score'] = candidate_score
                candidate['applied_rules'] = applied_rules
                filtered_candidates.append(candidate)
            
            # Record all rule executions for this candidate
            for rule in rules:
                rule_execution = RuleExecution(
                    rule_id=rule['id'],
                    rule_name=rule['name'],
                    fired=rule['id'] in [r['rule_id'] for r in applied_rules],
                    details={
                        'candidate_sku': candidate.get('sku'),
                        'candidate_description': candidate.get('description'),
                        'applied_rules': applied_rules,
                        'final_score': candidate_score if candidate_passed else 0
                    },
                    applied_at=datetime.utcnow()
                )
                rule_executions.append(rule_execution)
        
        # Sort by rule score (highest first)
        filtered_candidates.sort(key=lambda x: x.get('rule_score', 1.0), reverse=True)
        
        return filtered_candidates, rule_executions
    
    def _rule_applies(
        self, 
        rule: Dict[str, Any], 
        candidate: Dict[str, Any], 
        item_want: Dict[str, Any],
        quote_context: Dict[str, Any] = None
    ) -> bool:
        """Check if a rule applies to the given candidate."""
        condition = rule['condition']
        scope = rule['scope']
        
        # For item-level rules, check the candidate
        if scope == 'item':
            return self._evaluate_condition(condition, candidate, item_want)
        
        # For global rules, check the quote context
        elif scope == 'global':
            context = quote_context or {}
            return self._evaluate_condition(condition, context, item_want)
        
        return False
    
    def _evaluate_condition(
        self, 
        condition: Dict[str, Any], 
        target: Dict[str, Any], 
        item_want: Dict[str, Any]
    ) -> bool:
        """Evaluate a rule condition against a target object."""
        try:
            # Handle different condition types
            for field, expected in condition.items():
                if field == 'brand':
                    target_brand = target.get('brand', '').lower()
                    expected_brand = expected.lower()
                    if target_brand != expected_brand:
                        return False
                
                elif field == 'family':
                    target_family = target.get('family', '').lower()
                    expected_family = expected.lower()
                    if target_family != expected_family:
                        return False
                
                elif field == 'description':
                    if isinstance(expected, dict) and 'contains' in expected:
                        target_desc = (target.get('description') or '').lower()
                        expected_text = expected['contains'].lower()
                        if expected_text not in target_desc:
                            return False
                
                elif field == 'price':
                    target_price = float(target.get('price', 0))
                    if isinstance(expected, dict):
                        if 'gte' in expected and target_price < expected['gte']:
                            return False
                        if 'lte' in expected and target_price > expected['lte']:
                            return False
                        if 'gt' in expected and target_price <= expected['gt']:
                            return False
                        if 'lt' in expected and target_price >= expected['lt']:
                            return False
                    else:
                        if target_price != expected:
                            return False
                
                elif field == 'switch_ports':
                    target_ports = target.get('switch_ports', 0)
                    if isinstance(expected, dict):
                        if 'gte' in expected and target_ports < expected['gte']:
                            return False
                        if 'lte' in expected and target_ports > expected['lte']:
                            return False
                    else:
                        if target_ports != expected:
                            return False
                
                elif field == 'nvr_channels':
                    target_channels = target.get('nvr_channels', 0)
                    if isinstance(expected, dict):
                        if 'gte' in expected and target_channels < expected['gte']:
                            return False
                        if 'lte' in expected and target_channels > expected['lte']:
                            return False
                    else:
                        if target_channels != expected:
                            return False
                
                # Add more field types as needed
                else:
                    # Generic field matching
                    target_value = target.get(field)
                    if target_value != expected:
                        return False
            
            return True
            
        except (ValueError, TypeError, KeyError) as e:
            # If there's an error evaluating the condition, assume it doesn't match
            return False
    
    def _apply_rule_actions(
        self, 
        rule: Dict[str, Any], 
        candidate: Dict[str, Any], 
        item_want: Dict[str, Any],
        quote_context: Dict[str, Any] = None
    ) -> Tuple[float, bool, Dict[str, Any]]:
        """
        Apply rule actions to a candidate.
        
        Returns:
            Tuple of (score_modifier, passed, details)
        """
        actions = rule['actions']
        score_modifier = 1.0
        passed = True
        details = {}
        
        try:
            # Apply boost_score action
            if 'boost_score' in actions:
                boost = float(actions['boost_score'])
                score_modifier *= boost
                details['boost_score'] = boost
            
            # Apply filter action
            if 'filter' in actions and actions['filter']:
                # This is a hard filter - candidate must pass all conditions
                # The filter logic is handled in the condition evaluation
                details['filtered'] = True
            
            # Add more action types as needed
            if 'penalty' in actions:
                penalty = float(actions['penalty'])
                score_modifier *= penalty
                details['penalty'] = penalty
            
            return score_modifier, passed, details
            
        except (ValueError, TypeError, KeyError) as e:
            # If there's an error applying actions, don't modify the candidate
            return 1.0, True, {'error': str(e)}
    
    async def log_rule_executions(
        self, 
        quote_id: str, 
        rule_executions: List[RuleExecution]
    ) -> None:
        """Log rule executions to the database."""
        if not rule_executions:
            return
        
        query = """
            INSERT INTO rule_executions (id, quote_id, rule_id, fired, details, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        
        for execution in rule_executions:
            execution_id = f"exec_{execution.rule_id}_{datetime.utcnow().timestamp()}"
            await self.conn.execute(
                query,
                execution_id,
                quote_id,
                execution.rule_id,
                execution.fired,
                json.dumps(execution.details),
                execution.applied_at
            )
