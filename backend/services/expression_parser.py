"""
Expression Parser Service
Parses sentiment from AI responses and maps to Live2D parameters.
"""
import re
from config import EXPRESSION_PARAMS


class ExpressionParser:
    def __init__(self):
        self.expression_params = EXPRESSION_PARAMS
        self.current_expression = "neutral"

    def parse_expression(self, text: str) -> dict:
        """
        Extract expression tag from text and return Live2D parameters.
        Returns dict with expression name and parameter values.
        """
        expression = "neutral"

        # Check for explicit expression tag
        match = re.search(r'\[EXPRESSION:(\w+)\]', text)
        if match:
            expr_name = match.group(1).lower()
            if expr_name in self.expression_params:
                expression = expr_name

        self.current_expression = expression

        return {
            "expression": expression,
            "params": self.expression_params.get(
                expression,
                self.expression_params["neutral"]
            ),
            "transition_duration": 0.5,  # seconds for smooth transition
        }

    def get_clean_text(self, text: str) -> str:
        """Remove expression tags from text."""
        return re.sub(r'\s*\[EXPRESSION:\w+\]\s*', '', text).strip()

    def get_current_params(self) -> dict:
        """Get current expression parameters."""
        return self.expression_params.get(
            self.current_expression,
            self.expression_params["neutral"]
        )
