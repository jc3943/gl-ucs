import hvac
import requests
from intersight_auth import IntersightAuth

# Vault & Intersight configuration
VAULT_ADDR = "http://172.0.1.50:8200"   # replace with your Vault address
VAULT_TOKEN = "DEVP@ssw0rd"                   # replace or use environment variable
MOUNT_POINT = "intersight"
SECRET_PATH = "intersight_api"

def get_intersight_credentials():
    """Retrieve Intersight API credentials from HashiCorp Vault KV v2."""
    client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
    
    if not client.is_authenticated():
        raise Exception("Vault authentication failed.")
    
    # KV v2 requires accessing data['data']['data']
    secret = client.secrets.kv.v2.read_secret_version(
        mount_point=MOUNT_POINT,
        path=SECRET_PATH
    )
    
    data = secret['data']['data']
    return {
        'api_key_id': data['api_key_id'],
        'secret_key_string': data['secret_key_string'],
        'target_url': data['target-url']
    }

def get_compute_physical_summaries(creds):
    """Query Intersight ComputePhysicalSummaries endpoint and return results."""
    auth = IntersightAuth(
        secret_key_string=creds['secret_key_string'],
        api_key_id=creds['api_key_id']
    )

    url = f"{creds['target_url'].rstrip('/')}/api/v1/compute/PhysicalSummaries"
    response = requests.get(url, auth=auth, verify=False)
    response.raise_for_status()

    return response.json().get('Results', [])

def main():
    creds = get_intersight_credentials()
    summaries = get_compute_physical_summaries(creds)

    print(f"{'Name':30} {'IPv4':15} {'Moid':40} {'Serial':20} {'Model'}")
    print("=" * 120)
    for item in summaries:
        name = item.get('Name', 'N/A')
        ipv4 = item.get('Ipv4Address', 'N/A')
        moid = item.get('Moid', 'N/A')
        serial = item.get('Serial', 'N/A')
        model = item.get('Model', 'N/A')
        print(f"{name:30} {ipv4:15} {moid:40} {serial:20} {model}")

if __name__ == "__main__":
    main()
