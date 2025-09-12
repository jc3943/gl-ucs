#Authored: Jeff Comer
data "vault_generic_secret" "intersight" {
  path = "intersight/intersight_api"
}

terraform {
  required_providers {
    intersight = {
      source = "CiscoDevNet/intersight"
    }
  }
}

provider "vault" {}

provider "intersight" {
#   apikey = var.api_key
#   secretkey = var.api_key_file
#   endpoint = var.api_endpoint
  apikey = data.vault_generic_secret.intersight.data["api_key_id"]
  secretkey = data.vault_generic_secret.intersight.data["secret_key_string"]
  endpoint = data.vault_generic_secret.intersight.data["target-url"]
  
}