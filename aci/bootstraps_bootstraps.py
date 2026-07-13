#!/usr/bin/env python3
"""
Bootstrap a Cisco APIC cluster (virtual APIC on ESXi, Layer 2 / directly attached)
for release 6.0(2)+ (tested schema for 6.2.x).
 
Flow (all against APIC 1's OOB IP):
  1. POST /api/workflows/v1/login              -> session token
  2. POST /api/workflows/v1/controller/verify  -> once per node, returns serialNumber
  3. POST /api/workflows/v1/cluster/bootstrap  -> cluster + nodes[] + pods[]
 
Only APIC 1 is targeted; it relays config to the other controllers.
"""
 
import sys
import json
import yaml
import requests
import urllib3
import hvac
import os
 
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
TIMEOUT = 30
 
 
def load_config():
    infile_path = os.environ['varPath']
    path = infile_path + "/aci/cluster_config.yaml"
    with open(path, "r") as fh:
        return yaml.safe_load(fh)
 
 
def login(session, apic1, username, password):
    url = f"https://{apic1}/api/workflows/v1/login"
    body = {"username": username, "password": password, "domain": "DefaultAuth"}
    r = session.post(url, json=body, verify=False, timeout=TIMEOUT)
    r.raise_for_status()
    # Token is returned as an APIC auth cookie on the session; some builds also
    # return it in the body. The cookie on `session` is what subsequent calls use.
    print(f"  login OK ({r.status_code})")
    return r
 
 
def verify_node(session, apic1, node, admin_user, admin_pw):
    """Call verify for a single controller; return its serial number.
    Per-node creds are optional; fall back to the cluster admin creds."""
    url = f"https://{apic1}/api/workflows/v1/controller/verify"
    body = {
        "controllerType": "virtual",
        "username": node.get("username", admin_user),
        "password": node.get("password", admin_pw),
        "address": node["mgmtIp"].split("/")[0],  # VM mgmt (OOB) IP, no mask
    }
    r = session.post(url, json=body, verify=False, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
 
    # The serial is returned in the verify response. Field name has varied across
    # builds ("serialNumber" / "serial"); pull whichever is present.
    serial = _extract_serial(data)
    if not serial:
        raise RuntimeError(
            f"verify for node {node['id']} ({node['name']}) returned no serial:\n"
            f"{json.dumps(data, indent=2)}"
        )
    print(f"  node {node['id']} ({node['name']}) serial = {serial}")
    return serial
 
 
def _extract_serial(data):
    """Best-effort pull of a serial number from the verify response."""
    if isinstance(data, dict):
        for key in ("serialNumber", "serial", "serialNum"):
            if key in data and data[key]:
                return data[key]
        # Sometimes nested under a node/controller object
        for v in data.values():
            found = _extract_serial(v)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _extract_serial(item)
            if found:
                return found
    return None
 
 
def build_bootstrap_payload(config, serials):
    """Assemble the cluster + nodes[] + pods[] body for L2 virtual APIC."""
    fabric = config["cluster"]
 
    nodes = []
    for ctrl in config["controllers"]:
        nodes.append({
            "nodeName": ctrl["name"],
            "controllerType": "virtual",
            "nodeId": int(ctrl["id"]),
            "podId": int(ctrl.get("podId", 1)),
            "serialNumber": serials[ctrl["id"]],
            "oobNetwork": {
                "address4": ctrl["mgmtIp"],        # WITH mask, e.g. 172.0.1.136/24
                "gateway4": ctrl["mgmtGateway"],
                "enableIPv4": True,
            },
        })
 
    payload = {
        "cluster": {
            "fabricName": fabric["fabricName"],
            "fabricId": int(fabric["fabricId"]),
            "clusterSize": int(fabric["clusterSize"]),
            "layer3": False,                        # directly attached (L2)
            "gipoPool": fabric["gipoPool"],
            "adminPassword": fabric["adminPassword"],
            "infraVlan": int(fabric["infraVlan"]),
        },
        "nodes": nodes,
        "pods": _build_pods(config),
    }
    return payload
 
 
def _build_pods(config):
    """Support either an explicit multi-pod `pods:` list, or a single-pod
    fabric where tepPool lives at the cluster level."""
    if config.get("pods"):
        return [
            {"podId": int(p["podId"]), "tepPool": p["tepPool"]}
            for p in config["pods"]
        ]
    # single-pod fallback: cluster.tepPool
    return [{"podId": 1, "tepPool": config["cluster"]["tepPool"]}]
 
 
def bootstrap(session, apic1, payload):
    url = f"https://{apic1}/api/workflows/v1/cluster/bootstrap"
    r = session.post(url, json=payload, verify=False, timeout=TIMEOUT)
    if r.status_code in (200, 201):
        print(f"\nSuccess! APIC 1 accepted the bootstrap ({r.status_code}).")
        print("Cluster formation begins now; the fabric UI/API typically takes "
              "10-15 minutes to become fully active.")
    else:
        print(f"\nBootstrap failed: HTTP {r.status_code}")
        print(r.text)
        r.raise_for_status()
 
 
def main():
    config = load_config()
    apic1 = config["controllers"][0]["mgmtIp"].split("/")[0]

    #export VAULT_ADDR='ip address for vault'
    #export VAULT_TOKEN='vault access token'

    #get credentials from vault for ACI Basic Auth
    client = hvac.Client(verify=False)
    admin_user = client.secrets.kv.v2.read_secret_version(mount_point='aci', path="sandbox").get("data").get("data").get("username")
    admin_pw = client.secrets.kv.v2.read_secret_version(mount_point='aci', path="sandbox").get("data").get("data").get("password")
 
    session = requests.Session()
 
    print(f"[1/3] Logging in to APIC 1 ({apic1}) ...")
    login(session, apic1, admin_user, admin_pw)
 
    print(f"[2/3] Verifying {len(config['controllers'])} controllers ...")
    serials = {}
    for ctrl in config["controllers"]:
        serials[ctrl["id"]] = verify_node(session, apic1, ctrl, admin_user, admin_pw)
 
    print("[3/3] Posting cluster bootstrap ...")
    payload = build_bootstrap_payload(config, serials)
    bootstrap(session, apic1, payload)
 
 
if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.RequestException as e:
        print(f"\nHTTP error talking to APIC: {e}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, RuntimeError) as e:
        print(f"\nConfig/response error: {e}", file=sys.stderr)
        sys.exit(1)