"""
Graceful degradation manager for AI services.

Handles:
- Health checks for Ollama/LLM availability
- Fallback strategies when LLM is unavailable
- Queuing work for later processing
"""
import logging
import json
from typing import Optional, Literal
from datetime import datetime
from dataclasses import dataclass

from ..db import get_db
from ..config import Config

logger = logging.getLogger(__name__)


HealthLevel = Literal['full', 'degraded', 'minimal', 'offline']


@dataclass
class HealthStatus:
    """Current health status of AI services."""
    level: HealthLevel
    ollama_available: bool
    fast_model_loaded: bool
    slow_model_loaded: bool
    last_check: datetime
    message: str


class GracefulDegradation:
    """
    Manages AI service availability and fallbacks.
    
    Health levels:
    - full: All services available (Ollama running, models loaded)
    - degraded: Ollama running but slow model unavailable
    - minimal: Only rule-based scoring available
    - offline: No AI features available
    """
    
    def __init__(self):
        self._last_health: Optional[HealthStatus] = None
        self._ollama_host = Config.get('ollama_host', 'http://localhost:11434')
        self._fast_model = Config.get('fast_model', 'qwen2.5:1.5b-instruct-q4_K_M')
        self._slow_model = Config.get('slow_model', 'qwen2.5:7b-instruct-q4_K_M')
    
    def check_health(self) -> HealthStatus:
        """Check current health of AI services."""
        now = datetime.now()
        
        ollama_available = self._check_ollama()
        
        if not ollama_available:
            status = HealthStatus(
                level='minimal',
                ollama_available=False,
                fast_model_loaded=False,
                slow_model_loaded=False,
                last_check=now,
                message='Ollama not available - using rule-based scoring only'
            )
            self._last_health = status
            return status
        
        fast_loaded = self._check_model(self._fast_model)
        slow_loaded = self._check_model(self._slow_model)
        
        if fast_loaded and slow_loaded:
            level = 'full'
            message = 'All AI services available'
        elif fast_loaded or slow_loaded:
            level = 'degraded'
            message = f'Some models not loaded'
        else:
            level = 'minimal'
            message = 'No models loaded - using rule-based scoring only'
        
        status = HealthStatus(
            level=level,
            ollama_available=True,
            fast_model_loaded=fast_loaded,
            slow_model_loaded=slow_loaded,
            last_check=now,
            message=message
        )
        self._last_health = status
        return status
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is running."""
        try:
            import httpx
            response = httpx.get(f'{self._ollama_host}/api/tags', timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False
    
    def _check_model(self, model_name: str) -> bool:
        """Check if a model is available."""
        try:
            import httpx
            response = httpx.get(f'{self._ollama_host}/api/tags', timeout=2.0)
            if response.status_code != 200:
                return False
            data = response.json()
            models = data.get('models', [])
            for model in models:
                if model_name.split(':')[0] in model.get('name', ''):
                    return True
            return False
        except Exception:
            return False
    
    def get_last_health(self) -> Optional[HealthStatus]:
        return self._last_health
    
    def can_run_slow_path(self) -> bool:
        if self._last_health is None:
            self.check_health()
        return self._last_health and self._last_health.level in ('full', 'degraded') and self._last_health.slow_model_loaded
    
    def queue_for_later(self, task_type: str, task_id: int, task_data: dict) -> int:
        """Queue a slow-path task for later processing."""
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO pending_slow_work (task_type, task_id, task_data, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (task_type, task_id, json.dumps(task_data))
            )
            return cursor.lastrowid
    
    def get_pending_work(self, limit: int = 10) -> list[dict]:
        """Get pending slow-path work items."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM pending_slow_work 
                WHERE status = 'pending'
                ORDER BY queued_at ASC LIMIT ?
                """,
                (limit,)
            ).fetchall()
            
            return [
                {
                    'id': row['id'],
                    'task_type': row['task_type'],
                    'task_id': row['task_id'],
                    'task_data': json.loads(row['task_data']) if row['task_data'] else {},
                    'queued_at': row['queued_at'],
                }
                for row in rows
            ]
    
    def mark_work_completed(self, work_id: int, status: str = 'completed'):
        """Mark a queued work item as completed or failed."""
        with get_db() as conn:
            conn.execute(
                """
                UPDATE pending_slow_work 
                SET status = ?, processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, work_id)
            )
    
    def process_pending_when_healthy(self, processor_func) -> int:
        """Process pending work if system is healthy."""
        if not self.can_run_slow_path():
            return 0
        
        pending = self.get_pending_work()
        processed = 0
        
        for work in pending:
            try:
                success = processor_func(
                    work['task_type'],
                    work['task_id'],
                    work['task_data']
                )
                self.mark_work_completed(work['id'], 'completed' if success else 'failed')
                processed += 1
            except Exception as e:
                logger.error(f"Error processing work item {work['id']}: {e}")
                self.mark_work_completed(work['id'], 'failed')
        
        return processed
