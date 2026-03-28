"""
compass_routes.py
Flask blueprint for serving Compass newsletter HTML files.
Add this to your MLB Stats Tracker app on Railway.

SETUP:
1. Copy this file to your mlb-slate-tracker project
2. Create a /compass_issues/ folder in your project root
3. Register the blueprint in app.py:
   from compass_routes import compass_bp
   app.register_blueprint(compass_bp)
4. Pipeline saves full HTML to /compass_issues/{date}.html
   (update OUTPUT_DIR in render_newsletter.py to point here)
"""

import os
from flask import Blueprint, abort, send_from_directory, render_template_string

compass_bp = Blueprint("compass", __name__)

# Directory where rendered newsletter HTML files are stored
# Update this path to match your Railway deployment structure
ISSUES_DIR = os.path.join(os.path.dirname(__file__), "compass_issues")


@compass_bp.route("/compass/<date_str>")
def serve_newsletter(date_str):
    """
    Serve a rendered newsletter HTML file by date.
    Example: /compass/2026-03-26
    """
    # Validate date format to prevent path traversal
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        abort(400)

    filename = f"compass_{date_str}.html"
    filepath = os.path.join(ISSUES_DIR, filename)

    if not os.path.exists(filepath):
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
          <title>Compass — Not Found</title>
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <style>
            body { font-family: sans-serif; text-align: center; padding: 60px 20px; color: #333; }
            h1 { font-size: 24px; }
            p { color: #666; }
            a { color: #1B3A6B; }
          </style>
        </head>
        <body>
          <h1>⚾ Compass</h1>
          <p>No edition found for {{ date }}.</p>
          <p><a href="/compass/latest">View latest edition →</a></p>
        </body>
        </html>
        """, date=date_str), 404

    return send_from_directory(ISSUES_DIR, filename)


@compass_bp.route("/compass/latest")
def serve_latest():
    """Redirect to the most recent newsletter edition."""
    from flask import redirect

    if not os.path.exists(ISSUES_DIR):
        abort(404)

    files = sorted([
        f for f in os.listdir(ISSUES_DIR)
        if f.startswith("compass_") and f.endswith(".html") and "teaser" not in f
    ])

    if not files:
        abort(404)

    latest = files[-1]
    date_str = latest.replace("compass_", "").replace(".html", "")
    return redirect(f"/compass/{date_str}")


@compass_bp.route("/compass")
def compass_index():
    """List all available newsletter editions."""
    if not os.path.exists(ISSUES_DIR):
        issues = []
    else:
        files = sorted([
            f for f in os.listdir(ISSUES_DIR)
            if f.startswith("compass_") and f.endswith(".html") and "teaser" not in f
        ], reverse=True)
        issues = [f.replace("compass_", "").replace(".html", "") for f in files]

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Compass — MLB Edition Archive</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        body { font-family: 'DM Sans', sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px; color: #111; }
        h1 { font-family: Georgia, serif; font-size: 28px; margin-bottom: 4px; }
        .sub { color: #6B6860; font-size: 12px; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 32px; }
        .issue { display: flex; justify-content: space-between; align-items: center; padding: 14px 0; border-bottom: 1px solid #E0DDD6; }
        .issue a { color: #1B3A6B; text-decoration: none; font-weight: 500; }
        .issue a:hover { text-decoration: underline; }
        .date { color: #6B6860; font-size: 12px; font-family: monospace; }
        .empty { color: #6B6860; font-style: italic; margin-top: 20px; }
      </style>
    </head>
    <body>
      <h1>⚾ Compass</h1>
      <div class="sub">MLB Edition · Archive</div>
      {% if issues %}
        {% for date in issues %}
        <div class="issue">
          <a href="/compass/{{ date }}">{{ date }}</a>
          <span class="date">View →</span>
        </div>
        {% endfor %}
      {% else %}
        <p class="empty">No editions published yet.</p>
      {% endif %}
    </body>
    </html>
    """, issues=issues)