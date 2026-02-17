"""
Fast/slow path decision logic for AI operations.

Fast path: instant, no LLM (scoring, simple queries)
Slow path: requires LLM (implementation intentions, complex clarification)
"""
from typing import Optional
from dataclasses import dataclass


@dataclass
class RouteDecision:
    """Result of routing decision."""
    path: str  # 'fast' or 'slow'
    reason: str
    priority: int = 0  # Higher = more urgent


class PathRouter:
    """Decides whether AI operations go through fast or slow path."""
    
    # Operations that can complete instantly
    FAST_TASKS = [
        'register_task',      # Just record in DB
        'status_query',       # Read from DB
        'score_task',         # scikit-learn or rules
        'simple_clarification',  # Template-based questions
    ]
    
    # Operations requiring LLM
    SLOW_TASKS = [
        'implementation_intention',  # Generate full breakdown
        'external_prompt',           # User-triggered AI query
        'complex_clarification',     # Context-aware questions
        'task_decomposition',        # Break into subtasks
    ]
    
    def route(self, request_type: str, context: Optional[dict] = None) -> RouteDecision:
        """
        Determine which path a request should take.
        
        Args:
            request_type: Type of AI operation
            context: Additional context (task details, urgency, etc.)
            
        Returns:
            RouteDecision with path and reasoning
        """
        context = context or {}
        
        # Explicit fast tasks
        if request_type in self.FAST_TASKS:
            return RouteDecision(
                path='fast',
                reason=f'{request_type} is a fast-path operation',
                priority=context.get('priority', 0)
            )
        
        # Explicit slow tasks
        if request_type in self.SLOW_TASKS:
            return RouteDecision(
                path='slow',
                reason=f'{request_type} requires LLM processing',
                priority=context.get('priority', 0)
            )
        
        # Heuristics for unknown types
        if context.get('requires_generation'):
            return RouteDecision(
                path='slow',
                reason='Operation requires text generation',
                priority=context.get('priority', 0)
            )
        
        if context.get('word_count', 0) > 50:
            return RouteDecision(
                path='slow', 
                reason='Complex input suggests LLM needed',
                priority=context.get('priority', 0)
            )
        
        # Default to fast (safe)
        return RouteDecision(
            path='fast',
            reason='Default to fast path for unknown operation',
            priority=0
        )
    
    def can_fast_path(self, request_type: str) -> bool:
        """Quick check if request can be handled via fast path."""
        return request_type in self.FAST_TASKS
    
    def get_slow_queue_priority(self, request_type: str, context: Optional[dict] = None) -> int:
        """
        Determine queue priority for slow-path operations.
        Higher number = process sooner.
        """
        context = context or {}
        base_priority = 0
        
        # User-initiated requests get highest priority
        if context.get('user_initiated'):
            base_priority += 100
        
        # High AI-help-score tasks get priority
        ai_score = context.get('ai_help_score', 0)
        if ai_score:
            base_priority += int(ai_score * 50)
        
        # Urgent tasks (due soon)
        if context.get('due_today'):
            base_priority += 30
        elif context.get('due_this_week'):
            base_priority += 10
        
        return base_priority
