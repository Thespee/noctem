"""
Standalone test runner for Noctem v0.6.0
Runs without pytest to avoid Windows issues
"""
import sys
import os
from datetime import date, datetime

sys.path.insert(0, '.')

# Import test subjects
from noctem.models import Task
from noctem.ai.scorer import TaskScorer
from noctem.ai.router import PathRouter
from noctem.ai.degradation import GracefulDegradation

passed = 0
failed = 0

def test(name, condition, details=""):
    global passed, failed
    if condition:
        print(f"  ✓ {name}")
        passed += 1
    else:
        print(f"  ✗ {name} - {details}")
        failed += 1

print("=" * 60)
print("Noctem v0.6.0 Test Suite")
print("=" * 60)

# === SCORER TESTS ===
print("\n[TaskScorer Tests]")
scorer = TaskScorer()

# Test 1: Short vague task scores high
task = Task(name="project stuff")
result = scorer.score(task)
test("Short vague task scores >= 0.3", result.score >= 0.3, f"got {result.score}")

# Test 2: Clear action scores low
task = Task(name="call mom", due_date=date.today())
result = scorer.score(task)
test("Clear action task scores < 0.3", result.score < 0.3, f"got {result.score}")

# Test 3: Complex keyword increases score
task = Task(name="research best practices for database design")
result = scorer.score(task)
test("Complex keywords increase score", result.score >= 0.3, f"got {result.score}")

# Test 4: Question increases score
task = Task(name="figure out how to fix the bug?")
result = scorer.score(task)
test("Question mark increases score", result.score >= 0.2, f"got {result.score}")

# Test 5: Score bounded 0-1
tasks = [Task(name="x"), Task(name="a" * 100), Task(name="buy milk")]
all_bounded = all(0.0 <= scorer.score(t).score <= 1.0 for t in tasks)
test("Scores always bounded 0-1", all_bounded)

# Test 6: should_generate_intention works
high_task = Task(name="plan the project roadmap")
low_task = Task(name="send email to john")
test("should_generate_intention high task", scorer.should_generate_intention(high_task, 0.3))
test("should_generate_intention low task false", not scorer.should_generate_intention(low_task, 0.5))

# === ROUTER TESTS ===
print("\n[PathRouter Tests]")
router = PathRouter()

# Test 7: Fast tasks route fast
for task_type in ['register_task', 'status_query', 'score_task']:
    decision = router.route(task_type)
    test(f"'{task_type}' routes to fast", decision.path == 'fast')

# Test 8: Slow tasks route slow
for task_type in ['implementation_intention', 'task_decomposition']:
    decision = router.route(task_type)
    test(f"'{task_type}' routes to slow", decision.path == 'slow')

# Test 9: Unknown defaults to fast
decision = router.route('unknown_thing')
test("Unknown routes to fast (safe default)", decision.path == 'fast')

# Test 10: Context affects routing
decision = router.route('unknown', context={'requires_generation': True})
test("requires_generation context routes slow", decision.path == 'slow')

# Test 11: Queue priority
p1 = router.get_slow_queue_priority('test', {'user_initiated': True})
p2 = router.get_slow_queue_priority('test', {'user_initiated': False})
test("User-initiated gets higher priority", p1 > p2)

# === DEGRADATION TESTS ===
print("\n[GracefulDegradation Tests]")
degradation = GracefulDegradation()

# Test 12: Health check returns HealthStatus
health = degradation.check_health()
test("Health check returns HealthStatus", hasattr(health, 'level'))
test("Health level is valid", health.level in ('full', 'degraded', 'minimal', 'offline'))
test("Has last_check timestamp", isinstance(health.last_check, datetime))

# Test 13: get_last_health caches
health2 = degradation.get_last_health()
test("get_last_health returns cached result", health.last_check == health2.last_check)

# === DATABASE TESTS ===
print("\n[Database Tests]")
from noctem.db import get_db, init_db

# Reinit to make sure schema is current
init_db()

with get_db() as conn:
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t['name'] for t in tables]

required_tables = [
    'tasks', 'projects', 'goals', 'habits', 
    'implementation_intentions', 'next_steps', 
    'clarification_requests', 'pending_slow_work',
    'notification_responses'
]
for table in required_tables:
    test(f"Table '{table}' exists", table in table_names)

# === SERVICE TESTS ===
print("\n[Service Tests]")
from noctem.services import task_service

# Test: Create task
task = task_service.create_task("test task for verification", importance=0.8)
test("Create task works", task is not None and task.id is not None)
test("Task has correct name", task.name == "test task for verification")
test("Task has correct importance", task.importance == 0.8)

