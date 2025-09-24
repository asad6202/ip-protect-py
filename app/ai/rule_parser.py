"""
NLP Rule Parser - Converts natural language commands to rule format
"""

import re
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

@dataclass
class ParsedRule:
    name: str
    condition: Dict[str, Any]
    actions: Dict[str, Any]
    scope: str = "global"
    priority: int = 100

class RuleParser:
    """Parses natural language commands into rule conditions and actions."""
    
    def __init__(self):
        # Brand mappings
        self.brand_keywords = {
            'axis': ['axis', 'axis communications'],
            'hanwha': ['hanwha', 'hanwha techwin', 'samsung'],
            'hikvision': ['hikvision', 'hik'],
            'dahua': ['dahua', 'dahua technology'],
            'uniview': ['uniview', 'uniview tech'],
            'bosch': ['bosch', 'bosch security'],
            'sony': ['sony'],
            'panasonic': ['panasonic'],
            'i-pro': ['i-pro', 'ipro', 'i pro']
        }
        
        # Product type mappings
        self.type_keywords = {
            'camera': ['camera', 'cameras', 'dome', 'bullet', 'ptz', 'turret', 'sensor'],
            'nvr': ['nvr', 'recorder', 'network video recorder', 'server'],
            'switch': ['switch', 'poe switch', 'ethernet switch', 'network switch'],
            'accessory': ['accessory', 'accessories', 'mount', 'bracket', 'cable']
        }
        
        # Feature mappings
        self.feature_keywords = {
            'outdoor': ['outdoor', 'weatherproof', 'ip65', 'ip66', 'ip67'],
            'indoor': ['indoor', 'internal'],
            'night_vision': ['night vision', 'ir', 'infrared', 'low light'],
            'ptz': ['ptz', 'pan tilt zoom', 'pan-tilt-zoom'],
            'dome': ['dome', 'dome camera'],
            'bullet': ['bullet', 'bullet camera'],
            'wireless': ['wireless', 'wifi', 'wi-fi'],
            'poe': ['poe', 'power over ethernet', 'poe+', '802.3at'],
            'hd': ['hd', 'high definition', '1080p', '4k', '8mp', '12mp'],
            'zoom': ['zoom', 'optical zoom', 'digital zoom']
        }
        
        # Price range patterns
        self.price_patterns = [
            r'under\s+\$?(\d+)',
            r'below\s+\$?(\d+)',
            r'less\s+than\s+\$?(\d+)',
            r'up\s+to\s+\$?(\d+)',
            r'maximum\s+\$?(\d+)',
            r'over\s+\$?(\d+)',
            r'above\s+\$?(\d+)',
            r'more\s+than\s+\$?(\d+)',
            r'minimum\s+\$?(\d+)',
            r'at\s+least\s+\$?(\d+)',
            r'between\s+\$?(\d+)\s+and\s+\$?(\d+)',
            r'from\s+\$?(\d+)\s+to\s+\$?(\d+)'
        ]
        
        # Action keywords
        self.action_keywords = {
            'prefer': ['prefer', 'favor', 'prioritize', 'boost', 'increase'],
            'avoid': ['avoid', 'exclude', 'filter out', 'reduce', 'penalize'],
            'require': ['require', 'must have', 'mandatory', 'essential'],
            'filter': ['filter', 'only', 'exclusively', 'strictly']
        }

    def parse_nlp_command(self, command: str) -> ParsedRule:
        """Parse a natural language command into a rule."""
        command = command.lower().strip()
        
        # Extract rule name (first part before any action words)
        name = self._extract_rule_name(command)
        
        # Determine scope
        scope = self._determine_scope(command)
        
        # Parse condition and actions
        condition, actions = self._parse_condition_and_actions(command)
        
        # Determine priority based on action strength
        priority = self._determine_priority(command, actions)
        
        return ParsedRule(
            name=name,
            condition=condition,
            actions=actions,
            scope=scope,
            priority=priority
        )

    def _extract_rule_name(self, command: str) -> str:
        """Extract a meaningful name from the command."""
        # Remove common action words to get the core concept
        action_words = ['prefer', 'avoid', 'require', 'filter', 'boost', 'exclude']
        words = command.split()
        
        # Find the first action word and take everything before it
        for i, word in enumerate(words):
            if word in action_words:
                return ' '.join(words[:i]).title() or 'Custom Rule'
        
        # If no action word found, take first few words
        return ' '.join(words[:3]).title() or 'Custom Rule'

    def _determine_scope(self, command: str) -> str:
        """Determine if rule should be global or item-level."""
        global_indicators = ['always', 'never', 'overall', 'total', 'budget', 'quote']
        item_indicators = ['camera', 'switch', 'nvr', 'product', 'item', 'each']
        
        for indicator in global_indicators:
            if indicator in command:
                return 'global'
        
        for indicator in item_indicators:
            if indicator in command:
                return 'item'
        
        return 'global'  # Default to global

    def _parse_condition_and_actions(self, command: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Parse the command into condition and action objects."""
        condition = {}
        actions = {}
        
        # Parse brand preferences/avoidances
        brand_condition, brand_action = self._parse_brand_rule(command)
        if brand_condition:
            condition.update(brand_condition)
            actions.update(brand_action)
        
        # Parse product type rules
        type_condition, type_action = self._parse_type_rule(command)
        if type_condition:
            condition.update(type_condition)
            actions.update(type_action)
        
        # Parse feature rules
        feature_condition, feature_action = self._parse_feature_rule(command)
        if feature_condition:
            condition.update(feature_condition)
            actions.update(feature_action)
        
        # Parse price rules
        price_condition, price_action = self._parse_price_rule(command)
        if price_condition:
            condition.update(price_condition)
            actions.update(price_action)
        
        # Parse technical specifications
        tech_condition, tech_action = self._parse_tech_rule(command)
        if tech_condition:
            condition.update(tech_condition)
            actions.update(tech_action)
        
        # If no specific conditions found, create a general rule
        if not condition:
            condition = {"description": {"contains": command}}
            actions = {"boost_score": 1.1}
        
        return condition, actions

    def _parse_brand_rule(self, command: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Parse brand-related rules."""
        condition = {}
        actions = {}
        
        for brand, keywords in self.brand_keywords.items():
            for keyword in keywords:
                if keyword in command:
                    # Check for action type
                    if any(word in command for word in ['prefer', 'favor', 'prioritize', 'boost']):
                        condition['brand'] = brand.title()
                        actions['boost_score'] = 1.2
                        return condition, actions
                    elif any(word in command for word in ['avoid', 'exclude', 'filter out']):
                        condition['brand'] = brand.title()
                        actions['boost_score'] = 0.5
                        return condition, actions
                    elif any(word in command for word in ['require', 'must', 'only']):
                        condition['brand'] = brand.title()
                        actions['filter'] = True
                        return condition, actions
        
        return condition, actions

    def _parse_type_rule(self, command: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Parse product type rules."""
        condition = {}
        actions = {}
        
        for product_type, keywords in self.type_keywords.items():
            for keyword in keywords:
                if keyword in command:
                    if any(word in command for word in ['prefer', 'favor', 'prioritize']):
                        condition['family'] = product_type
                        actions['boost_score'] = 1.1
                        return condition, actions
                    elif any(word in command for word in ['avoid', 'exclude', 'filter out']):
                        condition['family'] = product_type
                        actions['boost_score'] = 0.3
                        return condition, actions
                    elif any(word in command for word in ['require', 'must', 'only']):
                        condition['family'] = product_type
                        actions['filter'] = True
                        return condition, actions
        
        return condition, actions

    def _parse_feature_rule(self, command: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Parse feature-based rules."""
        condition = {}
        actions = {}
        
        for feature, keywords in self.feature_keywords.items():
            for keyword in keywords:
                if keyword in command:
                    if any(word in command for word in ['prefer', 'favor', 'prioritize']):
                        condition['description'] = {"contains": keyword}
                        actions['boost_score'] = 1.1
                        return condition, actions
                    elif any(word in command for word in ['avoid', 'exclude', 'filter out']):
                        condition['description'] = {"contains": keyword}
                        actions['boost_score'] = 0.5
                        return condition, actions
                    elif any(word in command for word in ['require', 'must', 'only']):
                        condition['description'] = {"contains": keyword}
                        actions['filter'] = True
                        return condition, actions
        
        return condition, actions

    def _parse_price_rule(self, command: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Parse price-related rules."""
        condition = {}
        actions = {}
        
        for pattern in self.price_patterns:
            match = re.search(pattern, command)
            if match:
                groups = match.groups()
                
                if len(groups) == 1:  # Single price
                    price = float(groups[0])
                    if 'under' in pattern or 'below' in pattern or 'less' in pattern:
                        condition['price'] = {"lte": price}
                        actions['boost_score'] = 1.1
                    elif 'over' in pattern or 'above' in pattern or 'more' in pattern:
                        condition['price'] = {"gte": price}
                        actions['boost_score'] = 1.1
                    elif 'minimum' in pattern or 'at least' in pattern:
                        condition['price'] = {"gte": price}
                        actions['filter'] = True
                    else:  # up to, maximum
                        condition['price'] = {"lte": price}
                        actions['filter'] = True
                
                elif len(groups) == 2:  # Price range
                    min_price = float(groups[0])
                    max_price = float(groups[1])
                    condition['price'] = {"gte": min_price, "lte": max_price}
                    actions['boost_score'] = 1.1
                
                return condition, actions
        
        return condition, actions

    def _parse_tech_rule(self, command: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Parse technical specification rules."""
        condition = {}
        actions = {}
        
        # Switch port rules
        port_match = re.search(r'(\d+)\s*port', command)
        if port_match:
            ports = int(port_match.group(1))
            if any(word in command for word in ['minimum', 'at least', 'require']):
                condition['switch_ports'] = {"gte": ports}
                actions['filter'] = True
            elif any(word in command for word in ['maximum', 'up to', 'below']):
                condition['switch_ports'] = {"lte": ports}
                actions['boost_score'] = 1.1
            else:
                condition['switch_ports'] = {"gte": ports}
                actions['boost_score'] = 1.1
        
        # NVR channel rules
        channel_match = re.search(r'(\d+)\s*channel', command)
        if channel_match:
            channels = int(channel_match.group(1))
            if any(word in command for word in ['minimum', 'at least', 'require']):
                condition['nvr_channels'] = {"gte": channels}
                actions['filter'] = True
            elif any(word in command for word in ['maximum', 'up to', 'below']):
                condition['nvr_channels'] = {"lte": channels}
                actions['boost_score'] = 1.1
            else:
                condition['nvr_channels'] = {"gte": channels}
                actions['boost_score'] = 1.1
        
        return condition, actions

    def _determine_priority(self, command: str, actions: Dict[str, Any]) -> int:
        """Determine rule priority based on action strength."""
        if actions.get('filter') == True:
            return 10  # High priority for filters
        elif actions.get('boost_score', 1.0) > 1.5:
            return 50  # Medium-high priority for strong boosts
        elif actions.get('boost_score', 1.0) < 0.8:
            return 80  # Lower priority for penalties
        else:
            return 100  # Default priority

    def get_suggestions(self, partial_command: str) -> List[str]:
        """Get suggestions for completing a natural language command."""
        suggestions = []
        
        if not partial_command.strip():
            return [
                "Prefer Axis cameras",
                "Avoid PTZ cameras",
                "Require outdoor cameras only",
                "Filter cameras under $500",
                "Boost 4K cameras",
                "Require switches with at least 24 ports",
                "Prefer Hanwha NVRs",
                "Avoid wireless cameras",
                "Require POE cameras only"
            ]
        
        command = partial_command.lower()
        
        # Brand suggestions
        if any(word in command for word in ['prefer', 'avoid', 'require']) and 'brand' not in command:
            suggestions.extend([
                "Prefer Axis cameras",
                "Avoid Hanwha products",
                "Require Hikvision only"
            ])
        
        # Type suggestions
        if any(word in command for word in ['camera', 'switch', 'nvr']):
            suggestions.extend([
                "Prefer dome cameras",
                "Avoid PTZ cameras",
                "Require POE switches only"
            ])
        
        # Price suggestions
        if any(word in command for word in ['price', 'cost', 'budget', '$']):
            suggestions.extend([
                "Filter cameras under $300",
                "Prefer products under $1000",
                "Require minimum $200 per camera"
            ])
        
        return suggestions[:5]  # Return top 5 suggestions

# Example usage and testing
if __name__ == "__main__":
    parser = RuleParser()
    
    test_commands = [
        "Prefer Axis cameras",
        "Avoid PTZ cameras", 
        "Require outdoor cameras only",
        "Filter cameras under $500",
        "Boost 4K cameras",
        "Require switches with at least 24 ports",
        "Prefer Hanwha NVRs",
        "Avoid wireless cameras"
    ]
    
    for cmd in test_commands:
        result = parser.parse_nlp_command(cmd)
        print(f"\nCommand: {cmd}")
        print(f"Name: {result.name}")
        print(f"Scope: {result.scope}")
        print(f"Priority: {result.priority}")
        print(f"Condition: {json.dumps(result.condition, indent=2)}")
        print(f"Actions: {json.dumps(result.actions, indent=2)}")
