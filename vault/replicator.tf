terraform {
  required_providers {
    vault = {
      source  = "hashicorp/vault"
      version = "~> 4.0"
    }
    external = {
      source  = "hashicorp/external"
      version = "~> 2.0"
    }
  }
}

provider "vault" {
  alias   = "primary"
  address = "http://172.0.1.10:8200"
}

provider "vault" {
  alias   = "secondary"
  #address = "http://172.16.112.6:8200"
  #address = "http://172.0.1.50:8200"
  address = "http://192.168.40.116:8200"
}

# Dynamically list all secrets from the primary Vault
data "external" "vault_secrets" {
  program = ["python3", "/workspaces/gl-ucs/vault/list_vault_secrets.py"]

  query = {
    vault_addr  = "http://172.0.1.10:8200"
  }
}

locals {
  secret_paths = toset(jsondecode(data.external.vault_secrets.result.paths))
  # Derive unique mount names from the discovered secret paths
  mount_names  = toset([for path in local.secret_paths : split("/", path)[0]])
}

# Create KV v2 secret engines on Secondary
resource "vault_mount" "kv_mounts" {
  for_each = local.mount_names
  provider = vault.secondary
  path     = each.value
  type     = "kv"
  options  = { version = "2" }
}

# Read all discovered secrets from Primary
data "vault_kv_secret_v2" "secrets" {
  for_each = local.secret_paths
  provider = vault.primary
  mount    = split("/", each.value)[0]
  name     = join("/", slice(split("/", each.value), 1, length(split("/", each.value))))
}

# Write all secrets to Secondary — depends_on ensures mounts exist first
resource "vault_kv_secret_v2" "sync_to_secondary" {
  for_each  = local.secret_paths
  provider  = vault.secondary
  mount     = split("/", each.value)[0]
  name      = join("/", slice(split("/", each.value), 1, length(split("/", each.value))))
  data_json = data.vault_kv_secret_v2.secrets[each.value].data_json

  depends_on = [vault_mount.kv_mounts]
}