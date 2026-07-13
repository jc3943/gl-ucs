#!/usr/bin/env python3
"""
vcs_commits_to_splunk.py
========================
Collect commits from GitLab (self-hosted) AND GitHub (cloud or Enterprise),
normalise them into a unified schema, and ship every event to Splunk via
HTTP Event Collector (HEC).

Designed to power a Splunk "Commits per Project per User over Time" app.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Required environment variables
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Splunk (always required unless --dry-run):
  SPLUNK_HEC_URL          https://splunk.example.com:8088
  SPLUNK_HEC_TOKEN        Splunk HEC token

GitLab (required when --sources includes 'gitlab'):
  GITLAB_URL              https://gitlab.example.com
  GITLAB_TOKEN            Admin personal access token

GitHub (required when --sources includes 'github'):
  GITHUB_TOKEN            Personal access token (or fine-grained PAT)
  GITHUB_URL              Base URL  [default: https://api.github.com]
                          For GitHub Enterprise: https://github.example.com/api/v3
  GITHUB_ORGS             Comma-separated org names to scan.
                          Leave blank to scan all repos visible to the token.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Optional environment variables
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SPLUNK_INDEX            [default: main]
  SPLUNK_SOURCE           [default: vcs:commits]
  SPLUNK_SOURCETYPE       [default: vcs_commit]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Usage examples
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # Both sources, last 30 days
  python vcs_commits_to_splunk.py

  # GitLab only
  python vcs_commits_to_splunk.py --sources gitlab

  # GitHub only, last 7 days, test without sending
  python vcs_commits_to_splunk.py --sources github --since 2024-01-01T00:00:00Z --dry-run

  # Filter to a specific project name substring
  python vcs_commits_to_splunk.py --project-filter "payments"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Generator, Iterator

import requests
import urllib3

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

PER_PAGE        = 100
SPLUNK_BATCH    = 500       # HEC events per POST
MAX_RETRIES     = 3
RETRY_WAIT      = 5         # seconds between retries
GH_RATE_PAUSE   = 10        # seconds to sleep when GitHub rate-limit is near
GH_RATE_BUFFER  = 50        # requests to keep in reserve


# ─────────────────────────────────────────────────────────────────────────────
# Unified commit event (normalised across GitLab & GitHub)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CommitEvent:
    source_platform:  str   # "gitlab" | "github"
    project_id:       str
    project_name:     str   # owner/repo  or  group/project
    project_namespace:str
    project_url:      str
    commit_id:        str
    short_id:         str
    title:            str
    author_name:      str
    author_email:     str
    authored_date:    str   # ISO 8601
    committer_name:   str
    committer_email:  str
    committed_date:   str   # ISO 8601
    web_url:          str


# ─────────────────────────────────────────────────────────────────────────────
# Environment helpers
# ─────────────────────────────────────────────────────────────────────────────

def require_env(key: str) -> str:
    v = os.environ.get(key, "").strip()
    if not v:
        print(f"ERROR: environment variable '{key}' is not set.", file=sys.stderr)
        sys.exit(1)
    return v

def optional_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip() or default


# ─────────────────────────────────────────────────────────────────────────────
# Generic HTTP helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_with_retry(session: requests.Session, url: str,
                    params: dict | None = None) -> requests.Response | None:
    """GET with exponential-ish retry on 5xx / network errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=30)
            if resp.status_code < 500:
                if not resp.ok:
                    print(f"  WARN: HTTP {resp.status_code} on {url}: {resp.text[:300]}", file=sys.stderr)
                return resp
            print(f"  WARN: {resp.status_code} on {url} (attempt {attempt})", file=sys.stderr)
        except requests.RequestException as exc:
            print(f"  WARN: request error on {url} (attempt {attempt}): {exc}", file=sys.stderr)
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_WAIT * attempt)
    return None


def iso_to_epoch(iso: str) -> float:
    """ISO 8601 → Unix timestamp float, fallback to now."""
    if not iso:
        return time.time()
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return time.time()


# ─────────────────────────────────────────────────────────────────────────────
# GitLab client
# ─────────────────────────────────────────────────────────────────────────────

