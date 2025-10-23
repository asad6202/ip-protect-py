"""
OpenAI Agent Workflow for Quote Generation
Implements a multi-agent workflow for processing quote requests with guardrails
"""
import os
import json
from typing import Dict, Any, List, Optional
from openai import OpenAI
from agents import Agent, Runner
from pydantic import BaseModel


class GuardrailsResult(BaseModel):
    """Result from guardrails checks"""
    safe: bool
    issues: Dict[str, Any]
    safe_text: Optional[str] = None


class AgentWorkflow:
    """
    Multi-agent workflow for quote generation with safety guardrails
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not self.client.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
    
    async def run_guardrails(self, input_text: str) -> GuardrailsResult:
        """
        Run safety guardrails on input text
        Checks for: PII, harmful content, jailbreak attempts
        """
        try:
            # Use OpenAI moderation API for content safety
            moderation_response = self.client.moderations.create(input=input_text)
            moderation_result = moderation_response.results[0]
            
            issues = {}
            safe = True
            
            # Check moderation flags
            if moderation_result.flagged:
                safe = False
                flagged_categories = [
                    category for category, flagged 
                    in moderation_result.categories.model_dump().items() 
                    if flagged
                ]
                issues['moderation'] = {
                    'failed': True,
                    'flagged_categories': flagged_categories
                }
            
            # Simple PII detection using GPT
            pii_check_response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a PII detector. Return 'true' if the text contains personal identifiable information (email, phone, SSN, credit card, address), otherwise return 'false'. Respond with only 'true' or 'false'."
                    },
                    {"role": "user", "content": input_text}
                ],
                temperature=0.0
            )
            
            pii_content = pii_check_response.choices[0].message.content
            has_pii = pii_content.strip().lower() == 'true' if pii_content else False
            
            if has_pii:
                safe = False
                issues['pii'] = {
                    'failed': True,
                    'detected_counts': ['potential_pii:1']
                }
            
            return GuardrailsResult(
                safe=safe,
                issues=issues,
                safe_text=input_text if safe else None
            )
            
        except Exception as e:
            # If guardrails fail, be conservative and flag as unsafe
            return GuardrailsResult(
                safe=False,
                issues={'error': str(e)},
                safe_text=None
            )
    
    async def classify_intent(self, input_text: str) -> Dict[str, Any]:
        """
        Router agent: Classify the type of request
        Returns intent type: quote_request, rfp, pricing_update, or rule_edit
        """
        try:
            # Create router agent
            router_agent = Agent(
                name="Router Agent",
                instructions="""You are a classification agent for the Protect IP workflow.
Your only job is to decide what type of request this is and return a small JSON object.

Possible intents:
- "quote_request": A natural-language request for a quote or list of products (e.g., "Need 3 outdoor 4K IR cameras and an NVR")
- "rfp": The user uploaded or mentioned an RFP or tender document
- "pricing_update": The user mentioned price lists, vendors, or distributor updates
- "rule_edit": The user mentioned rules, constraints, or company policies

Return ONLY JSON:
{
  "intent": "<one of the four above>",
  "normalized": { "details you extracted, if any" }
}
No prose or explanations.
If unsure, choose "quote_request".""",
                model="gpt-4o"
            )
            
            # Run the agent using Runner
            result = await Runner.run(router_agent, input_text)
            
            # Parse the agent's output
            content = result.final_output
            if not content:
                return {"intent": "quote_request", "normalized": {}}
            result_data = json.loads(content)
            return result_data
            
        except Exception as e:
            # Default to quote_request if classification fails
            return {
                "intent": "quote_request",
                "normalized": {},
                "error": str(e)
            }
    
    async def generate_quote(self, input_text: str, product_catalog_context: str = "") -> Dict[str, Any]:
        """
        Quote Builder Agent: Generate quote from natural language request
        """
        try:
            instructions = f"""You are an expert quoting assistant for a CCTV security integrator.

PRODUCT CATALOG CONTEXT
{product_catalog_context if product_catalog_context else "Use your knowledge of common security camera products"}

CRITICAL INSTRUCTIONS
1) Parse the USER REQUEST and extract product requirements (tolerate typos like "outdor" = "outdoor")
2) Include essential installation components for a complete system:
   - Cameras (as requested)
   - NVR (Network Video Recorder) - 1 unit to record all cameras (ensure sufficient channels)
   - PoE Switch - 1 unit to power all cameras (ensure sufficient ports)
   - Note: Skip cables/patch cords as they're sourced separately
