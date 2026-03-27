#!/usr/bin/env python3
"""
Fetch all GitLab commits and send them to Splunk via HTTP Event Collector (HEC).
Designed to support a "Commits per Project per User" Splunk dashboard.

Required environment variables:
    GITLAB_URL          e.g. https://gitlab.example.com
    GITLAB_TOKEN        GitLab personal access token (admin)
    SPLUNK_HEC_URL      e.g. https://splunk.example.com:8088
    SPLUNK_HEC_TOKEN    Splunk HEC token

Optional environment variables:
    SPLUNK_INDEX        Splunk index to write to (default: main)
    SPLUNK_SOURCE       Splunk source field  (default: gitlab:commits)
    SPLUNK_SOURCETYPE   Splunk sourcetype    (default: gitlab_commit)

Usage:
    python gitlab_commits_to_splunk.py [--since 2024-01-01T00:00:00Z] [--project-filter group/repo]
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

# ---------------------------------------------------------------------------
# Config / defaults
# ---------------------------------------------------------------------------

GITLAB_PER_PAGE  = 100
SPLUNK_BATCH_SIZE = 500      # events per HEC request
MAX_RETRIES      = 3
RETRY_WAIT       = 5         # seconds


def require_env(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        print(f"ERROR: Environment variable '{key}' is not set.", file=sys.stderr)
        sys.exit(1)
    return val


def optional_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip() or default


# ---------------------------------------------------------------------------
# GitLab helpers
# ---------------------------------------------------------------------------

def gitlab_paginate(session: requests.Session, url: str, params: dict = None) -> list:
    """Return all items from a paginated GitLab endpoint."""
    params = dict(params or {})
    params.update({"per_page": GITLAB_PER_PAGE, "page": 1})
    results = []

    while True:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                break
            except requests.RequestException as exc:
                if attempt == MAX_RETRIES:
                    print(f"  WARNING: Skipping page after {MAX_RETRIES} retries: {exc}", file=sys.stderr)
                    return results
                time.sleep(RETRY_WAIT)

        page_data = resp.json()
        if not page_data:
            break
        results.extend(page_data)

        next_page = resp.headers.get("x-next-page", "")
        if not next_page:
            break
        params["page"] = int(next_page)

    return results


def get_projects(session: requests.Session, base_url: str, project_filter: str = "") -> list:
    print("Fetching GitLab projects...", flush=True)
    projects = gitlab_paginate(
        session,
        f"{base_url}/api/v4/projects",
        {"membership": False, "simple": True},
    )
    if project_filter:
        projects = [p for p in projects if project_filter.lower() in p.get("path_with_namespace", "").lower()]
    print(f"  -> {len(projects)} project(s) found.", flush=True)
    return projects


def get_commits(session: requests.Session, base_url: str, project: dict,
                since: str = "", until: str = "") -> list:
    params = {"all": "true", "with_stats": "false"}
    if since:
        params["since"] = since
    if until:
        params["until"] = until

    raw = gitlab_paginate(
        session,
        f"{base_url}/api/v4/projects/{project['id']}/repository/commits",
        params,
    )
    return raw


def iso_to_epoch(iso_str: str) -> float:
    """Convert an ISO 8601 string to a Unix timestamp (float)."""
    if not iso_str:
        return time.time()
    try:
        # Python 3.7+ handles most ISO 8601 with fromisoformat after stripping Z
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.timestamp()
    except ValueError:
        try:
            dt = parsedate_to_datetime(iso_str)
            return dt.timestamp()
        except Exception:
            return time.time()


# ---------------------------------------------------------------------------
# Splunk HEC helpers
# ---------------------------------------------------------------------------

def build_hec_event(commit: dict, project: dict,
                    index: str, source: str, sourcetype: str) -> dict:
    """Build a single Splunk HEC event payload from a GitLab commit."""
    committed_epoch = iso_to_epoch(commit.get("committed_date", ""))
    return {
        "time": committed_epoch,
        "host": "gitlab",
        "source": source,
        "sourcetype": sourcetype,
        "index": index,
        "event": {
            # Project fields
            "project_id":        project["id"],
            "project_name":      project.get("path_with_namespace", ""),
            "project_namespace": project.get("namespace", {}).get("full_path", "") if isinstance(project.get("namespace"), dict) else "",
            # Commit fields
            "commit_id":         commit.get("id", ""),
            "short_id":          commit.get("short_id", ""),
            "title":             commit.get("title", "").replace("\n", " "),
            "author_name":       commit.get("author_name", ""),
            "author_email":      commit.get("author_email", ""),
            "authored_date":     commit.get("authored_date", ""),
            "committer_name":    commit.get("committer_name", ""),
            "committer_email":   commit.get("committer_email", ""),
            "committed_date":    commit.get("committed_date", ""),
            "web_url":           commit.get("web_url", ""),
        },
    }


def send_to_splunk(hec_session: requests.Session, hec_url: str,
                   events: list, dry_run: bool = False) -> bool:
    """Send a batch of HEC events to Splunk. Returns True on success."""
    if dry_run:
        print(f"  [dry-run] Would send {len(events)} events to Splunk.")
        return True

    # HEC batch format: newline-delimited JSON objects
    payload = "\n".join(json.dumps(e) for e in events)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = hec_session.post(
                f"{hec_url}/services/collector/event",
                data=payload,
                timeout=30,
            )
            if resp.status_code == 200:
                return True
            print(f"  WARNING: Splunk HEC returned {resp.status_code}: {resp.text}", file=sys.stderr)
            if resp.status_code < 500:
                # 4xx — don't retry
                return False
        except requests.RequestException as exc:
            print(f"  WARNING: HEC request failed (attempt {attempt}): {exc}", file=sys.stderr)

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_WAIT)

    return False


def flush_batch(hec_session, hec_url, batch, dry_run, stats):
    if not batch:
        return
    ok = send_to_splunk(hec_session, hec_url, batch, dry_run)
    if ok:
        stats["sent"] += len(batch)
    else:
        stats["failed"] += len(batch)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Send GitLab commits to Splunk HEC.")
    parser.add_argument("--since",          default="", help="Only commits after this ISO 8601 date")
    parser.add_argument("--until",          default="", help="Only commits before this ISO 8601 date")
    parser.add_argument("--project-filter", default="", help="Only include projects whose path contains this string")
    parser.add_argument("--dry-run",        action="store_true", help="Fetch data but do NOT send to Splunk")
    args = parser.parse_args()

    # --- credentials --------------------------------------------------------
    gitlab_url   = require_env("GITLAB_URL").rstrip("/")
    gitlab_token = require_env("GITLAB_TOKEN")

    if not args.dry_run:
        hec_url   = require_env("SPLUNK_HEC_URL").rstrip("/")
        hec_token = require_env("SPLUNK_HEC_TOKEN")
    else:
        hec_url = hec_token = ""

    index      = optional_env("SPLUNK_INDEX",      "main")
    source     = optional_env("SPLUNK_SOURCE",     "gitlab:commits")
    sourcetype = optional_env("SPLUNK_SOURCETYPE", "gitlab_commit")

    # --- sessions -----------------------------------------------------------
    gl_session = requests.Session()
    gl_session.headers.update({"PRIVATE-TOKEN": gitlab_token})

    hec_session = requests.Session()
    hec_session.headers.update({
        "Authorization": f"Splunk {hec_token}",
        "Content-Type":  "application/json",
    })

    # --- fetch & send -------------------------------------------------------
    projects = get_projects(gl_session, gitlab_url, args.project_filter)
    start    = datetime.now()
    batch    = []
    stats    = {"sent": 0, "failed": 0, "commits": 0}

    for i, project in enumerate(projects, 1):
        name = project.get("path_with_namespace", project["id"])
        print(f"[{i}/{len(projects)}] {name}", flush=True)

        try:
            commits = get_commits(gl_session, gitlab_url, project, args.since, args.until)
        except Exception as exc:
            print(f"  WARNING: Could not fetch commits: {exc}", file=sys.stderr)
            continue

        print(f"  -> {len(commits)} commit(s)", flush=True)
        stats["commits"] += len(commits)

        for commit in commits:
            event = build_hec_event(commit, project, index, source, sourcetype)
            batch.append(event)

            if len(batch) >= SPLUNK_BATCH_SIZE:
                flush_batch(hec_session, hec_url, batch, args.dry_run, stats)
                batch = []

    # flush remaining events
    flush_batch(hec_session, hec_url, batch, args.dry_run, stats)

    elapsed = datetime.now() - start
    print(f"\n{'='*50}")
    print(f"Done in {elapsed}")
    print(f"  Total commits fetched : {stats['commits']}")
    if not args.dry_run:
        print(f"  Events sent to Splunk : {stats['sent']}")
        print(f"  Events failed         : {stats['failed']}")
    else:
        print("  Dry-run mode — no data was sent to Splunk.")


if __name__ == "__main__":
    main()