# Test: Get task
retrieved = task_service.get_task(task.id)
test("Get task by ID works", retrieved is not None)
test("Retrieved task matches", retrieved.name == task.name)

# Test: AI scoring methods
unscored = task_service.get_unscored_tasks(limit=5)
test("get_unscored_tasks works", isinstance(unscored, list))

# Test: Update AI score
updated = task_service.update_ai_score(task.id, 0.75)
test("update_ai_score works", updated is not None)
test("AI score was set", updated.ai_help_score == 0.75)

# Test: Complete task
completed = task_service.complete_task(task.id)
test("Complete task works", completed.status == "done")

# === INTEGRATION TESTS ===
print("\n[Integration Tests]")

# Full flow: create task -> score -> check if queued
task2 = task_service.create_task("plan complex multi-step project")
score_result = scorer.score(task2)
test("Complex task gets high score", score_result.score >= 0.3, f"got {score_result.score}")

# Check Ollama connectivity
if health.ollama_available:
    test("Ollama is available", True)
    test("Model is loaded", health.fast_model_loaded or health.slow_model_loaded)
else:
    print("  ⚠ Ollama not available - skipping LLM tests")

# === V0.5 FUNCTIONALITY TESTS ===
print("\n[v0.5 Core Functionality Tests]")

# Test: Project service
from noctem.services import project_service
project = project_service.create_project("Test Project")
test("Create project works", project is not None and project.id is not None)
test("Project has correct name", project.name == "Test Project")

# Test: Goal service  
from noctem.services import goal_service
goal = goal_service.create_goal("Test Goal")
test("Create goal works", goal is not None and goal.id is not None)

# Test: Habit service
from noctem.services import habit_service
habit = habit_service.create_habit("Test Habit", frequency="daily")
test("Create habit works", habit is not None and habit.id is not None)
habit_service.log_habit(habit.id)
stats = habit_service.get_habit_stats(habit.id)
test("Log habit and get stats works", stats is not None)

# Test: Task with project
task_with_proj = task_service.create_task("task in project", project_id=project.id)
test("Create task with project works", task_with_proj.project_id == project.id)

# Test: Priority tasks
priority_tasks = task_service.get_priority_tasks(5)
test("get_priority_tasks works", isinstance(priority_tasks, list))

# Test: Overdue tasks
overdue = task_service.get_overdue_tasks()
test("get_overdue_tasks works", isinstance(overdue, list))

# Test: Parser
from noctem.parser.task_parser import parse_task
parsed = parse_task("buy groceries tomorrow !1 #shopping")
test("Task parser parses name", parsed.name.lower() == "buy groceries")
test("Task parser parses importance", parsed.importance == 1.0)
test("Task parser parses tags", "shopping" in parsed.tags)
test("Task parser parses date", parsed.due_date is not None)

# Test: Command parser
from noctem.parser.command import parse_command, CommandType
cmd = parse_command("done 1")
test("Command parser: done command", cmd.type == CommandType.DONE)
cmd = parse_command("skip 2")
test("Command parser: skip command", cmd.type == CommandType.SKIP)
cmd = parse_command("today")
test("Command parser: today command", cmd.type == CommandType.TODAY)

# Test: Briefing service
from noctem.services.briefing import generate_morning_briefing, generate_today_view
briefing = generate_morning_briefing()
test("Morning briefing generates", isinstance(briefing, str) and len(briefing) > 0)
today_view = generate_today_view()
test("Today view generates", isinstance(today_view, str))

# Test: Web app creation
from noctem.web.app import create_app
app = create_app()
test("Flask app creates", app is not None)
test("Flask app has routes", len(app.url_map._rules) > 0)

# Test routes exist
routes = [rule.rule for rule in app.url_map.iter_rules()]
test("Dashboard route exists", '/' in routes)
test("Calendar route exists", '/calendar' in routes)
test("Settings route exists", '/settings' in routes)
test("Breakdowns route exists", '/breakdowns' in routes)
test("Clarifications route exists", '/clarifications' in routes)

# Test: Config
from noctem.config import Config
test("Config.get works", Config.get('web_port') is not None)
test("Config.get_all works", isinstance(Config.get_all(), dict))
Config.set('test_key', 'test_value')
test("Config.set works", Config.get('test_key') == 'test_value')

# === SUMMARY ===
print("\n" + "=" * 60)
total = passed + failed
print(f"Results: {passed}/{total} tests passed")
if failed > 0:
    print(f"         {failed} tests FAILED")
    sys.exit(1)
else:
    print("All tests PASSED! ✓")
    sys.exit(0)