class GitLabClient:
    def __init__(self, base_url: str, token: str, verify_ssl: bool = True):
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"PRIVATE-TOKEN": token})
        self.session.verify = verify_ssl

    def _paginate(self, path: str, params: dict | None = None) -> list:
        url    = f"{self.base}/api/v4/{path.lstrip('/')}"
        params = dict(params or {})
        params.update({"per_page": PER_PAGE, "page": 1})
        results = []
        while True:
            resp = _get_with_retry(self.session, url, params)
            if resp is None or not resp.ok:
                break
            data = resp.json()
            if not data:
                break
            results.extend(data)
            next_page = resp.headers.get("x-next-page", "")
            if not next_page:
                break
            params["page"] = int(next_page)
        return results

    def projects(self, project_filter: str = "") -> list[dict]:
        projects = self._paginate("projects", {"membership": False, "simple": True})
        if project_filter:
            projects = [p for p in projects
                        if project_filter.lower() in
                        p.get("path_with_namespace", "").lower()]
        return projects

    def commits(self, project_id: int, since: str = "", until: str = "") -> list[dict]:
        params: dict = {"all": "true", "with_stats": "false"}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        return self._paginate(f"projects/{project_id}/repository/commits", params)

    def iter_commit_events(self, project_filter: str = "",
                           since: str = "", until: str = "") -> Iterator[CommitEvent]:
        projects = self.projects(project_filter)
        print(f"  [GitLab] {len(projects)} project(s) found.", flush=True)
        for i, proj in enumerate(projects, 1):
            name = proj.get("path_with_namespace", str(proj["id"]))
            print(f"  [GitLab] [{i}/{len(projects)}] {name}", flush=True)
            ns_obj   = proj.get("namespace") or {}
            ns       = ns_obj.get("full_path", "") if isinstance(ns_obj, dict) else ""
            proj_url = proj.get("web_url", "")
            try:
                raw_commits = self.commits(proj["id"], since, until)
            except Exception as exc:
                print(f"    WARN: could not fetch commits: {exc}", file=sys.stderr)
                continue
            print(f"    -> {len(raw_commits)} commit(s)", flush=True)
            for c in raw_commits:
                yield CommitEvent(
                    source_platform   = "gitlab",
                    project_id        = str(proj["id"]),
                    project_name      = name,
                    project_namespace = ns,
                    project_url       = proj_url,
                    commit_id         = c.get("id", ""),
                    short_id          = c.get("short_id", ""),
                    title             = c.get("title", "").replace("\n", " "),
                    author_name       = c.get("author_name", ""),
                    author_email      = c.get("author_email", ""),
                    authored_date     = c.get("authored_date", ""),
                    committer_name    = c.get("committer_name", ""),
                    committer_email   = c.get("committer_email", ""),
                    committed_date    = c.get("committed_date", ""),
                    web_url           = c.get("web_url", ""),
                )


# ─────────────────────────────────────────────────────────────────────────────
# GitHub client
# ─────────────────────────────────────────────────────────────────────────────

