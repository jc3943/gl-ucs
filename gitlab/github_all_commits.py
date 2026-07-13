#!/usr/bin/env python3
"""
Fetch all commits across all branches for all GitHub repositories.

Usage:
    export GITHUB_TOKEN=your_classic_personal_access_token
    export GITHUB_URL=https://api.github.com   # optional; override for GitHub Enterprise
    export GITHUB_ORG=my-org                   # optional; scope to an organization
    python github_all_commits.py [--output commits.csv] [--format csv|json]
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime

import requests

DEFAULT_PER_PAGE = 100
RETRY_WAIT_SECONDS = 5
MAX_RETRIES = 3


def get_env(key: str, required: bool = True) -> str:
    val = os.environ.get(key, "").strip()
    if not val and required:
        print(f"ERROR: Environment variable {key} is not set.", file=sys.stderr)
        sys.exit(1)
    return val


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _parse_link_header(header: str) -> dict:
    """Parse GitHub's Link header into {rel: url}."""
    links = {}
    for part in header.split(","):
        segments = part.strip().split(";")
        if len(segments) < 2:
            continue
        url = segments[0].strip().strip("<>")
        rel = segments[1].strip()
        if rel.startswith('rel="') and rel.endswith('"'):
            links[rel[5:-1]] = url
    return links


def api_get(session: requests.Session, url: str, params: dict = None) -> requests.Response:
    """GET with retry and GitHub rate-limit handling."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=30)
            if resp.status_code in (403, 429) and int(resp.headers.get("X-RateLimit-Remaining", 1)) == 0:
                reset_ts = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(reset_ts - int(time.time()), 1)
                print(f"  Rate limit hit, waiting {wait}s...", flush=True)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                raise
            print(f"  Retry {attempt}/{MAX_RETRIES}: {exc}", file=sys.stderr)
            time.sleep(RETRY_WAIT_SECONDS)


def paginate(session: requests.Session, url: str, params: dict = None) -> list:
    """Collect all pages from a GitHub API list endpoint via Link headers."""
    params = dict(params or {})
    params.setdefault("per_page", DEFAULT_PER_PAGE)
    items = []
    next_url = url

    while next_url:
        try:
            resp = api_get(session, next_url, params=params)
        except requests.RequestException as exc:
            print(f"  WARNING: Giving up on {next_url}: {exc}", file=sys.stderr)
            break

        page_items = resp.json()
        if not isinstance(page_items, list) or not page_items:
            break
        items.extend(page_items)

        params = {}  # next URL already encodes all params
        next_url = _parse_link_header(resp.headers.get("Link", "")).get("next", "")

    return items


def get_all_repos(session: requests.Session, base_url: str, org: str) -> list:
    if org:
        print(f"Fetching repos for org '{org}'...", flush=True)
        url = f"{base_url}/orgs/{org}/repos"
        params = {"type": "all"}
    else:
        print("Fetching repos for authenticated user...", flush=True)
        url = f"{base_url}/user/repos"
        params = {"affiliation": "owner,collaborator,organization_member"}

    repos = paginate(session, url, params)
    print(f"  Found {len(repos)} repositories.", flush=True)
    return repos


def get_commits_for_repo(
    session: requests.Session,
    base_url: str,
    repo: dict,
    since: str,
    until: str,
) -> list:
    """
    Fetch all unique commits across every branch for a repo.
    GitHub has no 'all branches' shortcut, so we enumerate branches and
    deduplicate by SHA.
    """
    repo_id = repo["id"]
    repo_full_name = repo["full_name"]

    branches = paginate(session, f"{base_url}/repos/{repo_full_name}/branches")
    branch_names = [b["name"] for b in branches] or ["HEAD"]

    seen_shas: set = set()
    commits = []

    for branch in branch_names:
        params: dict = {"sha": branch}
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        branch_commits = paginate(
            session,
            f"{base_url}/repos/{repo_full_name}/commits",
            params,
        )

        for c in branch_commits:
            sha = c.get("sha", "")
            if not sha or sha in seen_shas:
                continue
            seen_shas.add(sha)

            cd = c.get("commit", {})
            author = cd.get("author") or {}
            committer = cd.get("committer") or {}
            title = (cd.get("message") or "").splitlines()[0]

            commits.append({
                "repo_id":        repo_id,
                "repo_name":      repo_full_name,
                "commit_id":      sha,
                "short_id":       sha[:8],
                "title":          title,
                "author_name":    author.get("name", ""),
                "author_email":   author.get("email", ""),
                "authored_date":  author.get("date", ""),
                "committer_name":  committer.get("name", ""),
                "committer_email": committer.get("email", ""),
                "committed_date":  committer.get("date", ""),
                "web_url":         c.get("html_url", ""),
            })

    return commits


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

CSV_FIELDS = [
    "repo_id", "repo_name", "commit_id", "short_id", "title",
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
    parser = argparse.ArgumentParser(description="Export all GitHub commits to CSV or JSON.")
    parser.add_argument("--output", default="github_commits.csv",
                        help="Output file path (default: github_commits.csv)")
    parser.add_argument("--format", choices=["csv", "json"], default="csv",
                        help="Output format (default: csv)")
    parser.add_argument("--org", default="",
                        help="GitHub org name (overrides GITHUB_ORG env var)")
    parser.add_argument("--repo-filter", default="",
                        help="Only include repos whose full name contains this string")
    parser.add_argument("--since", default="",
                        help="Only commits after this date (ISO 8601, e.g. 2024-01-01T00:00:00Z)")
    parser.add_argument("--until", default="",
                        help="Only commits before this date (ISO 8601)")
    args = parser.parse_args()

    token    = get_env("GITHUB_TOKEN")
    base_url = (get_env("GITHUB_URL", required=False) or "https://api.github.com").rstrip("/")
    org      = args.org or get_env("GITHUB_ORG", required=False)

    session = requests.Session()
    session.headers.update({
        "Authorization":        f"Bearer {token}",
        "Accept":               "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })

    repos = get_all_repos(session, base_url, org)

    if args.repo_filter:
        repos = [r for r in repos if args.repo_filter.lower() in r.get("full_name", "").lower()]
        print(f"  Filtered to {len(repos)} repos matching '{args.repo_filter}'.", flush=True)

    all_commits = []
    start = datetime.now()

    for i, repo in enumerate(repos, 1):
        name = repo.get("full_name", str(repo["id"]))
        print(f"[{i}/{len(repos)}] {name}", flush=True)
        try:
            commits = get_commits_for_repo(session, base_url, repo, args.since, args.until)
            print(f"  -> {len(commits)} unique commits", flush=True)
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
