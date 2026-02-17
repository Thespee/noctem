"""
Noctem AI Module v0.6.0

Background AI task runner for life management.
Provides:
- Task scoring (fast path)
- Implementation intentions (slow path)
- Clarification requests
- Adaptive notification timing
- Graceful degradation
"""

from .router import PathRouter
from .scorer import TaskScorer
from .degradation import GracefulDegradation
from .loop import AILoop

__all__ = [
    'PathRouter',
    'TaskScorer', 
    'GracefulDegradation',
    'AILoop',
]
