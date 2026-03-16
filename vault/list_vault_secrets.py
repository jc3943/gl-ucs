#!/usr/bin/env python3
import json
import os
import sys
import urllib.request
import urllib.error


def list_secrets_recursive_v1(vault_addr, token, mount, prefix=""):
    list_path = f"{mount}/{prefix}" if prefix else mount
    url = f"{vault_addr}/v1/{list_path}"
    req = urllib.request.Request(url, method="LIST")
    req.add_header("X-Vault-Token", token)
    try:
        with urllib.request.urlopen(req) as resp:
            keys = json.loads(resp.read()).get("data", {}).get("keys", [])
    except urllib.error.HTTPError:
        return []
    paths = []
    for key in keys:
        full_prefix = f"{prefix}{key}"
        if key.endswith("/"):
            paths.extend(list_secrets_recursive_v1(vault_addr, token, mount, full_prefix))
        else:
            paths.append(f"{mount}/{full_prefix}")
    return paths


def list_secrets_recursive_v2(vault_addr, token, mount, prefix=""):
    list_path = f"{mount}/metadata/{prefix}" if prefix else f"{mount}/metadata"
    url = f"{vault_addr}/v1/{list_path}"
    req = urllib.request.Request(url, method="LIST")
    req.add_header("X-Vault-Token", token)
    try:
        with urllib.request.urlopen(req) as resp:
            keys = json.loads(resp.read()).get("data", {}).get("keys", [])
    except urllib.error.HTTPError:
        return []
    paths = []
    for key in keys:
        full_prefix = f"{prefix}{key}"
        if key.endswith("/"):
            paths.extend(list_secrets_recursive_v2(vault_addr, token, mount, full_prefix))
        else:
            paths.append(f"{mount}/{full_prefix}")
    return paths


def get_kv_mounts(vault_addr, token):
    url = f"{vault_addr}/v1/sys/mounts"
    req = urllib.request.Request(url)
    req.add_header("X-Vault-Token", token)
    with urllib.request.urlopen(req) as resp:
        mounts = json.loads(resp.read())
    kv_mounts = []
    for mount_path, info in mounts.items():
        if not isinstance(info, dict):
            continue
        if info.get("type") == "kv":
            options = info.get("options") or {}
            version = options.get("version", "1")
            kv_mounts.append({"path": mount_path.rstrip("/"), "version": version})
    return kv_mounts


def main():
    query = json.loads(sys.stdin.read())
    vault_addr = query["vault_addr"].rstrip("/")

    token = os.environ.get("VAULT_TOKEN")
    if not token:
        print(json.dumps({"error": "VAULT_TOKEN environment variable is not set"}), file=sys.stderr)
        sys.exit(1)

    all_paths = []
    for mount in get_kv_mounts(vault_addr, token):
        if mount["version"] == "2":
            all_paths.extend(list_secrets_recursive_v2(vault_addr, token, mount["path"]))
        else:
            all_paths.extend(list_secrets_recursive_v1(vault_addr, token, mount["path"]))

    print(json.dumps({"paths": json.dumps(all_paths)}))


if __name__ == "__main__":
    main()

