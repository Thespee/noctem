# Noctem v0.8.0

A self-hosted executive assistant system for task management, voice journaling, and AI-assisted daily organization.

## Features

- **Natural Language Task Input** - Add tasks via Telegram/CLI/Web with dates, priorities, tags
- **Voice Journals** - Upload audio, automatic transcription, edit transcripts
- **Butler Protocol** - Respectful AI outreach (max 5 contacts/week) with status updates
- **Priority System** - Importance (!1/!2/!3) × urgency (from due dates) = priority score
- **Calendar Integration** - ICS import from any calendar (Google, Apple, Outlook)
- **Web Dashboard** - Dark mode, mobile-friendly, 3-column layout with thinking feed
- **Remote Access** - Secure access via Tailscale VPN with `/access` command
- **Execution Logging** - Full pipeline tracing for debugging and self-improvement
- **Self-Improvement Engine** - Learns from patterns, generates insights, creates learned rules
- **Model Registry** - Dynamic local model discovery (Ollama) with benchmarking
- **Maintenance Scanner** - System health checks and actionable recommendations
- **Skills Infrastructure** - Extensible skill system with triggers, approval workflow, and execution logging

## Quick Start

```bash
# 1. Clone/copy project to your machine
# 2. Create virtual environment
python3 -m venv ~/noctem_venv
source ~/noctem_venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize database
python -m noctem.main init

# 5. Set Telegram bot token (get from @BotFather)
python -m noctem.cli
> set telegram_bot_token YOUR_TOKEN_HERE

# 6. Run!
bash start.sh        # QR code mode (default)
bash start.sh all    # Web + CLI with logs
bash start.sh cli    # CLI only
```

## Interfaces

| Interface | Description |
|-----------|-------------|
| **Telegram Bot** | Primary input - add tasks, quick actions, get briefings |
| **Web Dashboard** | Interactive view at `http://localhost:5000` (Voice, Calendar, Prompts, Settings) |
| **CLI** | Configuration, direct commands, `/summon` for corrections |

## Remote Access (Tailscale)

Access Noctem securely from anywhere using Tailscale VPN:

```powershell
# Install Tailscale
winget install Tailscale.Tailscale

# Authenticate (opens browser)
& "C:\Program Files\Tailscale\tailscale.exe" up

# Get your Tailscale IP
& "C:\Program Files\Tailscale\tailscale.exe" ip -4
```

Then access `http://<tailscale-ip>:5000` from any device on your Tailscale network.

**Telegram command:** `/access` sends you the remote URL directly.

## v0.8.0 New Features: Skills Infrastructure

```bash
# Skills: Extensible system for packaged knowledge + procedures
# - SKILL.yaml metadata + instructions.md format
# - RapidFuzz pattern matching for triggers
# - Approval workflow for sensitive skills
# - Full execution logging

# CLI skill commands
noctem skill list               # List all installed skills
noctem skill info <name>        # Show skill details
noctem skill run <name> [input] # Execute a skill
noctem skill enable <name>      # Enable a skill
noctem skill disable <name>     # Disable a skill
noctem skill create <name>      # Scaffold a new skill
noctem skill validate <path>    # Validate SKILL.yaml

# Telegram skill commands
/skill list                     # List enabled skills
/skill info <name>              # Show skill details  
/skill run <name> [input]       # Execute a skill
```

## v0.7.0 Features: Self-Improvement

```bash
# Self-improvement: pattern detection and learning
# - Detects recurring issues (ambiguities, extraction failures, corrections)
# - Generates insights from patterns (max 3 per review)
# - Creates learned rules to improve future classifications
# - Runs automatically (weekly OR 50+ thoughts OR 10+ patterns)

# Summon Butler for corrections/queries
noctem summon "actually that task is for next week"
noctem summon "what's my status?"

# Maintenance commands
noctem maintenance models    # List available LLMs
noctem maintenance scan      # Run health check
noctem maintenance insights  # View recommendations
noctem maintenance preview   # Preview Butler report
```

## Project Structure

```
noctem/
├── main.py           # Entry point
├── cli.py            # Interactive CLI + /summon + skill commands
├── db.py             # SQLite database (13 tables)
├── models.py         # Data models (19 dataclasses)
├── config.py         # Configuration
├── parser/           # Natural language parsing
├── services/         # Business logic (tasks, suggestions, prompts)
├── skills/           # Skills infrastructure
│   ├── loader.py     # YAML parsing, validation
│   ├── registry.py   # Discovery, CRUD, stats
│   ├── trigger.py    # Pattern matching (RapidFuzz)
│   ├── executor.py   # Execution flow, approval workflow
│   └── service.py    # High-level API
├── fast/             # Fast path: classifier, capture, voice cleanup
├── slow/             # Slow path: LLM analysis, model registry
├── butler/           # Butler protocol, summon handler, clarifications
├── logging/          # Execution logging with trace IDs
├── maintenance/      # System scanner, insights, reports
├── telegram/         # Bot handlers
├── scheduler/        # APScheduler jobs
├── web/              # Flask dashboard + templates
└── data/
    ├── noctem.db     # SQLite database
    ├── skills/       # User-created skills
    └── voice_journals/  # Audio files
```

## Documentation

- [docs/USER_GUIDE_v0.8.0.md](docs/USER_GUIDE_v0.8.0.md) - User guide with all features
- [docs/improvements.md](docs/improvements.md) - Design notes, roadmap, learnings
- [docs/Ideals_v0.7.0.md](docs/Ideals_v0.7.0.md) - Aspirational vision and philosophy
- [docs/discussion_v0.7.0.md](docs/discussion_v0.7.0.md) - Critical analysis and technical review
- [SETUP.md](SETUP.md) - Detailed setup guide
- [COMMANDS.md](COMMANDS.md) - All commands reference

## Data Model

```
Goal (long-term outcome)
├── Project (bounded effort)
│   └── Task (atomic action)
└── Project
    └── Task

Habit (recurring tracked behavior)
TimeBlock (calendar events)
```

## License

Personal project - not licensed for distribution.
