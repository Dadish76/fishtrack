"""Сбор ограниченного снимка GitHub Actions без публикации токена и логов."""

import json
import os
import re
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

WORKFLOWS = {"FishTrack CI": "ci.yml", "Monitoring CI": "monitoring-ci.yml"}
STAGES = {
    "container_check": "Container Check",
    "build": "Docker Build",
    "image_scan": "Trivy Image Scan",
    "publish": "Publish to Local Registry",
    "deploy": "Deploy to staging",
}
STATES = ("success", "failure", "cancelled", "skipped", "queued", "in_progress", "other", "missing")
WINDOW = 30
POLL_SECONDS = 120


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api_client(repo, token):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not token:
        raise ValueError("Invalid repository or missing token")
    opener = build_opener(NoRedirect())

    def get(path):
        req = Request(
            f"https://api.github.com/repos/{repo}/actions/{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "fishtrack-actions-exporter",
            },
        )
        with opener.open(req, timeout=10) as response:
            return json.load(response)

    return get


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def duration(start, end):
    if not start or not end:
        return None
    value = timestamp(end) - timestamp(start)
    return value if value >= 0 else None


def state(obj):
    if obj is None:
        return "missing"
    status = obj.get("status")
    result = obj.get("conclusion") if status == "completed" else status
    if result in ("timed_out", "action_required", "startup_failure"):
        return "failure"
    if result in ("waiting", "pending", "requested"):
        return "queued"
    return result if result in STATES and result != "missing" else "other"


def metric(name, value, **labels):
    # Экранируем значения по формату Prometheus. Метки имеют ограниченный набор.
    def escape(v):
        return str(v).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')

    suffix = ""
    if labels:
        suffix = "{" + ",".join(f'{k}="{escape(v)}"' for k, v in labels.items()) + "}"
    return f"github_actions_{name}{suffix} {value}\n"


def one_hot(name, selected, **labels):
    return "".join(metric(name, int(s == selected), state=s, **labels) for s in STATES)


def snapshot(get):
    """Окно последних 30 запусков каждого workflow; это gauges, не counters."""
    output = []
    for workflow, filename in WORKFLOWS.items():
        runs = get(f"workflows/{filename}/runs?per_page={WINDOW}")["workflow_runs"]
        latest = max(runs, key=lambda r: (r["run_number"], r.get("run_attempt", 1)), default=None)
        for s in STATES:
            output.append(metric("runs_window", sum(state(r) == s for r in runs), workflow=workflow, state=s))
        output.append(metric("sample_size", len(runs), workflow=workflow))
        completed = [r for r in runs if r.get("status") == "completed"]
        if completed:
            output.append(metric("success_ratio", sum(state(r) == "success" for r in completed) / len(completed), workflow=workflow))
        output.append(one_hot("latest_run_state", state(latest), workflow=workflow))
        if latest:
            output.append(metric("latest_run_number", latest["run_number"], workflow=workflow))
            if latest.get("status") == "completed":
                elapsed = duration(latest.get("run_started_at"), latest.get("updated_at"))
                if elapsed is not None:
                    output.append(metric("latest_run_duration_seconds", elapsed, workflow=workflow))

    # CD имеет смысл только для push develop. PR и другие ветки не считаем поставкой.
    runs = get("workflows/ci.yml/runs?branch=develop&event=push&per_page=1")["workflow_runs"]
    jobs = []
    if runs:
        run = runs[0]
        output.append(metric("develop_run_number", run["run_number"]))
        page = 1
        while True:
            result = get(f"runs/{int(run['id'])}/jobs?filter=latest&per_page=100&page={page}")
            jobs.extend(result["jobs"])
            if len(jobs) >= result["total_count"] or len(result["jobs"]) < 100:
                break
            page += 1
            if page > 5:
                raise ValueError("Unexpected job count")
    for stage, expected in STAGES.items():
        matches = [j for j in jobs if j["name"].split(" / ")[-1] == expected]
        # При неоднозначности не утверждаем, что этап успешно прошел.
        job = matches[0] if len(matches) == 1 else None
        output.append(one_hot("stage_state", state(job), stage=stage))
        if job and job.get("status") == "completed":
            elapsed = duration(job.get("started_at"), job.get("completed_at"))
            if elapsed is not None:
                output.append(metric("stage_duration_seconds", elapsed, stage=stage))
    return "".join(output)


class Cache:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_success = 0
        self.body = metric("api_up", 0) + metric("last_success_timestamp_seconds", 0)

    def refresh(self, get):
        try:
            body = snapshot(get)
            self.last_success = time.time()
            body += metric("api_up", 1)
        except Exception as exc:
            # Не печатаем URL, тело ответа, заголовки или токен.
            code = f" HTTP {exc.code}" if isinstance(exc, HTTPError) else ""
            print(f"GitHub API collection failed: {type(exc).__name__}{code}", flush=True)
            # Не выдаем старые данные за актуальные при отказе API.
            body = metric("api_up", 0)
        body += metric("last_success_timestamp_seconds", self.last_success)
        with self.lock:
            self.body = body

    def read(self):
        with self.lock:
            return self.body.encode("utf-8")


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "Dadish76/fishtrack")
    token_path = Path(os.environ.get("GITHUB_TOKEN_FILE", "/run/secrets/github_actions_token"))
    cache = Cache()

    def poll():
        while True:
            try:
                get = api_client(repo, token_path.read_text(encoding="utf-8").strip())
            except Exception:
                def get(_):
                    raise ValueError("Token unavailable")
            cache.refresh(get)
            time.sleep(POLL_SECONDS)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/metrics":
                self.send_error(404)
                return
            body = cache.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    threading.Thread(target=poll, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", 9817), Handler).serve_forever()


if __name__ == "__main__":
    main()
