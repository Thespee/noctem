# Noctem v0.6.0 - Windows Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Prerequisites
- Python 3.9+ installed
- (Optional) Ollama for AI features

---

## Step 1: Install Dependencies

Open PowerShell in this folder and run:

```powershell
# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Initialize Database

```powershell
python -m noctem.main init
```

This creates `noctem/data/noctem.db` with the schema.

---

## Step 3: Run Noctem

### Option A: Web Dashboard Only (Easiest)
```powershell
python -m noctem.main web
```
Then open http://localhost:5000 in your browser.

### Option B: CLI Only
```powershell
python -m noctem.main cli
```

### Option C: Everything (Web + AI Loop)
```powershell
python -m noctem.main all
```

### Option D: AI Loop Only (for testing AI features)
```powershell
python -m noctem.main ai
```

---

## Step 4: (Optional) Setup Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy your bot token
4. Run the CLI and set the token:
   ```powershell
   python -m noctem.main cli
   > set telegram_bot_token YOUR_TOKEN_HERE
   > exit
   ```
5. Run with bot:
   ```powershell
   python -m noctem.main all
   ```
6. Send `/start` to your bot in Telegram

---

## Step 5: (Optional) Setup Ollama for AI Features

The AI features work without Ollama (rule-based scoring), but for full functionality:

### Install Ollama
1. Download from https://ollama.ai/download/windows
2. Install and run Ollama
3. Pull the required model:
   ```powershell
   ollama pull qwen3-vl:4b
   ```
   *(Already installed on this machine)*

### Verify Ollama is Running
```powershell
curl http://localhost:11434/api/tags
```

---

## 🎮 Quick Usage Guide

### Adding Tasks (CLI or Telegram)
```
buy groceries tomorrow
call mom friday 3pm !1
write report by feb 20 #work /myproject
```

### Task Modifiers
- `!1` - High priority
- `!2` - Medium (default)
- `!3` - Low priority
- `#tag` - Add tag
- `/project` - Assign to project

### Quick Actions
- `done 1` - Complete task #1
- `skip 2` - Defer to tomorrow
- `delete taskname` - Delete task

### Commands (CLI/Telegram)
- `today` or `/today` - Today's briefing
- `week` or `/week` - Week view
- `projects` - List projects
- `habits` - Habit stats
- `/nextaction` - Show next AI-suggested action
- `/aistatus` - Show AI system status
- `/aisettings` - Configure AI

### Web Dashboard
- http://localhost:5000/ - Main dashboard
- http://localhost:5000/calendar - Calendar import
- http://localhost:5000/breakdowns - AI breakdowns
- http://localhost:5000/clarifications - AI clarification requests
- http://localhost:5000/settings - Configuration

---

## 📊 Testing the AI Features

1. **Start the system:**
   ```powershell
   python -m noctem.main all
   ```

2. **Add some test tasks:**
   Open the CLI or Telegram and add:
   ```
   plan vacation
   research best laptop
   figure out taxes
   buy milk tomorrow
   call dentist friday
   ```

3. **Check AI scoring:**
   - Open http://localhost:5000/breakdowns
   - Tasks like "plan vacation" should have high AI scores
   - Tasks like "buy milk" should have low scores

4. **View AI status:**
   - In Telegram: `/aistatus`
   - Shows if Ollama is connected and models are loaded

5. **Get next action:**
   - In Telegram: `/nextaction`
   - Shows the first action for your highest-priority complex task

---

## 🔧 Troubleshooting

### "Module not found" errors
```powershell
pip install -r requirements.txt
```

### Database errors
```powershell
# Reset database (WARNING: deletes all data)
Remove-Item noctem/data/noctem.db
python -m noctem.main init
```

### AI not working
1. Check Ollama is running: `curl http://localhost:11434/api/tags`
2. Check models are pulled: `ollama list`
3. The system works without Ollama (rule-based scoring only)

### Port already in use
```powershell
# Use a different port
python -m noctem.main web --port 8080
```

---

## 📝 Providing Feedback for v0.6.1

As you use Noctem, please note:

1. **What works well?**
   - Which AI features are helpful?
   - Are the breakdowns useful?

2. **What's confusing?**
   - Any unclear commands?
   - Missing features?

3. **What breaks?**
   - Error messages
   - Unexpected behavior

4. **Feature requests?**
   - What would make this better?

Create issues or notes in the repository for v0.6.1 improvements!

---

## 📁 File Locations

| File | Purpose |
|------|---------|
| `noctem/data/noctem.db` | SQLite database (all your data) |
| `noctem/data/logs/noctem.log` | Log file |
| `noctem/ai/` | AI module (scorer, intentions, etc.) |
| `noctem/web/templates/` | Dashboard HTML templates |

---

## 🛠 Development Commands

```powershell
# Run tests
python -m pytest noctem/tests/ -v

# Check AI scorer on a task
python -c "from noctem.ai.scorer import TaskScorer; from noctem.models import Task; s=TaskScorer(); print(s.score(Task(name='plan vacation')))"

# Check database schema
sqlite3 noctem/data/noctem.db ".schema"
```

---

**Happy task managing! 🌙**

*Noctem v0.6.0 - Co-Authored-By: Warp <agent@warp.dev>*
