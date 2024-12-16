data "vault_generic_secret" "vcsa" {
  path = "vsphere/vcenter"
}

data "vault_generic_secret" "esxi" {
  path = "vsphere/esxi"
}

provider "vsphere" {
  user                 = data.vault_generic_secret.vcsa.data["username"]
  password             = data.vault_generic_secret.vcsa.data["password"]
  vsphere_server       = data.vault_generic_secret.vcsa.data["vcenter-ip"]
  allow_unverified_ssl = true
}

provider "vault" {

}