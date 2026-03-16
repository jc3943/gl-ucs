# Primary Vault Provider
provider "vault" {
  alias   = "primary"
  address = "http://172.16.112.6:8200"
}

# Secondary Vault Provider
provider "vault" {
  alias   = "secondary"
  address = "http://172.0.1.50:8200"
}

# Read from Primary
data "vault_generic_secret" "my_secret" {
  provider = vault.primary
  path     = "intersight/intersight_api"
}

# Write to Secondary
resource "vault_generic_secret" "sync_to_secondary" {
  provider = vault.secondary
  path     = "intersight/intersight_api"
  data_json = data.vault_generic_secret.my_secret.data_json
}

# Read from Primary
data "vault_generic_secret" "my_secret2" {
  provider = vault.primary
  path     = "cimc/cimc-admin"
}

# Write to Secondary
resource "vault_generic_secret" "sync_to_secondary2" {
  provider = vault.secondary
  path     = "cimc/cimc-admin"
  data_json = data.vault_generic_secret.my_secret.data_json
}

# Read from Primary
data "vault_generic_secret" "my_secret3" {
  provider = vault.primary
  path     = "cml/cml-admin"
}

# Write to Secondary
resource "vault_generic_secret" "sync_to_secondary3" {
  provider = vault.secondary
  path     = "cml/cml-admin"
  data_json = data.vault_generic_secret.my_secret.data_json
}