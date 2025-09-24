"""
Service for analyzing item-level feedback to improve quote generation.
"""
import json
from typing import Dict, List, Any, Optional
import asyncpg
from collections import defaultdict, Counter


class ItemFeedbackAnalyzer:
    """Analyzes item-level feedback to provide insights for quote generation."""
    
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
    
    async def get_feedback_insights_for_sku(self, sku: str) -> Dict[str, Any]:
        """Get aggregated feedback insights for a specific SKU."""
        # Get feedback specifically for this SKU - be more restrictive to prevent global leakage
        # Only look for feedback where this exact SKU was the target of feedback
        feedback_data = await self.conn.fetch("""
            SELECT 
                qif.feedback_type,
                qif.rating,
                qif.comment,
                qif.suggested_sku,
                qif.suggested_quantity,
                qif.suggested_price,
                qif.correction_data,
                qif.user_context,
                qi.sku as current_sku,
                qi.description as current_description,
                qi.item_metadata->>'original_sku' as original_sku,
                q.prompt,
                qif.created_at
            FROM quote_item_feedback qif
            JOIN quote_items qi ON qif.quote_item_id = qi.id
            JOIN quotes q ON qif.quote_id = q.id
            WHERE (
                -- Direct feedback on this exact SKU
                qi.sku = $1 
                -- Or feedback where this SKU was suggested as replacement
                OR qif.suggested_sku = $1
                -- Or feedback on the original SKU that this replaced
                OR qi.item_metadata->>'original_sku' = $1
            )
            ORDER BY qif.created_at DESC
        """, sku)
        
        if not feedback_data:
            return {"has_feedback": False}
        
        # Analyze feedback patterns
        feedback_types = [row['feedback_type'] for row in feedback_data]
        ratings = [row['rating'] for row in feedback_data if row['rating']]
        
        # Calculate confidence score based on feedback
        confidence_score = self._calculate_confidence_score(feedback_types, ratings)
        
        # Find common corrections
        corrections = self._analyze_corrections(feedback_data)
        
        # Find common user contexts
        contexts = self._analyze_user_contexts(feedback_data)
        
        # Find suggested alternatives
        alternatives = self._analyze_alternatives(feedback_data)
        
        # Extract SKUs and product descriptions from natural language comments
        nlp_suggestions = self._extract_skus_from_comments(feedback_data)
        print(f"DEBUG: NLP suggestions for SKU {sku}: {nlp_suggestions}")
        if nlp_suggestions:
            # Merge NLP suggestions with structured alternatives
            if 'suggested_skus' not in alternatives:
                alternatives['suggested_skus'] = {}
            
            # Add extracted SKUs
            for sku_suggestion, count in nlp_suggestions.items():
                if sku_suggestion != '_product_descriptions':
                    alternatives['suggested_skus'][sku_suggestion] = alternatives['suggested_skus'].get(sku_suggestion, 0) + count
            
            # Store product descriptions for context
            if '_product_descriptions' in nlp_suggestions:
                alternatives['product_descriptions'] = nlp_suggestions['_product_descriptions']
                print(f"DEBUG: Extracted product descriptions: {nlp_suggestions['_product_descriptions']}")
            
            print(f"DEBUG: Updated alternatives: {alternatives}")
        
        return {
            "has_feedback": True,
            "confidence_score": confidence_score,
            "feedback_count": len(feedback_data),
            "feedback_types": dict(Counter(feedback_types)),
            "average_rating": sum(ratings) / len(ratings) if ratings else None,
            "corrections": corrections,
            "contexts": contexts,
            "alternatives": alternatives,
            "recent_feedback": [
                {
                    "feedback_type": row['feedback_type'],
                    "rating": row['rating'],
                    "comment": row['comment'],
                    "suggested_sku": row['suggested_sku'],
                    "created_at": row['created_at'].isoformat() if hasattr(row, 'created_at') else None
                }
                for row in feedback_data[:5]  # Last 5 feedback entries
            ]
        }
    
    async def get_feedback_insights_for_prompt(self, prompt: str) -> Dict[str, Any]:
        """Get feedback insights relevant to a specific prompt."""
        # Extract key terms from prompt for matching
        prompt_terms = self._extract_key_terms(prompt)
        
        # Find similar quotes and their feedback
        similar_quotes = await self.conn.fetch("""
            SELECT 
                q.id,
                q.prompt,
                q.extracted_intent,
                qi.sku,
                qi.description,
                qif.feedback_type,
                qif.rating,
                qif.comment,
                qif.suggested_sku,
                qif.correction_data
            FROM quotes q
            JOIN quote_items qi ON q.id = qi.quote_id
            LEFT JOIN quote_item_feedback qif ON qi.id = qif.quote_item_id
            WHERE q.prompt ILIKE ANY($1)
            ORDER BY q.created_at DESC
            LIMIT 50
        """, [f"%{term}%" for term in prompt_terms])
        
        # Analyze patterns
        sku_feedback = defaultdict(list)
        for row in similar_quotes:
            if row['feedback_type']:
                sku_feedback[row['sku']].append({
                    'feedback_type': row['feedback_type'],
                    'rating': row['rating'],
                    'comment': row['comment'],
                    'suggested_sku': row['suggested_sku']
                })
        
        # Generate insights
        insights = {}
        for sku, feedbacks in sku_feedback.items():
            if feedbacks:
                feedback_types = [f['feedback_type'] for f in feedbacks]
                ratings = [f['rating'] for f in feedbacks if f['rating']]
                
                insights[sku] = {
                    "confidence_score": self._calculate_confidence_score(feedback_types, ratings),
                    "feedback_count": len(feedbacks),
                    "common_issues": dict(Counter(feedback_types)),
                    "average_rating": sum(ratings) / len(ratings) if ratings else None,
                    "suggested_alternatives": list(set([f['suggested_sku'] for f in feedbacks if f['suggested_sku']]))
                }
        
        return insights
    
    async def get_feedback_insights_for_missing_product(self, product_name: str, prompt: str) -> Dict[str, Any]:
        """Get feedback insights for a product that was missing from a quote."""
        # Look for feedback where this product was mentioned in the prompt or comments
        # This handles the case where a product was missing and feedback was provided
        feedback_data = await self.conn.fetch("""
            SELECT 
                qif.feedback_type,
                qif.rating,
                qif.comment,
                qif.suggested_sku,
                qif.suggested_quantity,
                qif.suggested_price,
                qif.correction_data,
                qif.user_context,
                qi.sku as current_sku,
                qi.description as current_description,
                qi.item_metadata->>'original_sku' as original_sku,
                q.prompt
            FROM quote_item_feedback qif
            JOIN quote_items qi ON qif.quote_item_id = qi.id
            JOIN quotes q ON qif.quote_id = q.id
            WHERE qif.feedback_type = 'missing'
               AND (q.prompt ILIKE '%' || $1 || '%' 
                   OR qif.comment ILIKE '%' || $1 || '%'
                   OR qi.item_metadata->>'original_sku' ILIKE '%' || $1 || '%')
            ORDER BY qif.created_at DESC
        """, product_name)
        
        if not feedback_data:
            return {"has_feedback": False}
        
        # Analyze feedback patterns
        feedback_types = [row['feedback_type'] for row in feedback_data]
        ratings = [row['rating'] for row in feedback_data if row['rating']]
        
        # Calculate confidence score based on feedback
        confidence_score = self._calculate_confidence_score(feedback_types, ratings)
        
        # Find common corrections
        corrections = self._analyze_corrections(feedback_data)
        
        # Find common user contexts
        contexts = self._analyze_user_contexts(feedback_data)
        
        # Find suggested alternatives
        alternatives = self._analyze_alternatives(feedback_data)
        
        # Extract SKUs and product descriptions from natural language comments
        nlp_suggestions = self._extract_skus_from_comments(feedback_data)
        print(f"DEBUG: NLP suggestions for missing product {product_name}: {nlp_suggestions}")
        if nlp_suggestions:
            # Merge NLP suggestions with structured alternatives
            if 'suggested_skus' not in alternatives:
                alternatives['suggested_skus'] = {}
            
            # Add extracted SKUs
            for sku_suggestion, count in nlp_suggestions.items():
                if sku_suggestion != '_product_descriptions':
                    alternatives['suggested_skus'][sku_suggestion] = alternatives['suggested_skus'].get(sku_suggestion, 0) + count
            
            # Store product descriptions for context
            if '_product_descriptions' in nlp_suggestions:
                alternatives['product_descriptions'] = nlp_suggestions['_product_descriptions']
                print(f"DEBUG: Extracted product descriptions: {nlp_suggestions['_product_descriptions']}")
            
            print(f"DEBUG: Updated alternatives: {alternatives}")
        
        return {
            "has_feedback": True,
            "confidence_score": confidence_score,
            "feedback_count": len(feedback_data),
            "feedback_types": dict(Counter(feedback_types)),
            "average_rating": sum(ratings) / len(ratings) if ratings else None,
            "corrections": corrections,
            "contexts": contexts,
            "alternatives": alternatives,
            "recent_feedback": [
                {
                    "feedback_type": row['feedback_type'],
                    "rating": row['rating'],
                    "comment": row['comment'],
                    "suggested_sku": row['suggested_sku'],
                    "created_at": row['created_at'].isoformat() if hasattr(row, 'created_at') else None
                }
                for row in feedback_data[:5]  # Last 5 feedback entries
            ]
        }
    
    async def get_learning_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for improving quote generation based on feedback."""
        # Get problematic SKUs
        problematic_skus = await self.conn.fetch("""
            SELECT 
                qi.sku,
                qi.description,
                COUNT(qif.id) as feedback_count,
                AVG(qif.rating) as avg_rating,
                STRING_AGG(DISTINCT qif.feedback_type, ', ') as feedback_types
            FROM quote_item_feedback qif
            JOIN quote_items qi ON qif.quote_item_id = qi.id
            WHERE qif.feedback_type != 'correct'
            GROUP BY qi.sku, qi.description
            HAVING COUNT(qif.id) >= 2
            ORDER BY feedback_count DESC
            LIMIT 20
        """)
        
        # Get common correction patterns
        correction_patterns = await self.conn.fetch("""
            SELECT 
                correction_data->>'field' as field,
                correction_data->>'reason' as reason,
                COUNT(*) as count
            FROM quote_item_feedback
            WHERE correction_data IS NOT NULL
            GROUP BY correction_data->>'field', correction_data->>'reason'
            ORDER BY count DESC
            LIMIT 10
        """)
        
        # Get user context patterns
        context_patterns = await self.conn.fetch("""
            SELECT 
                user_context->>'use_case' as use_case,
                user_context->>'environment' as environment,
                COUNT(*) as count
            FROM quote_item_feedback
            WHERE user_context IS NOT NULL
            GROUP BY user_context->>'use_case', user_context->>'environment'
            ORDER BY count DESC
            LIMIT 10
        """)
        
        return {
            "problematic_skus": [
                {
                    "sku": row['sku'],
                    "description": row['description'],
                    "feedback_count": row['feedback_count'],
                    "avg_rating": float(row['avg_rating']) if row['avg_rating'] else None,
                    "feedback_types": row['feedback_types'].split(', ')
                }
                for row in problematic_skus
            ],
            "correction_patterns": [
                {
                    "field": row['field'],
                    "reason": row['reason'],
                    "count": row['count']
                }
                for row in correction_patterns
            ],
            "context_patterns": [
                {
                    "use_case": row['use_case'],
                    "environment": row['environment'],
                    "count": row['count']
                }
                for row in context_patterns
            ]
        }
    
    def _calculate_confidence_score(self, feedback_types: List[str], ratings: List[int]) -> float:
        """Calculate confidence score based on feedback types and ratings."""
        if not feedback_types:
            return 1.0
        
        # Weight different feedback types
        type_weights = {
            'correct': 1.0,
            'incorrect': 0.2,
            'missing': 0.1,
            'wrong_quantity': 0.6,
            'wrong_price': 0.4,
            'wrong_specs': 0.3
        }
        
        # Calculate weighted average
        weighted_score = sum(type_weights.get(ft, 0.5) for ft in feedback_types) / len(feedback_types)
        
        # Adjust based on ratings if available
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            rating_factor = avg_rating / 5.0  # Normalize to 0-1
            weighted_score = (weighted_score + rating_factor) / 2
        
        return min(1.0, max(0.0, weighted_score))
    
    def _analyze_corrections(self, feedback_data: List[Any]) -> Dict[str, Any]:
        """Analyze correction patterns from feedback data."""
        corrections = defaultdict(list)
        
        for row in feedback_data:
            if row['correction_data']:
                correction_data = row['correction_data']
                if isinstance(correction_data, str):
                    correction_data = json.loads(correction_data)
                
                for field, value in correction_data.items():
                    corrections[field].append(value)
        
        # Find most common corrections
        common_corrections = {}
        for field, values in corrections.items():
            common_corrections[field] = dict(Counter(values))
        
        return common_corrections
    
    def _analyze_user_contexts(self, feedback_data: List[Any]) -> Dict[str, Any]:
        """Analyze user context patterns from feedback data."""
        contexts = defaultdict(list)
        
        for row in feedback_data:
            if row['user_context']:
                context_data = row['user_context']
                if isinstance(context_data, str):
                    context_data = json.loads(context_data)
                
                for key, value in context_data.items():
                    contexts[key].append(value)
        
        # Find most common contexts
        common_contexts = {}
        for key, values in contexts.items():
            common_contexts[key] = dict(Counter(values))
        
        return common_contexts
    
    def _analyze_alternatives(self, feedback_data: List[Any]) -> Dict[str, Any]:
        """Analyze suggested alternatives from feedback data."""
        alternatives = {
            'suggested_skus': [],
            'suggested_quantities': [],
            'suggested_prices': []
        }
        
        for row in feedback_data:
            if row['suggested_sku']:
                alternatives['suggested_skus'].append(row['suggested_sku'])
            if row['suggested_quantity']:
                alternatives['suggested_quantities'].append(row['suggested_quantity'])
            if row['suggested_price']:
                alternatives['suggested_prices'].append(row['suggested_price'])
        
        # Find most common alternatives
        return {
            'suggested_skus': dict(Counter(alternatives['suggested_skus'])),
            'suggested_quantities': dict(Counter(alternatives['suggested_quantities'])),
            'suggested_prices': dict(Counter(alternatives['suggested_prices']))
        }

    def _extract_skus_from_comments(self, feedback_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Extract SKUs and product suggestions from natural language comments using regex patterns."""
        import re
        from collections import Counter
        
        # SKU patterns (exact matches)
        sku_patterns = [
            r'replace\s+(?:this\s+product\s+)?with\s+(?:this\s+product\s+)?([A-Z0-9\-]+)',  # "Replace this product with 03170-001"
            r'use\s+([A-Z0-9\-]+)',  # "Use 03170-001"
            r'suggest\s+([A-Z0-9\-]+)',  # "Suggest 03170-001"
            r'recommend\s+([A-Z0-9\-]+)',  # "Recommend 03170-001"
            r'sku\s*:?\s*([A-Z0-9\-]+)',  # "SKU: 03170-001"
            r'part\s+number\s*:?\s*([A-Z0-9\-]+)',  # "Part number: 03170-001"
            r'([A-Z]{2,}\s+[A-Z0-9\-]+)',  # "AXIS 03170-001" or similar
            r'([A-Z0-9]{3,}-[A-Z0-9\-]+)',  # Pattern like "03170-001"
        ]
        
        # Product description patterns (for learning context)
        product_patterns = [
            r'replace\s+(?:this\s+product\s+with\s+)?(?:a\s+)?([^,\.]+?)(?:\s+instead|\s+camera|\s+unit|$)',  # "Replace with outdoor dome camera"
            r'use\s+(?:a\s+)?([^,\.]+?)(?:\s+instead|\s+camera|\s+unit|$)',  # "Use outdoor dome camera"
            r'suggest\s+(?:a\s+)?([^,\.]+?)(?:\s+instead|\s+camera|\s+unit|$)',  # "Suggest outdoor dome camera"
            r'recommend\s+(?:a\s+)?([^,\.]+?)(?:\s+instead|\s+camera|\s+unit|$)',  # "Recommend outdoor dome camera"
            r'need\s+(?:a\s+)?([^,\.]+?)(?:\s+instead|\s+camera|\s+unit|$)',  # "Need outdoor dome camera"
            r'want\s+(?:a\s+)?([^,\.]+?)(?:\s+instead|\s+camera|\s+unit|$)',  # "Want outdoor dome camera"
        ]
        
        extracted_skus = Counter()
        extracted_products = Counter()
        
        for row in feedback_data:
            comment = row.get('comment', '')
            if not comment:
                continue
                
            comment_lower = comment.lower()
            
            # Skip if it's already a structured suggestion
            if row.get('suggested_sku'):
                continue
                
            # Try SKU patterns first
            for pattern in sku_patterns:
                matches = re.findall(pattern, comment, re.IGNORECASE)
                for match in matches:
                    # Clean up the match
                    sku = match.strip().upper()
                    # Basic validation - should contain letters and numbers/hyphens
                    if len(sku) >= 3 and re.match(r'^[A-Z0-9\-]+$', sku):
                        extracted_skus[sku] += 1
                        print(f"DEBUG: Extracted SKU from comment: '{comment}' -> '{sku}'")
            
            # Try product description patterns
            for pattern in product_patterns:
                matches = re.findall(pattern, comment, re.IGNORECASE)
                for match in matches:
                    # Clean up the match
                    product_desc = match.strip().lower()
                    # Basic validation - should be meaningful
                    if len(product_desc) >= 3 and not product_desc in ['this', 'that', 'it', 'the', 'a', 'an']:
                        extracted_products[product_desc] += 1
                        print(f"DEBUG: Extracted product description from comment: '{comment}' -> '{product_desc}'")
        
        # Store product descriptions in metadata for future learning
        result = dict(extracted_skus)
        if extracted_products:
            result['_product_descriptions'] = dict(extracted_products)
        
        return result
    
    def _extract_key_terms(self, prompt: str) -> List[str]:
        """Extract key terms from a prompt for matching similar quotes."""
        # Simple keyword extraction - could be enhanced with NLP
        import re
        
        # Remove common words and extract meaningful terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
        
        words = re.findall(r'\b\w+\b', prompt.lower())
        key_terms = [word for word in words if word not in stop_words and len(word) > 2]
        
        return key_terms[:10]  # Limit to top 10 terms
