terraform {
  #required_version = ">= 1.3.6"
  required_providers {
    intersight = {
      source = "CiscoDevNet/intersight"
      #version = "1.0.35"
    }
  }
}

provider "intersight" {
  apikey    = "6457bfa47564612d300f0917/6457cbbd7564612d30cb32ab/64595f8c7564612d30cb47cc"
  secretkey = "../../creds/dev-isight-SecretKey.txt"
  endpoint  = "https://dev-intersight.some.domain.com"
}
