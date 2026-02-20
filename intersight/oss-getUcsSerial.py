#!/usr/bin/env python3
"""
Retrieve the serial number of a Cisco UCS server via the Redfish API.

Usage:
    python get_serial_number.py --ip <CIMC_IP> --user <USERNAME> --password <PASSWORD>

The script performs an HTTPS GET request to the Redfish endpoint on the
CIMC and extracts the "SerialNumber" field from the JSON response.

It disables SSL verification because Cisco's CA certs are usually
self‑signed.  If you have the proper CA certificates installed, you can
remove "verify=False".
"""

import argparse
import json
import sys
import requests
import urllib3

# Disable InsecureRequestWarning when verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REDIS_NAMESPACE = "fabrics"

def get_serial(cimc_ip: str, user: str, password: str) -> str:
    """Return the serial number for the first system on the CIMC.

    Parameters
    ----------
    cimc_ip:
        IP address or hostname of the CIMC.
    user, password:
        Credentials for HTTP basic authentication.
    """
    # Base URL for Redfish on Cisco IMC
    base_url = f"https://{cimc_ip}/redfish/v1"

    # Get the system resource.  Cisco IMC uses 'Systems/1' for the primary
    # server.
    system_url = f"{base_url}/Chassis/1"

    try:
        response = requests.get(
            system_url,
            auth=(user, password),
            verify=False,  # Cisco IMC typically has a self‑signed cert
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Error communicating with CIMC: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        print(f"Failed to parse JSON response: {exc}", file=sys.stderr)
        sys.exit(1)

    serial = data.get("SerialNumber") or data.get("SerialID")
    if not serial:
        print("Serial number not found in the response.", file=sys.stderr)
        sys.exit(1)

    return serial


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Get the serial number of a Cisco UCS server via Redfish."
    )
    parser.add_argument("--ip", required=True, help="IP address or hostname of the CIMC")
    parser.add_argument("--user", required=True, help="Username for CIMC login")
    parser.add_argument("--password", required=True, help="Password for CIMC login")

    args = parser.parse_args()

    serial = get_serial(args.ip, args.user, args.password)
    print(f"Serial Number: {serial}")


if __name__ == "__main__":
    main()
