#Authored: Jeff Comer
 data "vault_generic_secret" "os" {
   path = "os/redhat"
 }

terraform {
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = ">= 3.0.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0.0"
    }
  }
}

provider "vault" {}


