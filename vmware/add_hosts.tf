data "vault_generic_secret" "vcsa" {
  path = "vsphere/vcenter"
}

data "vsphere_datacenter" "datacenter" {
  name = "sandbox"
}

data "vsphere_compute_cluster" "cluster" {
  name          = "esxi-sa"
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

data "vsphere_host_thumbprint" "thumbprint" {
  address  = "esxi-01.example.com"
  insecure = true
}

resource "vsphere_host" "esx-01" {
  hostname   = "esxi-01.example.com"
  username   = "root"
  password   = "password"
  license    = "00000-00000-00000-00000-00000"
  thumbprint = data.vsphere_host_thumbprint.thumbprint.id
  cluster    = data.vsphere_compute_cluster.cluster.id
  services {
    ntpd {
      enabled     = true
      policy      = "on"
      ntp_servers = ["pool.ntp.org"]
    }
}