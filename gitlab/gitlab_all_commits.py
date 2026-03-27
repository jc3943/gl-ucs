#!/usr/bin/env python3
"""
Fetch all commits across all branches for all GitLab projects.

Usage:
    export GITLAB_URL=https://gitlab.example.com
    export GITLAB_TOKEN=your_personal_access_token
    python gitlab_all_commits.py [--output commits.csv] [--format csv|json]
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib3
from datetime import datetime

import requests

# Suppress InsecureRequestWarning when SSL verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_PER_PAGE = 100
RETRY_WAIT_SECONDS = 5
MAX_RETRIES = 3


def get_env(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        print(f"ERROR: Environment variable {key} is not set.", file=sys.stderr)
        sys.exit(1)
    return val


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def paginate(session: requests.Session, url: str, params: dict = None) -> list:
    """Yield items from all pages of a GitLab API endpoint."""
    params = dict(params or {})
    params["per_page"] = DEFAULT_PER_PAGE
    params["page"] = 1
    items = []

    while True:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                break
            except requests.RequestException as exc:
                if attempt == MAX_RETRIES:
                    print(f"  WARNING: Failed after {MAX_RETRIES} retries: {exc}", file=sys.stderr)
                    return items
                time.sleep(RETRY_WAIT_SECONDS)

        page_items = resp.json()
        if not page_items:
            break
        items.extend(page_items)

        # GitLab returns x-next-page header; stop when empty
        next_page = resp.headers.get("x-next-page", "")
        if not next_page:
            break
        params["page"] = int(next_page)

    return items


def get_all_projects(session: requests.Session, base_url: str) -> list:
    print("Fetching all projects...", flush=True)
    projects = paginate(session, f"{base_url}/api/v4/projects", {"membership": False, "simple": True})
    print(f"  Found {len(projects)} projects.", flush=True)
    return projects


def get_commits_for_project(session: requests.Session, base_url: str, project: dict) -> list:
    """
    Fetch all commits across all refs for a project.
    The `all=true` param tells GitLab to include commits from every branch/tag.
    """
    project_id = project["id"]
    project_name = project.get("path_with_namespace", str(project_id))

    commits_raw = paginate(
        session,
        f"{base_url}/api/v4/projects/{project_id}/repository/commits",
        {"all": "true", "with_stats": "false"},
    )

    commits = []
    for c in commits_raw:
        commits.append({
            "project_id": project_id,
            "project_name": project_name,
            "commit_id": c.get("id", ""),
            "short_id": c.get("short_id", ""),
            "title": c.get("title", "").replace("\n", " "),
            "author_name": c.get("author_name", ""),
            "author_email": c.get("author_email", ""),
            "authored_date": c.get("authored_date", ""),
            "committer_name": c.get("committer_name", ""),
            "committer_email": c.get("committer_email", ""),
            "committed_date": c.get("committed_date", ""),
            "web_url": c.get("web_url", ""),
        })

    return commits


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

CSV_FIELDS = [
    "project_id", "project_name", "commit_id", "short_id", "title",
    "author_name", "author_email", "authored_date",
    "committer_name", "committer_email", "committed_date", "web_url",
]


def write_csv(all_commits: list, output_path: str) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(all_commits)
    print(f"\nWrote {len(all_commits)} commits to {output_path}")


def write_json(all_commits: list, output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_commits, f, indent=2, default=str)
    print(f"\nWrote {len(all_commits)} commits to {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Export all GitLab commits to CSV or JSON.")
    parser.add_argument("--output", default="gitlab_commits.csv", help="Output file path (default: gitlab_commits.csv)")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Output format (default: csv)")
    parser.add_argument("--project-filter", default="", help="Optional: only include projects whose path contains this string")
    parser.add_argument("--since", default="", help="Optional: only commits after this date (ISO 8601, e.g. 2024-01-01T00:00:00Z)")
    parser.add_argument("--until", default="", help="Optional: only commits before this date (ISO 8601)")
    parser.add_argument("--no-verify", action="store_true", help="Disable SSL certificate verification (useful for self-signed certs)")
    args = parser.parse_args()

    base_url = get_env("GITLAB_URL").rstrip("/")
    token = get_env("GITLAB_TOKEN")

    session = requests.Session()
    session.headers.update({"PRIVATE-TOKEN": token})
    session.verify = not args.no_verify
    if args.no_verify:
        print("WARNING: SSL certificate verification is disabled.", flush=True)

    projects = get_all_projects(session, base_url)

    if args.project_filter:
        projects = [p for p in projects if args.project_filter.lower() in p.get("path_with_namespace", "").lower()]
        print(f"  Filtered to {len(projects)} projects matching '{args.project_filter}'.", flush=True)

    all_commits = []
    start = datetime.now()

    for i, project in enumerate(projects, 1):
        name = project.get("path_with_namespace", project["id"])
        print(f"[{i}/{len(projects)}] {name}", flush=True)

        try:
            commits = get_commits_for_project(session, base_url, project)

            # Apply date filters if specified (the API also accepts these but filtering
            # locally ensures consistent behavior across GitLab versions)
            if args.since:
                commits = [c for c in commits if c["committed_date"] >= args.since]
            if args.until:
                commits = [c for c in commits if c["committed_date"] <= args.until]

            print(f"  -> {len(commits)} commits", flush=True)
            all_commits.extend(commits)
        except Exception as exc:
            print(f"  WARNING: Skipping {name}: {exc}", file=sys.stderr)

    elapsed = datetime.now() - start
    print(f"\nTotal commits collected: {len(all_commits)}")
    print(f"Elapsed: {elapsed}")

    if args.format == "json":
        write_json(all_commits, args.output)
    else:
        write_csv(all_commits, args.output)


if __name__ == "__main__":
    main()