3) Calculate quantities intelligently:
   - NVR channels: At least equal to camera count (round up to common sizes: 4, 8, 16, 32)
   - Switch ports: At least equal to camera count + 1 for uplink (round up to common sizes: 8, 16, 24, 48)
4) For each item, specify detailed requirements using DATABASE-FRIENDLY TERMS:
   - Cameras: Use "2mp", "4mp", "5mp", "8mp", "ir", "poe", "vandal", "ik10", "h.265"
   - NVR: MUST include "recorder" in features array
   - Switches: Use "poe", and port count like "8-port", "16-port" 
   - Note: Skip standalone cables/accessories since they're typically sourced separately

OUTPUT FORMAT (JSON):
{{
  "items": [
    {{
      "family": "camera|nvr|switch|accessory",
      "quantity": <number>,
      "formFactor": "dome|bullet|turret|box|ptz|server|switch",
      "location": "indoor|outdoor|any",
      "features": ["5mp", "ir", "poe", "vandal", "h.265", etc.],
      "budgetPerUnit": {{"amount": <number>, "currency": "CAD"}},
      "brandPreference": ["axis", "hanwha", "ipro"],
      "notes": "Specific requirements or assumptions"
    }}
  ],
  "global": {{
    "totalBudget": {{"amount": <number>, "currency": "CAD"}},
    "preferredBrands": [],
    "avoidPtz": false
  }},
  "summary": "Brief explanation of complete system and assumptions"
}}

EXAMPLE: If user says "Need 4 outdoor cameras"
Return items for: 
- 4x outdoor bullet cameras with features ["5mp", "ir", "poe", "outdoor", "vandal"]
- 1x NVR with features ["recorder"] (MUST include "recorder")
- 1x PoE switch with features ["8-port", "poe"]

Return ONLY valid JSON."""
            
            # Create quote builder agent
            quote_builder_agent = Agent(
                name="Quote Builder Agent",
                instructions=instructions,
                model="gpt-4o"
            )
            
            # Run the agent using Runner
            result = await Runner.run(quote_builder_agent, input_text)
            
            # Parse the agent's output
            content = result.final_output
            print("=" * 80)
            print("DEBUG - Agent response content:")
            print(content)
            print("=" * 80)
            
            if not content:
                raise Exception("Empty response from OpenAI")
            
            # Strip markdown code block markers if present
            content_stripped = content.strip()
            if content_stripped.startswith("```json"):
                content_stripped = content_stripped[7:]  # Remove ```json
            elif content_stripped.startswith("```"):
                content_stripped = content_stripped[3:]  # Remove ```
            if content_stripped.endswith("```"):
                content_stripped = content_stripped[:-3]  # Remove trailing ```
            content_stripped = content_stripped.strip()
            
            # Try to parse JSON with error handling
            try:
                result_data = json.loads(content_stripped)
                # Ensure it's a dict
                if not isinstance(result_data, dict):
                    print(f"WARNING - Expected dict, got {type(result_data).__name__}, returning raw content")
                    return {"raw_content": content}
                return result_data
            except json.JSONDecodeError as e:
                print(f"WARNING - Failed to parse JSON: {e}")
                print(f"Returning raw content instead")
                # Return the content as-is wrapped in a dict
                return {"raw_content": content}
            
        except Exception as e:
            raise Exception(f"Quote generation failed: {str(e)}")
    
    async def process_quote_request(self, input_text: str) -> Dict[str, Any]:
        """
        Main workflow: Process a quote request through all agents with guardrails
        """
        # Step 1: Run guardrails
        guardrails_result = await self.run_guardrails(input_text)
        
        if not guardrails_result.safe:
            return {
                "status": "blocked",
                "reason": "guardrails_triggered",
                "issues": guardrails_result.issues
            }
        
        # Step 2: Classify intent
        classification = await self.classify_intent(input_text)
        intent_type = classification.get("intent", "quote_request")
        
        # Step 3: Process based on intent
        if intent_type == "quote_request":
            quote_data = await self.generate_quote(input_text)
            return {
                "status": "success",
                "intent": classification,
                "quote_data": quote_data
            }
        else:
            # For other intents, return the classification
            return {
                "status": "success",
                "intent": classification,
                "message": f"Request classified as: {intent_type}"
            }


# Global instance
_agent_workflow: Optional[AgentWorkflow] = None


def get_agent_workflow() -> AgentWorkflow:
    """Get or create the agent workflow instance"""
    global _agent_workflow
    if _agent_workflow is None:
        _agent_workflow = AgentWorkflow()
    return _agent_workflow
