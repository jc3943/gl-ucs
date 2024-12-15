provider "vsphere" {
  user                 = "administrator@vsphere.local"
  password             = "DEVP@ssw0rd"
  vsphere_server       = "172.16.14.137"
  allow_unverified_ssl = true
}

provider "vault" {
  address = "http://172.0.1.10:8200"
  #token   = "your-vault-token"
}