class GitHubClient:
    def __init__(self, base_url: str, token: str, orgs: list[str]):
        self.base = base_url.rstrip("/")
        self.orgs = orgs
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization":        f"Bearer {token}",
            "Accept":               "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    # ── rate-limit guard ───────────────────────────────────────────────────

    def _check_rate_limit(self, resp: requests.Response) -> None:
        remaining = int(resp.headers.get("X-RateLimit-Remaining", 9999))
        if remaining < GH_RATE_BUFFER:
            reset_at  = int(resp.headers.get("X-RateLimit-Reset", time.time()))
            wait      = max(0, reset_at - int(time.time())) + 2
            print(f"  [GitHub] Rate limit low ({remaining} left). "
                  f"Sleeping {wait}s …", flush=True)
            time.sleep(wait)

    # ── generic paginator ─────────────────────────────────────────────────

    def _paginate(self, path: str, params: dict | None = None) -> list:
        url    = f"{self.base}/{path.lstrip('/')}"
        params = dict(params or {})
        params["per_page"] = PER_PAGE
        results = []
        while url:
            resp = _get_with_retry(self.session, url, params)
            if resp is None or not resp.ok:
                break
            self._check_rate_limit(resp)
            results.extend(resp.json())
            # Follow GitHub's Link: <url>; rel="next" header
            url    = self._next_link(resp.headers.get("Link", ""))
            params = {}         # params already encoded in the next URL
        return results

    @staticmethod
    def _next_link(link_header: str) -> str:
        """Extract the 'next' URL from a GitHub Link header."""
        for part in link_header.split(","):
            part = part.strip()
            m = re.match(r'<([^>]+)>;\s*rel="next"', part)
            if m:
                return m.group(1)
        return ""

    # ── repos ─────────────────────────────────────────────────────────────

    def repos(self, project_filter: str = "") -> list[dict]:
        all_repos: list[dict] = []
        if self.orgs:
            for org in self.orgs:
                print(f"  [GitHub] Fetching repos for org: {org}", flush=True)
                repos = self._paginate(f"orgs/{org}/repos", {"type": "all"})
                all_repos.extend(repos)
        else:
            # Fetch every repo the token can see
            print("  [GitHub] Fetching all accessible repos (user + orgs)…", flush=True)
            all_repos = self._paginate("user/repos", {
                "affiliation": "owner,collaborator,organization_member",
            })

        if project_filter:
            all_repos = [r for r in all_repos
                         if project_filter.lower() in r.get("full_name", "").lower()]
        return all_repos

    # ── branches ──────────────────────────────────────────────────────────

    def branches(self, full_name: str) -> list[str]:
        raw = self._paginate(f"repos/{full_name}/branches")
        return [b["name"] for b in raw if "name" in b]

    # ── commits per branch ────────────────────────────────────────────────

    def commits_on_branch(self, full_name: str, branch: str,
                          since: str = "", until: str = "") -> list[dict]:
        params: dict = {"sha": branch}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        return self._paginate(f"repos/{full_name}/commits", params)

    # ── main iterator ─────────────────────────────────────────────────────

    def iter_commit_events(self, project_filter: str = "",
                           since: str = "", until: str = "") -> Iterator[CommitEvent]:
        repos = self.repos(project_filter)
        print(f"  [GitHub] {len(repos)} repo(s) found.", flush=True)

        for i, repo in enumerate(repos, 1):
            full_name = repo.get("full_name", "")
            owner     = repo.get("owner", {}).get("login", "")
            html_url  = repo.get("html_url", "")
            repo_id   = str(repo.get("id", ""))
            print(f"  [GitHub] [{i}/{len(repos)}] {full_name}", flush=True)

            try:
                branch_names = self.branches(full_name)
            except Exception as exc:
                print(f"    WARN: could not list branches: {exc}", file=sys.stderr)
                continue

            seen_shas: set[str] = set()   # deduplicate commits shared across branches

            for branch in branch_names:
                try:
                    raw = self.commits_on_branch(full_name, branch, since, until)
                except Exception as exc:
                    print(f"    WARN: branch '{branch}': {exc}", file=sys.stderr)
                    continue

                for c in raw:
                    sha = c.get("sha", "")
                    if sha in seen_shas:
                        continue
                    seen_shas.add(sha)

                    commit_obj  = c.get("commit", {})
                    author_obj  = commit_obj.get("author")  or {}
                    cmtr_obj    = commit_obj.get("committer") or {}
                    gh_author   = c.get("author")  or {}
                    gh_cmtr     = c.get("committer") or {}

                    # prefer verified name/email from commit object; fall back to
                    # the GitHub user login if the git identity is a no-reply address
                    author_name  = author_obj.get("name", "")  or gh_author.get("login", "")
                    author_email = author_obj.get("email", "") or ""
                    cmtr_name    = cmtr_obj.get("name", "")    or gh_cmtr.get("login", "")
                    cmtr_email   = cmtr_obj.get("email", "")   or ""
                    title_raw    = commit_obj.get("message", "")
                    title        = title_raw.split("\n")[0].strip()

                    yield CommitEvent(
                        source_platform   = "github",
                        project_id        = repo_id,
                        project_name      = full_name,
                        project_namespace = owner,
                        project_url       = html_url,
                        commit_id         = sha,
                        short_id          = sha[:8],
                        title             = title,
                        author_name       = author_name,
                        author_email      = author_email,
                        authored_date     = author_obj.get("date", ""),
                        committer_name    = cmtr_name,
                        committer_email   = cmtr_email,
                        committed_date    = cmtr_obj.get("date", ""),
                        web_url           = c.get("html_url", ""),
                    )

            print(f"    -> {len(seen_shas)} unique commit(s)", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# Splunk HEC client
# ─────────────────────────────────────────────────────────────────────────────

class SplunkHECClient:
    def __init__(self, hec_url: str, token: str,
                 index: str, source: str, sourcetype: str,
                 dry_run: bool = False, verify_ssl: bool = True):
        self.url        = hec_url.rstrip("/") + "/services/collector/event"
        self.index      = index
        self.source     = source
        self.sourcetype = sourcetype
        self.dry_run    = dry_run
        self.session    = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({
            "Authorization": f"Splunk {token}",
            "Content-Type":  "application/json",
        })
        self.sent   = 0
        self.failed = 0

    def _build_hec_event(self, evt: CommitEvent) -> dict:
        epoch = iso_to_epoch(evt.committed_date or evt.authored_date)
        return {
            "time":       epoch,
            "host":       evt.source_platform,
            "source":     self.source,
            "sourcetype": self.sourcetype,
            "index":      self.index,
            "event":      asdict(evt),
        }

    def _post_batch(self, batch: list[dict]) -> bool:
        if self.dry_run:
            print(f"  [Splunk] dry-run: would send {len(batch)} events.")
            return True
        payload = "\n".join(json.dumps(e) for e in batch)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.post(self.url, data=payload, timeout=30)
                if resp.status_code == 200:
                    return True
                print(f"  WARN: HEC {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
                if resp.status_code < 500:
                    return False
            except requests.RequestException as exc:
                print(f"  WARN: HEC request failed (attempt {attempt}): {exc}", file=sys.stderr)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT)
        return False

    def send_events(self, events: Iterator[CommitEvent]) -> dict:
        """Stream CommitEvents into Splunk in batches. Returns stats dict."""
        batch: list[dict] = []
        total = 0
        for evt in events:
            total += 1
            batch.append(self._build_hec_event(evt))
            if len(batch) >= SPLUNK_BATCH:
                ok = self._post_batch(batch)
                if ok:
                    self.sent += len(batch)
                else:
                    self.failed += len(batch)
                batch = []

        if batch:                          # flush remainder
            ok = self._post_batch(batch)
            if ok:
                self.sent += len(batch)
            else:
                self.failed += len(batch)

        return {"total": total, "sent": self.sent, "failed": self.failed}


# ─────────────────────────────────────────────────────────────────────────────
# Event multiplexer — merge iterators from multiple sources
# ─────────────────────────────────────────────────────────────────────────────

def merged_events(*iterators: Iterator[CommitEvent]) -> Iterator[CommitEvent]:
    for it in iterators:
        yield from it


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ship GitLab + GitHub commits to Splunk HEC.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--sources",
        default="gitlab,github",
        help="Comma-separated list of sources to collect from: gitlab, github  [default: gitlab,github]",
    )
    parser.add_argument("--since",          default="",
                        help="Only commits after  this ISO 8601 date, e.g. 2024-01-01T00:00:00Z")
    parser.add_argument("--until",          default="",
                        help="Only commits before this ISO 8601 date")
    parser.add_argument("--project-filter", default="",
                        help="Only include projects whose full name contains this substring")
    parser.add_argument("--dry-run",        action="store_true",
                        help="Fetch data but do NOT send to Splunk")
    parser.add_argument("--no-verify",      action="store_true",
                        help="Disable SSL certificate verification (for self-signed certs)")
    args = parser.parse_args()

    if args.no_verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("WARNING: SSL certificate verification is disabled.", flush=True)

    sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()]

    # ── Splunk ──────────────────────────────────────────────────────────────
    if args.dry_run:
        hec_url = hec_token = "dry-run"
    else:
        hec_url   = require_env("SPLUNK_HEC_URL")
        hec_token = require_env("SPLUNK_HEC_TOKEN")

    splunk = SplunkHECClient(
        hec_url        = hec_url,
        token          = hec_token,
        index          = optional_env("SPLUNK_INDEX",      "main"),
        source         = optional_env("SPLUNK_SOURCE",     "vcs:commits"),
        sourcetype     = optional_env("SPLUNK_SOURCETYPE", "vcs_commit"),
        dry_run        = args.dry_run,
        verify_ssl     = not args.no_verify,
    )

    # ── Source iterators ────────────────────────────────────────────────────
    iterators: list[Iterator[CommitEvent]] = []

    if "gitlab" in sources:
        print("\n── GitLab ─────────────────────────────────────────────", flush=True)
        gl = GitLabClient(
            base_url   = require_env("GITLAB_URL"),
            token      = require_env("GITLAB_TOKEN"),
            verify_ssl = not args.no_verify,
        )
        iterators.append(
            gl.iter_commit_events(args.project_filter, args.since, args.until)
        )

    if "github" in sources:
        print("\n── GitHub ─────────────────────────────────────────────", flush=True)
        orgs_raw = optional_env("GITHUB_ORGS", "")
        orgs     = [o.strip() for o in orgs_raw.split(",") if o.strip()]
        gh = GitHubClient(
            base_url = optional_env("GITHUB_URL", "https://api.github.com"),
            token    = require_env("GITHUB_TOKEN"),
            orgs     = orgs,
        )
        iterators.append(
            gh.iter_commit_events(args.project_filter, args.since, args.until)
        )

    # ── Stream everything to Splunk ─────────────────────────────────────────
    print("\n── Sending to Splunk ──────────────────────────────────", flush=True)
    start = datetime.now()
    stats = splunk.send_events(merged_events(*iterators))
    elapsed = datetime.now() - start

    # ── Summary ─────────────────────────────────────────────────────────────
    print(f"\n{'═' * 52}")
    print(f"  Finished in : {elapsed}")
    print(f"  Total events: {stats['total']}")
    if not args.dry_run:
        print(f"  Sent        : {stats['sent']}")
        print(f"  Failed      : {stats['failed']}")
    else:
        print("  Mode        : dry-run (nothing sent)")
    print(f"{'═' * 52}")


if __name__ == "__main__":
    main()
