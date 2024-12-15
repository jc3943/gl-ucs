provider "vsphere" {
  user                 = "administrator@vsphere.local"
  password             = "DEVP@ssw0rd"
  vsphere_server       = "172.16.14.137"
  allow_unverified_ssl = true
}