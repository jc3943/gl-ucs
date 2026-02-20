#!/usr/bin/env python3
"""
Pulls Cisco Intersight server PhysicalSummaries using credentials from HashiCorp Vault KV v2.

Vault:
  mount_point = "intersight"
  path = "intersight_api"
  keys = api_key_id, secret_key_string, target-url

Requirements:
  pip install hvac requests intersight_auth
"""

import os
import hvac
import requests
from intersight_auth import IntersightAuth  # Cisco-provided signing class

VAULT_MOUNT = "intersight"
VAULT_PATH = "intersight_api"
#AI had the incorrect api endpoint
INTERSIGHT_ENDPOINT = "/api/v1/compute/PhysicalSummaries?$inlinecount=allpages"


def get_vault_client() -> hvac.Client:
    """Authenticate to Vault using VAULT_ADDR and VAULT_TOKEN."""
    vault_addr = os.environ.get("VAULT_ADDR")
    vault_token = os.environ.get("VAULT_TOKEN")

    if not vault_addr or not vault_token:
        raise EnvironmentError("Please set VAULT_ADDR and VAULT_TOKEN environment variables.")

    client = hvac.Client(url=vault_addr, token=vault_token)
    if not client.is_authenticated():
        raise PermissionError("Vault authentication failed. Check your token.")

    return client


def read_intersight_creds(client: hvac.Client):
    """Read Intersight credentials from Vault KV v2."""
    resp = client.secrets.kv.v2.read_secret_version(path=VAULT_PATH, mount_point=VAULT_MOUNT)
    data = resp["data"]["data"]

    required = ["api_key_id", "secret_key_string", "target-url"]
    missing = [k for k in required if k not in data]
    if missing:
        raise KeyError(f"Missing keys in Vault secret: {missing}")
    print(data["api_key_id"])

    return {
        "api_key_id": data["api_key_id"],
        "secret_key_string": data["secret_key_string"],
        "target_url": data["target-url"].rstrip("/")
    }


def get_physical_summaries(api_key_id: str, private_key_str: str, target_url: str, verify_ssl: bool = False):
    """
    Query Cisco Intersight for server PhysicalSummaries using raw requests + IntersightAuth.
    No PEM file written; the private key is held in memory.
    """
    url = f"{target_url}{INTERSIGHT_ENDPOINT}"

    # Initialize the IntersightAuth object — it accepts the private key as a string
    # From AI, had to change from priviate_key to secret_key_string for auth
    auth = IntersightAuth(api_key_id=api_key_id, secret_key_string=private_key_str)

    # Perform GET request
    response = requests.get(
        url,
        auth=auth,
        headers={"Accept": "application/json"},
        verify=verify_ssl,
        timeout=30
    )

    # Raise if API error
    response.raise_for_status()
    return response.json()


def main():
    print("Connecting to Vault...")
    client = get_vault_client()

    print(f"Reading Intersight credentials from {VAULT_MOUNT}/{VAULT_PATH} ...")
    creds = read_intersight_creds(client)

    print(f"Querying Intersight at {creds['target_url']} ...")
    data = get_physical_summaries(
        api_key_id=creds["api_key_id"],
        private_key_str=creds["secret_key_string"],
        target_url=creds["target_url"],
        verify_ssl=False  # WARNING: disable TLS verification only for testing!
    )

    print("=== Physical Summaries ===")
    for server in data.get("Results", data):
        # Added Serial
        print(f"- {server.get('Name', 'Unnamed')} ({server.get('Moid')}) ({server.get('Serial')})")


if __name__ == "__main__":
    main()

