"""
Flask web dashboard for Noctem.
Read-only view of goals, projects, tasks, and habits.
"""
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import date, datetime, timedelta

from ..config import Config
from ..services import task_service, project_service, goal_service, habit_service
from ..services.briefing import get_time_blocks_for_date
from ..services.ics_import import (
    import_ics_bytes, import_ics_url, clear_ics_events,
    get_saved_urls, save_url, remove_url, refresh_all_urls, refresh_url
)

# Common timezones for settings dropdown
COMMON_TIMEZONES = [
    "America/Vancouver", "America/Los_Angeles", "America/Denver", 
    "America/Chicago", "America/New_York", "America/Toronto",
    "America/Sao_Paulo", "Europe/London", "Europe/Paris", 
    "Europe/Berlin", "Europe/Moscow", "Asia/Dubai",
    "Asia/Kolkata", "Asia/Singapore", "Asia/Tokyo",
    "Asia/Shanghai", "Australia/Sydney", "Pacific/Auckland",
    "UTC"
]


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, 
                template_folder="templates",
                static_folder="static")
    app.secret_key = 'noctem-dev-key'  # For flash messages
    
    @app.route("/")
    def dashboard():
        """Main dashboard view."""
        today = date.today()
        
        # Today's data
        today_tasks = task_service.get_tasks_due_today()
        overdue_tasks = task_service.get_overdue_tasks()
        priority_tasks = task_service.get_priority_tasks(5)
        time_blocks = get_time_blocks_for_date(today)
        
        # Goals and projects hierarchy
        goals = goal_service.get_all_goals()
        goals_data = []
        for goal in goals:
            projects = project_service.get_all_projects(goal_id=goal.id)
            projects_data = []
            for project in projects:
                tasks = task_service.get_project_tasks(project.id)
                projects_data.append({
                    "project": project,
                    "tasks": tasks,
                    "done_count": len([t for t in tasks if t.status == "done"]),
                    "total_count": len(tasks),
                })
            goals_data.append({
                "goal": goal,
                "projects": projects_data,
            })
        
        # Standalone projects (no goal)
        standalone_projects = project_service.get_all_projects(goal_id=None)
        standalone_data = []
        for project in standalone_projects:
            if project.goal_id is None:
                tasks = task_service.get_project_tasks(project.id)
                standalone_data.append({
                    "project": project,
                    "tasks": tasks,
                    "done_count": len([t for t in tasks if t.status == "done"]),
                    "total_count": len(tasks),
                })
        
        # Inbox (tasks without project)
        inbox_tasks = task_service.get_inbox_tasks()
        
        # Habits with stats
        habits_stats = habit_service.get_all_habits_stats()
        
        # Week view (with calendar events)
        week_data = []
        for i in range(7):
            day = today + timedelta(days=i)
            day_tasks = task_service.get_tasks_due_on(day)
            day_events = get_time_blocks_for_date(day)
            week_data.append({
                "date": day,
                "day_name": day.strftime("%a"),
                "is_today": day == today,
                "tasks": day_tasks,
                "events": day_events,
            })
        
        # 2D graph data (urgency x importance)
        all_active_tasks = task_service.get_all_tasks(include_done=False)
        graph_tasks = []
        for task in all_active_tasks:
            graph_tasks.append({
                "id": task.id,
                "name": task.name[:30] + "..." if len(task.name) > 30 else task.name,
                "urgency": task.urgency,
                "importance": task.importance,
                "priority_score": task.priority_score,
            })
        
        return render_template(
            "dashboard.html",
            today=today,
            today_tasks=today_tasks,
            overdue_tasks=overdue_tasks,
            priority_tasks=priority_tasks,
            time_blocks=time_blocks,
            goals_data=goals_data,
            standalone_projects=standalone_data,
            inbox_tasks=inbox_tasks,
            habits_stats=habits_stats,
            week_data=week_data,
            graph_tasks=graph_tasks,
        )
    
    @app.route("/health")
    def health():
        """Health check endpoint."""
        return {"status": "ok", "time": datetime.now().isoformat()}
    
    @app.route("/calendar", methods=["GET", "POST"])
    def calendar_upload():
        """Calendar ICS upload page."""
        if request.method == "POST":
            # Check for URL to save
            ics_url = request.form.get('ics_url', '').strip()
            url_name = request.form.get('url_name', '').strip()
            
            if ics_url:
                try:
                    stats = save_url(ics_url, url_name if url_name else None)
                    if 'error' in stats.get('status', ''):
                        flash(f"Error fetching URL: {stats.get('message')}", 'error')
                    else:
                        flash(f"Saved & imported: {stats['created']} new, {stats['updated']} updated, {stats['skipped']} skipped", 'success')
                except Exception as e:
                    flash(f"Error importing: {str(e)}", 'error')
                return redirect(url_for('calendar_upload'))
            
            # Check for file upload
            if 'ics_file' not in request.files or request.files['ics_file'].filename == '':
                flash('Please provide a URL or upload a file', 'error')
                return redirect(url_for('calendar_upload'))
            
            file = request.files['ics_file']
            if file and file.filename.endswith('.ics'):
                try:
                    content = file.read()
                    stats = import_ics_bytes(content)
                    flash(f"Imported: {stats['created']} new, {stats['updated']} updated, {stats['skipped']} skipped", 'success')
                except Exception as e:
                    flash(f"Error importing: {str(e)}", 'error')
            else:
                flash('Please upload a .ics file', 'error')
            
            return redirect(url_for('calendar_upload'))
        
        # GET - show upload form
        from ..db import get_db
        with get_db() as conn:
            events = conn.execute("""
                SELECT * FROM time_blocks 
                WHERE start_time >= date('now', '-1 day')
                ORDER BY start_time ASC
                LIMIT 50
            """).fetchall()
        
        saved_urls = get_saved_urls()
        return render_template("calendar.html", events=events, saved_urls=saved_urls)
    
    @app.route("/calendar/refresh", methods=["POST"])
    def calendar_refresh():
        """Refresh a single URL or all saved URLs."""
        url = request.form.get('url', '').strip()
        
        if url:
            # Refresh single URL
            try:
                stats = refresh_url(url)
                if 'error' in stats.get('status', ''):
                    flash(f"Error: {stats.get('message')}", 'error')
                else:
                    flash(f"Refreshed: {stats['created']} new, {stats['updated']} updated", 'success')
            except Exception as e:
                flash(f"Error: {str(e)}", 'error')
        else:
            # Refresh all
            stats = refresh_all_urls()
            if stats['errors']:
                flash(f"Refreshed with errors: {', '.join(stats['errors'])}", 'error')
            else:
                flash(f"Refreshed all: {stats['created']} new, {stats['updated']} updated", 'success')
        
        return redirect(url_for('calendar_upload'))
    
    @app.route("/calendar/remove", methods=["POST"])
    def calendar_remove_url():
        """Remove a saved URL."""
        url = request.form.get('url', '').strip()
        if url:
            remove_url(url)
            flash("URL removed", 'success')
        return redirect(url_for('calendar_upload'))
    
    @app.route("/calendar/clear", methods=["POST"])
    def calendar_clear():
        """Clear all imported calendar events."""
        count = clear_ics_events()
        flash(f"Cleared {count} calendar events", 'success')
        return redirect(url_for('calendar_upload'))
    
    @app.route("/settings", methods=["GET", "POST"])
    def settings():
        """Settings page for configuring Noctem."""
        if request.method == "POST":
            # Save all config values
            fields = [
                'telegram_bot_token', 'telegram_chat_id', 'timezone',
                'morning_message_time', 'web_host', 'web_port'
            ]
            for field in fields:
                value = request.form.get(field, '').strip()
                if field == 'web_port':
                    try:
                        value = int(value) if value else 5000
                    except ValueError:
                        value = 5000
                if value or field in ['telegram_bot_token', 'telegram_chat_id']:
                    Config.set(field, value)
            
            Config.clear_cache()
            flash('Settings saved successfully!', 'success')
            return redirect(url_for('settings'))
        
        # GET - show settings form
        config = Config.get_all()
        return render_template(
            "settings.html",
            config=config,
            timezones=COMMON_TIMEZONES,
        )
    
    # AI Routes (v0.6.0)
    
    @app.route("/breakdowns")
    def breakdowns():
        """AI implementation intentions page."""
        intentions = task_service.get_tasks_with_intentions()
        
        # Get AI status
        try:
            from ..ai.loop import AILoop
            loop = AILoop()
            ai_status = loop.get_status()
        except Exception:
            ai_status = {'health_level': 'unknown', 'unscored_tasks': 0, 'pending_slow_work': 0}
        
        return render_template("breakdowns.html", intentions=intentions, ai_status=ai_status)
    
    @app.route("/breakdowns/approve/<int:intention_id>", methods=["POST"])
    def approve_breakdown(intention_id):
        """Approve an implementation intention."""
        from ..ai.intention_generator import IntentionGenerator
        generator = IntentionGenerator()
        generator.approve_intention(intention_id)
        flash("Breakdown approved!", "success")
        return redirect(url_for('breakdowns'))
    
    @app.route("/breakdowns/regenerate/<int:task_id>", methods=["POST"])
    def regenerate_breakdown(task_id):
        """Regenerate implementation intention for a task."""
        from ..ai.intention_generator import IntentionGenerator
        generator = IntentionGenerator()
        intention = generator.generate(task_id)
        if intention:
            flash("New breakdown generated!", "success")
        else:
            flash("Could not generate breakdown - check if Ollama is running", "error")
        return redirect(url_for('breakdowns'))
    
    @app.route("/clarifications")
    def clarifications():
        """Clarification requests page."""
        from ..ai.clarification import ClarificationGenerator
        generator = ClarificationGenerator()
        pending = generator.get_pending_clarifications()
        
        # Enrich with task names
        clarifications_with_tasks = []
        for c in pending:
            task = task_service.get_task(c.task_id)
            clarifications_with_tasks.append({
                'id': c.id,
                'question': c.question,
                'options': c.options,
                'task_name': task.name if task else 'Unknown task'
            })
        
        return render_template("clarifications.html", clarifications=clarifications_with_tasks)
    
    @app.route("/clarifications/respond/<int:clarification_id>", methods=["POST"])
    def respond_clarification(clarification_id):
        """Respond to a clarification request."""
        from ..ai.clarification import ClarificationGenerator
        generator = ClarificationGenerator()
        
        response = request.form.get('custom_response') or request.form.get('response')
        if response:
            generator.respond_to_clarification(clarification_id, response)
            flash("Response recorded!", "success")
        else:
            flash("Please select or enter a response", "error")
        
        return redirect(url_for('clarifications'))
    
    @app.route("/clarifications/skip/<int:clarification_id>", methods=["POST"])
    def skip_clarification(clarification_id):
        """Skip a clarification request."""
        from ..ai.clarification import ClarificationGenerator
        generator = ClarificationGenerator()
        generator.skip_clarification(clarification_id)
        flash("Clarification skipped", "success")
        return redirect(url_for('clarifications'))
    
    @app.route("/settings/test", methods=["POST"])
    def settings_test():
        """Send a test message to Telegram."""
        import requests as http_requests
        
        token = Config.telegram_token()
        chat_id = Config.telegram_chat_id()
        
        if not token:
            flash('Telegram bot token not set!', 'error')
            return redirect(url_for('settings'))
        
        if not chat_id:
            flash('Telegram chat ID not set! Send /start to your bot first.', 'error')
            return redirect(url_for('settings'))
        
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            response = http_requests.post(url, json={
                'chat_id': chat_id,
                'text': '✅ Noctem test message - connection working!',
            }, timeout=10)
            
            if response.ok:
                flash('Test message sent successfully! Check Telegram.', 'success')
            else:
                error = response.json().get('description', 'Unknown error')
                flash(f'Telegram API error: {error}', 'error')
        except Exception as e:
            flash(f'Connection error: {str(e)}', 'error')
        
        return redirect(url_for('settings'))
    
    return app


def run_web():
    """Run the web dashboard."""
    app = create_app()
    host = Config.web_host()
    port = Config.web_port()
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run_web()
