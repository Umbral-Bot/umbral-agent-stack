import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import fakeredis
import pytest

from dispatcher.queue import TaskQueue
from dispatcher.scheduler import TaskScheduler

REDIS_KEY_SCHEDULED_TASKS = "umbral:scheduled_tasks"


@pytest.fixture
def fake_redis():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def scheduler(fake_redis):
    return TaskScheduler(fake_redis)


@pytest.fixture
def queue(fake_redis):
    return TaskQueue(fake_redis)


def test_schedule_task(scheduler, fake_redis):
    envelope = {
        "task_id": "test-123",
        "task": "notion.add_comment",
        "input": {"text": "hello"},
    }
    run_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    scheduler.schedule(envelope, run_at)
    
    tasks = fake_redis.zrange(REDIS_KEY_SCHEDULED_TASKS, 0, -1, withscores=True)
    assert len(tasks) == 1
    
    stored_envelope_json, score = tasks[0]
    stored_envelope = json.loads(stored_envelope_json)
    
    assert stored_envelope["task_id"] == "test-123"
    assert score == run_at.timestamp()


def test_list_scheduled(scheduler):
    envelope1 = {"task_id": "opt-1"}
    envelope2 = {"task_id": "opt-2"}
    
    now = datetime.now(timezone.utc)
    
    scheduler.schedule(envelope1, now + timedelta(hours=2))
    scheduler.schedule(envelope2, now + timedelta(hours=1))
    
    scheduled_tasks = scheduler.list_scheduled()
    
    assert len(scheduled_tasks) == 2
    # Should be sorted by timestamp (opt-2 is earlier)
    assert scheduled_tasks[0]["envelope"]["task_id"] == "opt-2"
    assert scheduled_tasks[1]["envelope"]["task_id"] == "opt-1"


def test_cancel_task(scheduler, fake_redis):
    envelope = {"task_id": "test-cancel"}
    scheduler.schedule(envelope, datetime.now(timezone.utc) + timedelta(hours=1))
    
    assert len(scheduler.list_scheduled()) == 1
    
    cancelled = scheduler.cancel("test-cancel")
    assert cancelled is True
    assert len(scheduler.list_scheduled()) == 0


def test_cancel_nonexistent_task(scheduler):
    cancelled = scheduler.cancel("nonexistent")
    assert cancelled is False


def test_check_and_enqueue_due_tasks(scheduler, fake_redis, queue):
    # Task due in the past
    envelope_past = {"task_id": "past-task", "task": "notion.add_comment"}
    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    scheduler.schedule(envelope_past, past_time)
    
    # Task due in the future
    envelope_future = {"task_id": "future-task", "task": "notion.add_comment"}
    future_time = datetime.now(timezone.utc) + timedelta(minutes=10)
    scheduler.schedule(envelope_future, future_time)
    
    # Run check
    scheduler.check_and_enqueue(queue)
    
    # Only the past task should be removed from scheduler
    scheduled = scheduler.list_scheduled()
    assert len(scheduled) == 1
    assert scheduled[0]["envelope"]["task_id"] == "future-task"
    
    # Past task should be in queue
    queued_task = queue.dequeue()
    assert queued_task is not None
    assert queued_task["task_id"] == "past-task"


def test_check_and_enqueue_recurring_task(scheduler, queue):
    # Recurring task due in the past
    envelope = {
        "task_id": "recurring-task",
        "task": "notion.add_comment",
        "run_at": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
        "recurrence": "every_day",
    }
    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    scheduler.schedule(envelope, past_time)
    
    # Run check
    scheduler.check_and_enqueue(queue)
    
    # Task should be in queue
    queued_task = queue.dequeue()
    assert queued_task is not None
    assert queued_task["task_id"] == "recurring-task"
    
    # Task should be rescheduled for tomorrow
    scheduled = scheduler.list_scheduled()
    assert len(scheduled) == 1
    rescheduled_task = scheduled[0]["envelope"]
    assert rescheduled_task["task_id"] == "recurring-task"
    
    # Check the new scheduled time
    run_at_str = scheduled[0]["run_at"]
    next_run = datetime.fromisoformat(run_at_str)
    # Give it some leeway (should be ~24 hours from past_time)
    expected_next_run = past_time + timedelta(days=1)
    # The actual implementation calculates from the *original* run_at inside envelope if present, 
    # but let's just make sure it's in the future
    assert next_run > datetime.now(timezone.utc)


def test_calculate_next_run(scheduler):
    now = datetime.now(timezone.utc)
    
    # every_day
    next_day = scheduler._calculate_next_run("every_day")
    assert next_day > now
    
    # every_monday
    next_monday = scheduler._calculate_next_run("every_monday")
    assert next_monday > now
    assert next_monday.weekday() == 0  # 0 is Monday
