"""
Clarification system for vague tasks.

Detects when tasks need more information and generates
appropriate questions to gather that information.
"""
import logging
import json
from typing import Optional
from datetime import datetime

from ..db import get_db
from ..config import Config
from ..models import Task, ClarificationRequest

logger = logging.getLogger(__name__)


# Templates for common clarification questions
CLARIFICATION_TEMPLATES = {
    'when': {
        'question': 'When do you need to complete "{task_name}"?',
        'options': ['Today', 'Tomorrow', 'This week', 'Next week', 'No deadline']
    },
    'scope': {
        'question': 'What does "{task_name}" involve?',
        'options': ['Quick task (< 15 min)', 'Medium task (15-60 min)', 'Large task (1+ hours)', 'Project (multiple sessions)']
    },
    'project': {
        'question': 'Which project does "{task_name}" belong to?',
        'options': []  # Will be filled with actual projects
    },
    'importance': {
        'question': 'How important is "{task_name}"?',
        'options': ['Critical - must do', 'Important - should do', 'Nice to have', 'Low priority']
    },
    'ambiguous': {
        'question': 'What specifically do you mean by "{task_name}"?',
        'options': []  # Open-ended
    }
}


class ClarificationGenerator:
    """Generates clarification requests for vague tasks."""
    
    def __init__(self):
        self._ollama_host = Config.get('ollama_host', 'http://localhost:11434')
        self._model = Config.get('fast_model', 'qwen2.5:1.5b-instruct-q4_K_M')
    
    def needs_clarification(self, task: Task) -> bool:
        """Check if a task needs clarification."""
        name = task.name.lower()
        words = name.split()
        
        # Very short tasks often need clarification
        if len(words) <= 2 and not self._is_clear_action(name):
            return True
        
        # Tasks with question words
        question_words = ['what', 'how', 'when', 'where', 'why', 'which', 'should']
        if any(w in words for w in question_words):
            return True
        
        # Tasks ending with "?"
        if task.name.strip().endswith('?'):
            return True
        
        # Vague verbs without objects
        vague_verbs = ['do', 'work', 'handle', 'deal', 'figure', 'think', 'look']
        if len(words) <= 3 and any(w in words for w in vague_verbs):
            return True
        
        return False
    
    def _is_clear_action(self, name: str) -> bool:
        """Check if task name is a clear action."""
        clear_verbs = ['call', 'email', 'text', 'buy', 'pay', 'send', 'pick', 'book', 'schedule']
        return any(v in name for v in clear_verbs)
    
    def generate(self, task_id: int) -> Optional[ClarificationRequest]:
        """Generate a clarification request for a task."""
        with get_db() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        
        if not row:
            return None
        
        task = Task.from_row(row)
        
        # Check if already has pending clarification
        with get_db() as conn:
            existing = conn.execute(
                "SELECT id FROM clarification_requests WHERE task_id = ? AND status = 'pending'",
                (task_id,)
            ).fetchone()
        
        if existing:
            return None
        
        # Determine what type of clarification is needed
        clarification_type = self._determine_clarification_type(task)
        
        # Generate the clarification request
        question, options = self._build_clarification(task, clarification_type)
        
        # Save to database
        return self._save_clarification(task_id, question, options)
    
    def _determine_clarification_type(self, task: Task) -> str:
        """Determine what type of clarification is needed."""
        # No due date - ask about timing
        if task.due_date is None:
            return 'when'
        
        # No project - ask about project assignment
        if task.project_id is None and len(task.name.split()) > 3:
            return 'project'
        
        # Very short - might be ambiguous
        if len(task.name.split()) <= 2:
            return 'ambiguous'
        
        # Default to scope clarification
        return 'scope'
    
    def _build_clarification(self, task: Task, ctype: str) -> tuple[str, list[str]]:
        """Build clarification question and options."""
        template = CLARIFICATION_TEMPLATES.get(ctype, CLARIFICATION_TEMPLATES['ambiguous'])
        
        question = template['question'].format(task_name=task.name)
        options = template['options'].copy()
        
        # For project clarification, get actual project list
        if ctype == 'project':
            options = self._get_project_options()
        
        return question, options
    
    def _get_project_options(self) -> list[str]:
        """Get list of active projects as options."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT name FROM projects WHERE status = 'in_progress' ORDER BY name LIMIT 10"
            ).fetchall()
        
        options = [row['name'] for row in rows]
        options.append('Create new project')
        options.append('No project (standalone)')
        return options
    
    def _save_clarification(self, task_id: int, question: str, options: list[str]) -> ClarificationRequest:
        """Save clarification request to database."""
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO clarification_requests (task_id, question, options, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (task_id, question, json.dumps(options))
            )
            clarification_id = cursor.lastrowid
        
        return ClarificationRequest(
            id=clarification_id,
            task_id=task_id,
            question=question,
            options=options,
            status='pending'
        )
    
    def get_pending_clarifications(self, limit: int = 10) -> list[ClarificationRequest]:
        """Get pending clarification requests."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM clarification_requests 
                WHERE status = 'pending'
                ORDER BY created_at ASC LIMIT ?
                """,
                (limit,)
            ).fetchall()
        
        return [ClarificationRequest.from_row(row) for row in rows]
    
    def respond_to_clarification(self, clarification_id: int, response: str) -> bool:
        """Record a response to a clarification request."""
        with get_db() as conn:
            # Get the clarification
            row = conn.execute(
                "SELECT * FROM clarification_requests WHERE id = ?",
                (clarification_id,)
            ).fetchone()
            
            if not row:
                return False
            
            # Update clarification status
            conn.execute(
                """
                UPDATE clarification_requests 
                SET status = 'answered', response = ?, responded_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (response, clarification_id)
            )
            
            # Apply the response to the task
            self._apply_response(row['task_id'], response)
        
        return True
    
    def _apply_response(self, task_id: int, response: str):
        """Apply clarification response to task."""
        # This would intelligently update the task based on the response
        # For now, we'll log it for user review
        logger.info(f"Clarification response for task {task_id}: {response}")
    
    def skip_clarification(self, clarification_id: int) -> bool:
        """Mark a clarification as skipped."""
        with get_db() as conn:
            conn.execute(
                "UPDATE clarification_requests SET status = 'skipped' WHERE id = ?",
                (clarification_id,)
            )
        return True
