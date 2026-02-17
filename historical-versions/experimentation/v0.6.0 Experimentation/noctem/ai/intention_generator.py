"""
Implementation Intention Generator.

Uses Ollama/LLM to generate implementation intentions for tasks.
"""
import logging
import json
from typing import Optional
from datetime import datetime

from ..db import get_db
from ..config import Config
from ..models import Task, ImplementationIntention

logger = logging.getLogger(__name__)


INTENTION_PROMPT = """You are helping someone plan how to accomplish a task. Generate a practical implementation intention.

Task: {task_name}
{context}

Respond with a JSON object containing:
- when_trigger: A specific time/situation when they should start (e.g., "Tomorrow morning after coffee")
- where_location: A specific place to do this (e.g., "At my desk")
- how_approach: A brief approach strategy (1-2 sentences max)
- first_action: The very first tiny physical action to take (should be obvious and easy)

Be specific and practical. The first_action should be so simple it's almost impossible to procrastinate on.

JSON response:"""


class IntentionGenerator:
    """Generates implementation intentions using Ollama LLM."""
    
    def __init__(self):
        self._ollama_host = Config.get('ollama_host', 'http://localhost:11434')
        self._model = Config.get('slow_model', 'qwen2.5:7b-instruct-q4_K_M')
    
    def generate(self, task_id: int) -> Optional[ImplementationIntention]:
        """Generate an implementation intention for a task."""
        with get_db() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        
        if not row:
            return None
        
        task = Task.from_row(row)
        
        context_parts = []
        if task.due_date:
            context_parts.append(f"Due: {task.due_date}")
        if task.project_id:
            project_name = self._get_project_name(task.project_id)
            if project_name:
                context_parts.append(f"Project: {project_name}")
        
        context = "\n".join(context_parts) if context_parts else "No additional context"
        
        prompt = INTENTION_PROMPT.format(task_name=task.name, context=context)
        response = self._call_ollama(prompt)
        
        if not response:
            return None
        
        intention_data = self._parse_response(response)
        if not intention_data:
            return None
        
        return self._save_intention(task_id, intention_data)
    
    def _get_project_name(self, project_id: int) -> Optional[str]:
        with get_db() as conn:
            row = conn.execute("SELECT name FROM projects WHERE id = ?", (project_id,)).fetchone()
        return row['name'] if row else None
    
    def _call_ollama(self, prompt: str) -> Optional[str]:
        try:
            import httpx
            response = httpx.post(
                f'{self._ollama_host}/api/generate',
                json={
                    'model': self._model,
                    'prompt': prompt,
                    'stream': False,
                    'options': {'temperature': 0.7, 'num_predict': 500}
                },
                timeout=60.0
            )
            if response.status_code != 200:
                return None
            return response.json().get('response', '')
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return None
    
    def _parse_response(self, response: str) -> Optional[dict]:
        try:
            response = response.strip()
            start = response.find('{')
            end = response.rfind('}') + 1
            if start == -1 or end == 0:
                return None
            data = json.loads(response[start:end])
            required = ['when_trigger', 'where_location', 'how_approach', 'first_action']
            for field in required:
                if field not in data or not data[field]:
                    return None
            return data
        except json.JSONDecodeError:
            return None
    
    def _save_intention(self, task_id: int, data: dict) -> ImplementationIntention:
        with get_db() as conn:
            row = conn.execute(
                "SELECT MAX(version) as max_ver FROM implementation_intentions WHERE task_id = ?",
                (task_id,)
            ).fetchone()
            version = (row['max_ver'] or 0) + 1
            
            cursor = conn.execute(
                """
                INSERT INTO implementation_intentions 
                (task_id, version, when_trigger, where_location, how_approach, 
                 first_action, generated_by, confidence, status)
                VALUES (?, ?, ?, ?, ?, ?, 'llm', 0.7, 'draft')
                """,
                (task_id, version, data['when_trigger'], data['where_location'],
                 data['how_approach'], data['first_action'])
            )
            intention_id = cursor.lastrowid
            
            # Save first step
            conn.execute(
                """
                INSERT INTO next_steps (task_id, intention_id, step_text, step_order, status)
                VALUES (?, ?, ?, 1, 'current')
                """,
                (task_id, intention_id, data['first_action'])
            )
        
        return ImplementationIntention(
            id=intention_id, task_id=task_id, version=version,
            when_trigger=data['when_trigger'], where_location=data['where_location'],
            how_approach=data['how_approach'], first_action=data['first_action'],
            generated_by='llm', confidence=0.7, status='draft'
        )
    
    def get_intention(self, task_id: int) -> Optional[ImplementationIntention]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM implementation_intentions WHERE task_id = ? ORDER BY version DESC LIMIT 1",
                (task_id,)
            ).fetchone()
        return ImplementationIntention.from_row(row) if row else None
    
    def approve_intention(self, intention_id: int) -> bool:
        with get_db() as conn:
            conn.execute(
                "UPDATE implementation_intentions SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (intention_id,)
            )
        return True
