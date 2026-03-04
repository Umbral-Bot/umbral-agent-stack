"""
Scheduled Tasks Manager for Umbral Dispatcher.

Handles delayed and recurring tasks using Redis Sorted Sets.
"""

import json
import logging
import time
from datetime import datetime, timezone

from redis import Redis

from dispatcher.queue import TaskQueue

logger = logging.getLogger("dispatcher.scheduler")

class TaskScheduler:
    """Manages scheduled tasks stored in Redis sorted sets."""

    SCHEDULE_KEY = "umbral:scheduled_tasks"

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def schedule(self, envelope: dict, run_at_utc: datetime):
        """
        Stores a task to be executed at the specified time.
        
        Args:
            envelope: The task payload.
            run_at_utc: A timezone-aware datetime indicating when to run.
        """
        timestamp = run_at_utc.timestamp()
        task_id = envelope.get("task_id")
        
        # We need a unique member in the sorted set.
        # We'll store the entire envelope as JSON.
        payload = json.dumps(envelope)
        
        # Redis ZADD syntax: {member: score}
        self.redis.zadd(self.SCHEDULE_KEY, {payload: timestamp})
        logger.info(f"Scheduled task {task_id} to run at {run_at_utc.isoformat()} (score: {timestamp})")

    def check_and_enqueue(self, queue: TaskQueue):
        """
        Checks for tasks whose scheduled time has passed and enqueues them.
        Reschedules recurring tasks.
        """
        now = time.time()
        
        # Get tasks with score <= now
        # zrangebyscore(name, min, max)
        tasks = self.redis.zrangebyscore(self.SCHEDULE_KEY, 0, now)
        
        count = 0
        for task_payload in tasks:
            # Try to remove it to lock it for this worker
            if self.redis.zrem(self.SCHEDULE_KEY, task_payload) == 1:
                try:
                    envelope = json.loads(task_payload)
                    task_id = envelope.get("task_id", "unknown")
                    
                    # Enqueue the task
                    queue.enqueue(envelope)
                    logger.info(f"Enqueued scheduled task {task_id}")
                    count += 1
                    
                    # Handle recurrence
                    recurrence = envelope.get("recurrence")
                    if recurrence:
                        next_run_dt = self._calculate_next_run(recurrence)
                        if next_run_dt:
                            # Schedule it again
                            self.schedule(envelope, next_run_dt)
                            logger.info(f"Rescheduled recurring task {task_id} for {next_run_dt.isoformat()}")
                            
                except Exception as e:
                    logger.error(f"Failed to process scheduled task payload: {e}")
                    
        return count

    def _calculate_next_run(self, recurrence: str) -> datetime | None:
        """
        Calculates the next run datetime based on a recurrence string.
        Currently supports simple cases like 'every_monday'.
        """
        now = datetime.now(timezone.utc)
        
        if recurrence == "every_monday":
            # 0=Monday, 6=Sunday
            days_ahead = 0 - now.weekday()
            if days_ahead <= 0: # Target day already happened this week
                days_ahead += 7
            next_date = now.replace(hour=9, minute=0, second=0, microsecond=0)
            from datetime import timedelta
            return next_date + timedelta(days=days_ahead)
            
        elif recurrence == "every_day":
            from datetime import timedelta
            next_date = now.replace(hour=9, minute=0, second=0, microsecond=0)
            return next_date + timedelta(days=1)
            
        return None

    def list_scheduled(self) -> list[dict]:
        """
        Lists all scheduled tasks.
        
        Returns:
            A list of dicts with 'envelope' and 'run_at' (ISO 8601).
        """
        # zrange(name, start, end, withscores=True)
        # 0 to -1 gets all elements
        tasks_with_scores = self.redis.zrange(self.SCHEDULE_KEY, 0, -1, withscores=True)
        
        result = []
        for payload, score in tasks_with_scores:
            try:
                envelope = json.loads(payload)
                # Convert score back to ISO datetime
                run_at_dt = datetime.fromtimestamp(score, tz=timezone.utc)
                result.append({
                    "run_at": run_at_dt.isoformat(),
                    "envelope": envelope
                })
            except Exception:
                pass
                
        return result

    def cancel(self, task_id: str) -> bool:
        """
        Cancels a scheduled task by iterating through payloads.
        In a large set this might be slow, but typically there aren't many.
        
        Returns:
            True if cancelled, False if not found.
        """
        tasks = self.redis.zrange(self.SCHEDULE_KEY, 0, -1)
        for payload in tasks:
            try:
                envelope = json.loads(payload)
                if envelope.get("task_id") == task_id:
                    self.redis.zrem(self.SCHEDULE_KEY, payload)
                    logger.info(f"Cancelled scheduled task {task_id}")
                    return True
            except Exception:
                pass
                
        return False
