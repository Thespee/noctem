"""Quick verification script for Noctem v0.6.0"""
import sys
sys.path.insert(0, '.')

print("=" * 50)
print("Noctem v0.6.0 Verification")
print("=" * 50)

# Test 1: Imports
print("\n[1] Testing imports...")
try:
    from noctem.ai import TaskScorer, PathRouter, GracefulDegradation, AILoop
    from noctem.models import Task, ImplementationIntention, ClarificationRequest
    from noctem.services import task_service
    from noctem.config import Config
    print("    ✓ All imports successful")
except Exception as e:
    print(f"    ✗ Import error: {e}")
    sys.exit(1)

# Test 2: Config
print("\n[2] Testing config...")
print(f"    Fast model: {Config.get('fast_model')}")
print(f"    Slow model: {Config.get('slow_model')}")
print(f"    Ollama host: {Config.get('ollama_host')}")

# Test 3: AI Scorer
print("\n[3] Testing AI Scorer...")
scorer = TaskScorer()
test_tasks = [
    ("plan vacation", 0.3),  # Should be high
    ("buy milk", 0.0),       # Should be low  
    ("research best laptop for work", 0.3),  # Should be high
]
for name, min_score in test_tasks:
    task = Task(name=name)
    result = scorer.score(task)
    status = "✓" if result.score >= min_score else "✗"
    print(f"    {status} '{name}': {result.score:.2f}")

# Test 4: Health Check
print("\n[4] Testing Ollama connection...")
degradation = GracefulDegradation()
health = degradation.check_health()
print(f"    Health level: {health.level}")
print(f"    Ollama available: {health.ollama_available}")
print(f"    Fast model loaded: {health.fast_model_loaded}")
print(f"    Slow model loaded: {health.slow_model_loaded}")
print(f"    Message: {health.message}")

# Test 5: Database
print("\n[5] Testing database...")
from noctem.db import get_db
with get_db() as conn:
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t['name'] for t in tables]
    required = ['tasks', 'implementation_intentions', 'next_steps', 'clarification_requests']
    for t in required:
        status = "✓" if t in table_names else "✗"
        print(f"    {status} Table '{t}' exists")

# Test 6: Create and score a task
print("\n[6] Testing task creation and scoring...")
task = task_service.create_task("plan project roadmap")
print(f"    ✓ Created task: {task.name} (id={task.id})")
score = scorer.score(task)
print(f"    ✓ AI score: {score.score:.2f}")

print("\n" + "=" * 50)
print("Verification complete!")
print("=" * 50)
