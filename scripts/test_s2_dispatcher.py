#!/usr/bin/env python3
"""
S2 Orchestration Split Validation

Run this on the VPS. It pushes a task through the Dispatcher's Redis queue
and waits for it to be completed by the execution plane (Worker).

Req: REDIS_URL and WORKER_URL.
"""
import os
import sys
import time
import uuid
import json

import redis
from rich.console import Console

# Add repo root to PATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dispatcher.queue import TaskQueue

console = Console()

def main():
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    
    console.print(f"Connecting to Redis at {redis_url}...")
    try:
        r = redis.from_url(redis_url, decode_responses=True)
        r.ping()
    except Exception as e:
        console.print(f"[bold red]Failed to connect to Redis: {e}[/bold red]")
        sys.exit(1)
        
    queue = TaskQueue(r)
    
    task_id = str(uuid.uuid4())
    envelope = {
        "schema_version": "0.1",
        "task_id": task_id,
        "team": "system",  # system/marketing/advisory → VPS Worker; improvement/lab → VM
        "task_type": "testing",
        "task": "ping",
        "input": {"message": "hello from dispatcher test via redis", "ts": time.time()}
    }
    
    console.print(f"\n[cyan]1. Enqueuing task {task_id}...[/cyan]")
    queue.enqueue(envelope)
    
    console.print("\n[cyan]2. Waiting for task completion...[/cyan]")
    max_wait = 15
    for i in range(max_wait):
        task_data = queue.get_task(task_id)
        if not task_data:
            console.print("[red]Task not found in Redis![/red]")
            break
            
        status = task_data.get("status")
        console.print(f"   [{i}s] Status: {status}")
        
        if status == "done":
            console.print("\n[green]✅ Task completed successfully![/green]")
            console.print(f"Result: {json.dumps(task_data.get('result', {}), indent=2)}")
            sys.exit(0)
        elif status == "failed":
            console.print(f"\n[red]❌ Task failed: {task_data.get('error')}[/red]")
            sys.exit(1)
        elif status == "blocked":
            console.print(f"\n[yellow]⚠️ Task blocked: {task_data.get('block_reason')}[/yellow]")
            console.print("Make sure the execution VM is online and the Dispatcher service loop is running.")
            sys.exit(1)
            
        time.sleep(1)
        
    console.print("\n[bold red]Timeout waiting for task completion.[/bold red]")
    console.print("Is `dispatcher/service.py` running on the VPS?")
    sys.exit(1)

if __name__ == "__main__":
    main()
