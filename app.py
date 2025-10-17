from flask import Flask, request, jsonify
import os
import base64
import shutil
import subprocess
import datetime

# === CONFIGURATION ===
SECRET = "NotApassword324"  # your chosen secret
GITHUB_USERNAME = "23f3002461"
GITHUB_REPO = "TDS-Project-1"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # set this in your environment
BRANCH = "main"
APP_FOLDER = "app_files"  # temporary folder for generating app
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
PAGES_URL = f"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO}/"

# Create Flask app
app = Flask(__name__)

# --- Helper functions ---
def save_attachments(attachments):
    # Delete previous folder safely
    if os.path.exists(APP_FOLDER):
        try:
            shutil.rmtree(APP_FOLDER)
        except PermissionError:
            # Windows might lock files
            pass
    os.makedirs(APP_FOLDER, exist_ok=True)

    for attach in attachments:
        name = attach.get("name")
        url = attach.get("url", "")
        if name and url.startswith("data:"):
            header, encoded = url.split(",", 1)
            content = base64.b64decode(encoded)
            with open(os.path.join(APP_FOLDER, name), "wb") as f:
                f.write(content)

def generate_index_html(brief, attachments, round_index):
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Task Round {round_index}</title>
</head>
<body>
    <h1>{brief}</h1>
    <p>Attachments saved: {', '.join([a['name'] for a in attachments])}</p>
</body>
</html>"""
    with open(os.path.join(APP_FOLDER, "index.html"), "w") as f:
        f.write(html_content)

def generate_readme(task, round_index):
    content = f"""# {task} - Round {round_index}

This project implements the app generated for task `{task}` in round {round_index}.

## Setup
- Python 3.x
- Flask installed (`pip install flask`)
- Run `python app.py` locally or view on GitHub Pages

## Usage
Open `index.html` or visit the Pages URL: {PAGES_URL}

## License
MIT License
"""
    with open(os.path.join(APP_FOLDER, "README.md"), "w") as f:
        f.write(content)

def generate_license():
    mit_text = f"""MIT License

Copyright (c) 2025 {GITHUB_USERNAME}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files...
"""
    with open(os.path.join(APP_FOLDER, "LICENSE"), "w") as f:
        f.write(mit_text)

def git_push(task, round_index):
    # Commit from the repo root, not inside app_files
    commit_msg = f"Phase {round_index} app update - {datetime.datetime.now().isoformat()}"
    subprocess.run(["git", "add", APP_FOLDER, "app.py"], cwd=REPO_ROOT)
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_ROOT)

    # Push using PAT
    repo_url_with_token = f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{GITHUB_REPO}.git"
    subprocess.run(["git", "push", repo_url_with_token, BRANCH, "--force"], cwd=REPO_ROOT)

    # Get latest commit SHA
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True)
    return result.stdout.strip()

# --- API Endpoint ---
@app.route("/api-endpoint", methods=["POST"])
def api_endpoint():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    # Verify secret
    if data.get("secret") != SECRET:
        return jsonify({"error": "Invalid secret"}), 403

    task = data.get("task", "task1")
    round_index = data.get("round", 1)
    nonce = data.get("nonce", "")
    brief = data.get("brief", "")
    attachments = data.get("attachments", [])
    evaluation_url = data.get("evaluation_url", "")

    # --- Generate app files ---
    save_attachments(attachments)
    generate_index_html(brief, attachments, round_index)
    generate_readme(task, round_index)
    generate_license()

    # --- Push to GitHub ---
    commit_sha = git_push(task, round_index)

    # --- Prepare response ---
    response = {
        "email": data.get("email"),
        "task": task,
        "round": round_index,
        "nonce": nonce,
        "repo_url": f"https://github.com/{GITHUB_USERNAME}/{GITHUB_REPO}",
        "commit_sha": commit_sha,
        "pages_url": PAGES_URL
    }

    # Optionally, send POST to evaluation_url
    if evaluation_url:
        try:
            import requests
            requests.post(evaluation_url, json=response, timeout=5)
        except:
            pass

    return jsonify({"status": "received", "repo_url": response["repo_url"], "pages_url": PAGES_URL})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
