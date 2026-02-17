"""
Main AI background loop.

Runs as a daemon thread, continuously:
- Scoring new tasks
- Processing pending slow work when healthy
- Sending scheduled notifications
"""
import logging
import time
import threading
from datetime import datetime
from typing import Optional

from ..db import get_db
from ..config import Config
from .scorer import TaskScorer
from .degradation import GracefulDegradation

logger = logging.getLogger(__name__)


class AILoop:
    """Background AI processing loop."""
    
    def __init__(self, poll_interval: int = 30, score_batch_size: int = 10):
        self.poll_interval = poll_interval
        self.score_batch_size = score_batch_size
        self.scorer = TaskScorer()
        self.degradation = GracefulDegradation()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_health_check = None
        self._health_check_interval = 60
    
    def start(self, daemon: bool = True):
        """Start the AI loop in a background thread."""
        if self._running:
            logger.warning("AI loop already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=daemon)
        self._thread.start()
        logger.info("AI loop started")
    
    def stop(self):
        """Stop the AI loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("AI loop stopped")
    
    def _run_loop(self):
        """Main loop execution."""
        while self._running:
            try:
                self._tick()
            except Exception as e:
                logger.error(f"Error in AI loop tick: {e}", exc_info=True)
            
            for _ in range(self.poll_interval):
                if not self._running:
                    break
                time.sleep(1)
    
    def _tick(self):
        """Single tick of the AI loop."""
        now = datetime.now()
        
        if (self._last_health_check is None or 
            (now - self._last_health_check).seconds >= self._health_check_interval):
            health = self.degradation.check_health()
            self._last_health_check = now
            logger.debug(f"Health check: {health.level} - {health.message}")
        
        scored_count = self._score_unprocessed_tasks()
        if scored_count > 0:
            logger.info(f"Scored {scored_count} tasks")
        
        if self.degradation.can_run_slow_path():
            processed = self.degradation.process_pending_when_healthy(
                self._process_slow_work_item
            )
            if processed > 0:
                logger.info(f"Processed {processed} pending work items")
    
    def _score_unprocessed_tasks(self) -> int:
        """Score tasks that haven't been processed yet."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM tasks 
                WHERE ai_help_score IS NULL 
                AND status NOT IN ('done', 'canceled')
                LIMIT ?
                """,
                (self.score_batch_size,)
            ).fetchall()
        
        if not rows:
            return 0
        
        from ..models import Task
        
        scored = 0
        for row in rows:
            task = Task.from_row(row)
            result = self.scorer.score(task)
            
            with get_db() as conn:
                conn.execute(
                    """
                    UPDATE tasks 
                    SET ai_help_score = ?, ai_processed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (result.score, task.id)
                )
            
            if result.score >= Config.get('ai_confidence_threshold', 0.5):
                self._maybe_queue_intention(task.id, result.score)
            
            scored += 1
        
        return scored
    
    def _maybe_queue_intention(self, task_id: int, score: float):
        """Queue task for implementation intention if not already queued."""
        with get_db() as conn:
            existing = conn.execute(
                """
                SELECT id FROM implementation_intentions WHERE task_id = ?
                UNION
                SELECT id FROM pending_slow_work 
                WHERE task_id = ? AND task_type = 'implementation_intention' 
                AND status = 'pending'
                """,
                (task_id, task_id)
            ).fetchone()
            
            if not existing:
                self.degradation.queue_for_later(
                    'implementation_intention',
                    task_id,
                    {'ai_help_score': score}
                )
    
    def _process_slow_work_item(self, task_type: str, task_id: int, task_data: dict) -> bool:
        """Process a single slow-path work item."""
        if task_type == 'implementation_intention':
            return self._generate_intention(task_id, task_data)
        elif task_type == 'clarification':
            return self._generate_clarification(task_id, task_data)
        else:
            logger.warning(f"Unknown work type: {task_type}")
            return False
    
    def _generate_intention(self, task_id: int, task_data: dict) -> bool:
        """Generate implementation intention for a task."""
        try:
            from .intention_generator import IntentionGenerator
            generator = IntentionGenerator()
            intention = generator.generate(task_id)
            return intention is not None
        except Exception as e:
            logger.error(f"Error generating intention for task {task_id}: {e}")
            return False
    
    def _generate_clarification(self, task_id: int, task_data: dict) -> bool:
        """Generate clarification request for a task."""
        try:
            from .clarification import ClarificationGenerator
            generator = ClarificationGenerator()
            request = generator.generate(task_id)
            return request is not None
        except Exception as e:
            logger.error(f"Error generating clarification for task {task_id}: {e}")
            return False
    
    def score_task(self, task_id: int) -> Optional[float]:
        """Manually score a specific task."""
        with get_db() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        
        if not row:
            return None
        
        from ..models import Task
        task = Task.from_row(row)
        result = self.scorer.score(task)
        
        with get_db() as conn:
            conn.execute(
                """
                UPDATE tasks 
                SET ai_help_score = ?, ai_processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (result.score, task_id)
            )
        
        return result.score
    
    def get_status(self) -> dict:
        """Get current status of the AI loop."""
        health = self.degradation.get_last_health()
        
        with get_db() as conn:
            unscored = conn.execute(
                """
                SELECT COUNT(*) FROM tasks 
                WHERE ai_help_score IS NULL 
                AND status NOT IN ('done', 'canceled')
                """
            ).fetchone()[0]
            
            pending_work = conn.execute(
                "SELECT COUNT(*) FROM pending_slow_work WHERE status = 'pending'"
            ).fetchone()[0]
        
        return {
            'running': self._running,
            'health_level': health.level if health else 'unknown',
            'health_message': health.message if health else 'Not checked yet',
            'unscored_tasks': unscored,
            'pending_slow_work': pending_work,
            'poll_interval': self.poll_interval,
        }
