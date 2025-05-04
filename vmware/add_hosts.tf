data "vsphere_datacenter" "datacenter" {
  name = "sandbox"
}

data "vsphere_compute_cluster" "cluster" {
  name          = "esxi-sa"
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

data "vsphere_host_thumbprint" "thumbprint" {
  address  = "172.16.115.41"
  insecure = true
}

resource "vsphere_host" "esx-01" {
  hostname   = "172.16.115.41"
  username   = data.vault_generic_secret.esxi.data["username"]
  password   = data.vault_generic_secret.esxi.data["password"]
  #license    = "00000-00000-00000-00000-00000"
  thumbprint = data.vsphere_host_thumbprint.thumbprint.id
  cluster    = data.vsphere_compute_cluster.cluster.id
}