"""
Task AI-helpfulness scoring.

Determines which tasks would benefit most from AI assistance
(implementation intentions, breakdown, clarification).

Uses rule-based scoring with optional scikit-learn enhancement.
"""
import re
from typing import Optional
from dataclasses import dataclass
from datetime import date

from ..models import Task


@dataclass
class ScoreResult:
    """Result of scoring a task."""
    score: float  # 0-1, higher = more likely to benefit from AI help
    confidence: float  # How confident we are in this score
    reasons: list[str]  # Why this score was given
    method: str  # 'rules' or 'ml'


class TaskScorer:
    """
    Score tasks for AI helpfulness.
    
    High scores indicate tasks that would benefit from:
    - Implementation intention generation
    - Breaking down into subtasks
    - Clarification questions
    """
    
    # Keywords suggesting task needs breakdown
    COMPLEX_KEYWORDS = [
        'plan', 'research', 'write', 'design', 'create', 'build',
        'develop', 'organize', 'prepare', 'review', 'analyze',
        'investigate', 'figure out', 'work on', 'start', 'finish',
        'complete', 'project', 'implement', 'setup', 'configure',
    ]
    
    # Keywords suggesting task is already clear
    SIMPLE_KEYWORDS = [
        'buy', 'call', 'email', 'text', 'send', 'pick up',
        'drop off', 'return', 'pay', 'schedule', 'book',
        'remind', 'check', 'confirm', 'reply', 'respond',
    ]
    
    # Question words suggesting vagueness
    QUESTION_INDICATORS = [
        '?', 'how', 'what', 'when', 'where', 'why', 'which',
        'should', 'could', 'would', 'maybe', 'might', 'perhaps',
    ]
    
    def __init__(self):
        self._ml_model = None
        self._try_load_ml_model()
    
    def _try_load_ml_model(self):
        """Attempt to load scikit-learn model for enhanced scoring."""
        try:
            from sklearn.naive_bayes import MultinomialNB
            from sklearn.feature_extraction.text import CountVectorizer
            # Model would be trained on user feedback over time
            # For now, we use rule-based scoring
            self._ml_model = None
        except ImportError:
            self._ml_model = None
    
    def score(self, task: Task) -> ScoreResult:
        """
        Score a task for AI helpfulness.
        
        Returns score between 0 (no AI help needed) and 1 (definitely needs AI help).
        """
        reasons = []
        score = 0.0
        
        name_lower = task.name.lower()
        words = name_lower.split()
        word_count = len(words)
        
        # Factor 1: Task length/complexity
        if word_count <= 2:
            # Very short - might be vague OR very clear
            if any(kw in name_lower for kw in self.SIMPLE_KEYWORDS):
                score += 0.0
                reasons.append("Short, clear action")
            else:
                score += 0.3
                reasons.append("Very short - possibly vague")
        elif word_count <= 5:
            score += 0.1
            reasons.append("Moderate length")
        else:
            score += 0.2
            reasons.append("Longer task - may need breakdown")
        
        # Factor 2: Complex keywords
        complex_matches = [kw for kw in self.COMPLEX_KEYWORDS if kw in name_lower]
        if complex_matches:
            score += min(0.3, len(complex_matches) * 0.1)
            reasons.append(f"Complex keywords: {', '.join(complex_matches[:3])}")
        
        # Factor 3: Simple keywords (reduce score)
        simple_matches = [kw for kw in self.SIMPLE_KEYWORDS if kw in name_lower]
        if simple_matches:
            score -= min(0.2, len(simple_matches) * 0.1)
            reasons.append(f"Clear action keywords: {', '.join(simple_matches[:2])}")
        
        # Factor 4: Question indicators / vagueness
        question_matches = [q for q in self.QUESTION_INDICATORS if q in name_lower]
        if question_matches:
            score += 0.2
            reasons.append("Contains uncertainty/question")
        
        # Factor 5: No due date (might need planning)
        if task.due_date is None:
            score += 0.1
            reasons.append("No due date - may need timeline")
        
        # Factor 6: High importance but unclear
        if task.importance >= 0.7 and word_count <= 3:
            score += 0.15
            reasons.append("Important but brief - needs clarity")
        
        # Factor 7: No project assignment
        if task.project_id is None and word_count > 3:
            score += 0.05
            reasons.append("Unassigned to project")
        
        # Clamp to 0-1
        score = max(0.0, min(1.0, score))
        
        # Confidence based on how many factors we matched
        confidence = min(1.0, len(reasons) * 0.15)
        
        return ScoreResult(
            score=round(score, 3),
            confidence=round(confidence, 3),
            reasons=reasons,
            method='rules'
        )
    
    def score_batch(self, tasks: list[Task]) -> list[tuple[Task, ScoreResult]]:
        """Score multiple tasks efficiently."""
        return [(task, self.score(task)) for task in tasks]
    
    def should_generate_intention(self, task: Task, threshold: float = 0.5) -> bool:
        """Quick check if task should get an implementation intention."""
        result = self.score(task)
        return result.score >= threshold
    
    def should_clarify(self, task: Task, threshold: float = 0.6) -> bool:
        """Quick check if task needs clarification."""
        result = self.score(task)
        # Clarification needed if high score but short name
        return result.score >= threshold and len(task.name.split()) <= 4
    
    def get_features(self, task: Task) -> dict:
        """
        Extract features for ML model training.
        
        Returns dict of features that could be used to train
        a classifier on user feedback.
        """
        name_lower = task.name.lower()
        words = name_lower.split()
        
        return {
            'word_count': len(words),
            'char_count': len(task.name),
            'has_due_date': task.due_date is not None,
            'has_due_time': task.due_time is not None,
            'has_project': task.project_id is not None,
            'importance': task.importance,
            'has_question_mark': '?' in task.name,
            'has_complex_keyword': any(kw in name_lower for kw in self.COMPLEX_KEYWORDS),
            'has_simple_keyword': any(kw in name_lower for kw in self.SIMPLE_KEYWORDS),
            'tag_count': len(task.tags) if task.tags else 0,
            'is_recurring': task.recurrence_rule is not None,
        }
