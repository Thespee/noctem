"""
Tests for Noctem v0.6.0 AI components.
"""
import pytest
import sys
import os
from datetime import date, datetime

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from noctem.models import Task
from noctem.ai.scorer import TaskScorer, ScoreResult
from noctem.ai.router import PathRouter, RouteDecision
from noctem.ai.degradation import GracefulDegradation, HealthStatus


class TestTaskScorer:
    """Tests for the task AI-helpfulness scorer."""
    
    def setup_method(self):
        self.scorer = TaskScorer()
    
    def test_short_vague_task_scores_high(self):
        """Very short, vague tasks should score high."""
        task = Task(name="project stuff")
        result = self.scorer.score(task)
        assert result.score >= 0.3
        assert "Very short" in str(result.reasons) or "vague" in str(result.reasons).lower()
    
    def test_clear_action_scores_low(self):
        """Clear action tasks should score low."""
        task = Task(name="call mom", due_date=date.today())
        result = self.scorer.score(task)
        assert result.score < 0.3
    
    def test_complex_keyword_increases_score(self):
        """Tasks with complex keywords should score higher."""
        task = Task(name="research best practices for database design")
        result = self.scorer.score(task)
        assert result.score >= 0.3
        assert any("complex" in r.lower() or "research" in r.lower() for r in result.reasons)
    
    def test_question_increases_score(self):
        """Tasks with questions should score higher."""
        task = Task(name="figure out how to fix the bug?")
        result = self.scorer.score(task)
        assert result.score >= 0.2
    
    def test_no_due_date_increases_score(self):
        """Tasks without due dates may need planning."""
        task1 = Task(name="write documentation", due_date=None)
        task2 = Task(name="write documentation", due_date=date.today())
        
        result1 = self.scorer.score(task1)
        result2 = self.scorer.score(task2)
        
        # No due date should score higher
        assert result1.score >= result2.score
    
    def test_score_is_bounded(self):
        """Score should always be between 0 and 1."""
        tasks = [
            Task(name="x"),
            Task(name="research and write a comprehensive analysis of machine learning algorithms"),
            Task(name="buy milk"),
            Task(name="?????"),
        ]
        for task in tasks:
            result = self.scorer.score(task)
            assert 0.0 <= result.score <= 1.0
    
    def test_should_generate_intention(self):
        """Test the quick check for intention generation."""
        high_score_task = Task(name="plan the project roadmap")
        low_score_task = Task(name="send email to john")
        
        assert self.scorer.should_generate_intention(high_score_task, threshold=0.3)
        assert not self.scorer.should_generate_intention(low_score_task, threshold=0.5)


class TestPathRouter:
    """Tests for the fast/slow path router."""
    
    def setup_method(self):
        self.router = PathRouter()
    
    def test_fast_tasks_route_to_fast(self):
        """Explicit fast tasks should route to fast path."""
        for task_type in ['register_task', 'status_query', 'score_task']:
            decision = self.router.route(task_type)
            assert decision.path == 'fast'
    
    def test_slow_tasks_route_to_slow(self):
        """Explicit slow tasks should route to slow path."""
        for task_type in ['implementation_intention', 'task_decomposition']:
            decision = self.router.route(task_type)
            assert decision.path == 'slow'
    
    def test_unknown_defaults_to_fast(self):
        """Unknown task types should default to fast (safe)."""
        decision = self.router.route('unknown_operation_type')
        assert decision.path == 'fast'
    
    def test_context_affects_routing(self):
        """Context should affect routing decisions."""
        decision = self.router.route('unknown', context={'requires_generation': True})
        assert decision.path == 'slow'
    
    def test_queue_priority_calculation(self):
        """Test queue priority calculation."""
        # User-initiated should be highest
        priority1 = self.router.get_slow_queue_priority('test', {'user_initiated': True})
        priority2 = self.router.get_slow_queue_priority('test', {'user_initiated': False})
        assert priority1 > priority2
        
        # Due today should add priority
        priority3 = self.router.get_slow_queue_priority('test', {'due_today': True})
        priority4 = self.router.get_slow_queue_priority('test', {})
        assert priority3 > priority4


class TestGracefulDegradation:
    """Tests for the graceful degradation manager."""
    
    def setup_method(self):
        self.degradation = GracefulDegradation()
    
    def test_health_check_returns_status(self):
        """Health check should return a HealthStatus object."""
        status = self.degradation.check_health()
        assert isinstance(status, HealthStatus)
        assert status.level in ('full', 'degraded', 'minimal', 'offline')
        assert isinstance(status.last_check, datetime)
    
    def test_offline_when_ollama_unavailable(self):
        """When Ollama is not running, status should be minimal."""
        # This test assumes Ollama is not running in test environment
        status = self.degradation.check_health()
        if not status.ollama_available:
            assert status.level in ('minimal', 'offline')
    
    def test_get_last_health_caches(self):
        """get_last_health should return cached status."""
        # First check
        status1 = self.degradation.check_health()
        # Get cached
        status2 = self.degradation.get_last_health()
        
        assert status1.last_check == status2.last_check


class TestIntegration:
    """Integration tests for the AI system."""
    
    def test_scorer_with_real_task_scenarios(self):
        """Test scorer with realistic task scenarios."""
        scorer = TaskScorer()
        
        # Scenario 1: Vague project task
        task1 = Task(
            name="work on thesis",
            importance=1.0,
            due_date=None
        )
        result1 = scorer.score(task1)
        assert result1.score >= 0.5  # Should need AI help
        
        # Scenario 2: Clear simple task
        task2 = Task(
            name="buy groceries at store",
            importance=0.3,
            due_date=date.today()
        )
        result2 = scorer.score(task2)
        assert result2.score < 0.4  # Should be clear enough
        
        # Scenario 3: Research task
        task3 = Task(
            name="research best Python web frameworks for new project",
            importance=0.7,
            project_id=1
        )
        result3 = scorer.score(task3)
        assert result3.score >= 0.3  # Research tasks need breakdown


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
