"""
Adaptive notification timing.

Learns from user response patterns to optimize when to send
notifications for maximum engagement.
"""
import logging
from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict

from ..db import get_db
from ..config import Config

logger = logging.getLogger(__name__)


class AdaptiveTiming:
    """
    Learns optimal notification timing from user response patterns.
    
    Tracks:
    - Response delays per hour of day
    - Response delays per day of week
    - Which notification types get actioned
    
    After sufficient data (~7 responses), adjusts notification times.
    """
    
    MIN_RESPONSES_FOR_LEARNING = 7
    
    def __init__(self):
        self._default_morning = Config.get('morning_notification_time', '08:00')
        self._default_evening = Config.get('evening_notification_time', '20:00')
    
    def record_notification_sent(self, notification_type: str) -> int:
        """Record that a notification was sent. Returns notification ID."""
        now = datetime.now()
        
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO notification_responses 
                (sent_at, day_of_week, hour_of_day, notification_type, was_actioned)
                VALUES (?, ?, ?, ?, 0)
                """,
                (now, now.weekday(), now.hour, notification_type)
            )
            return cursor.lastrowid
    
    def record_response(self, notification_id: int, was_actioned: bool = True):
        """Record that user responded to a notification."""
        now = datetime.now()
        
        with get_db() as conn:
            # Get the notification
            row = conn.execute(
                "SELECT sent_at FROM notification_responses WHERE id = ?",
                (notification_id,)
            ).fetchone()
            
            if not row:
                return
            
            sent_at = datetime.fromisoformat(row['sent_at']) if isinstance(row['sent_at'], str) else row['sent_at']
            delay_minutes = (now - sent_at).total_seconds() / 60
            
            conn.execute(
                """
                UPDATE notification_responses 
                SET responded_at = ?, response_delay_minutes = ?, was_actioned = ?
                WHERE id = ?
                """,
                (now, delay_minutes, 1 if was_actioned else 0, notification_id)
            )
    
    def get_optimal_times(self) -> dict:
        """
        Get optimal notification times based on learned patterns.
        
        Returns dict with 'morning' and 'evening' times.
        """
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT hour_of_day, AVG(response_delay_minutes) as avg_delay, COUNT(*) as count
                FROM notification_responses
                WHERE responded_at IS NOT NULL
                GROUP BY hour_of_day
                HAVING count >= 2
                ORDER BY avg_delay ASC
                """
            ).fetchall()
        
        if len(rows) < self.MIN_RESPONSES_FOR_LEARNING:
            return {
                'morning': self._default_morning,
                'evening': self._default_evening,
                'learned': False
            }
        
        # Find best morning hour (6-12) and evening hour (17-22)
        morning_hours = [(r['hour_of_day'], r['avg_delay']) for r in rows if 6 <= r['hour_of_day'] <= 12]
        evening_hours = [(r['hour_of_day'], r['avg_delay']) for r in rows if 17 <= r['hour_of_day'] <= 22]
        
        best_morning = min(morning_hours, key=lambda x: x[1])[0] if morning_hours else 8
        best_evening = min(evening_hours, key=lambda x: x[1])[0] if evening_hours else 20
        
        return {
            'morning': f"{best_morning:02d}:00",
            'evening': f"{best_evening:02d}:00",
            'learned': True
        }
    
    def get_best_hours_by_day(self) -> dict:
        """Get best notification hours for each day of week."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT day_of_week, hour_of_day, AVG(response_delay_minutes) as avg_delay
                FROM notification_responses
                WHERE responded_at IS NOT NULL
                GROUP BY day_of_week, hour_of_day
                ORDER BY day_of_week, avg_delay ASC
                """
            ).fetchall()
        
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        result = {}
        
        for day_num, day_name in enumerate(day_names):
            day_rows = [r for r in rows if r['day_of_week'] == day_num]
            if day_rows:
                best_hour = day_rows[0]['hour_of_day']
                result[day_name] = f"{best_hour:02d}:00"
            else:
                result[day_name] = self._default_morning
        
        return result
    
    def should_notify_now(self) -> bool:
        """Check if now is a good time to notify based on patterns."""
        now = datetime.now()
        optimal = self.get_optimal_times()
        
        current_time = now.strftime('%H:%M')
        
        # Check if within 5 minutes of optimal time
        for key in ['morning', 'evening']:
            opt_time = optimal[key]
            opt_hour, opt_min = map(int, opt_time.split(':'))
            opt_dt = now.replace(hour=opt_hour, minute=opt_min, second=0)
            
            if abs((now - opt_dt).total_seconds()) <= 300:  # 5 minutes
                return True
        
        return False
    
    def get_response_stats(self) -> dict:
        """Get statistics about notification responses."""
        with get_db() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM notification_responses"
            ).fetchone()[0]
            
            responded = conn.execute(
                "SELECT COUNT(*) FROM notification_responses WHERE responded_at IS NOT NULL"
            ).fetchone()[0]
            
            actioned = conn.execute(
                "SELECT COUNT(*) FROM notification_responses WHERE was_actioned = 1"
            ).fetchone()[0]
            
            avg_delay = conn.execute(
                "SELECT AVG(response_delay_minutes) FROM notification_responses WHERE responded_at IS NOT NULL"
            ).fetchone()[0]
        
        return {
            'total_sent': total,
            'total_responded': responded,
            'total_actioned': actioned,
            'response_rate': responded / total if total > 0 else 0,
            'action_rate': actioned / responded if responded > 0 else 0,
            'avg_response_delay_minutes': round(avg_delay, 1) if avg_delay else None,
            'has_enough_data': total >= self.MIN_RESPONSES_FOR_LEARNING
        }
    
    def apply_learned_times(self):
        """Apply learned optimal times to config."""
        optimal = self.get_optimal_times()
        
        if optimal['learned']:
            Config.set('morning_notification_time', optimal['morning'])
            Config.set('evening_notification_time', optimal['evening'])
            logger.info(f"Applied learned notification times: morning={optimal['morning']}, evening={optimal['evening']}")
            return True
        
        return False
