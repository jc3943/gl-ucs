data "vault_generic_secret" "ubuntu" {
  path = "app-vms/vm-creds"
}

data "vsphere_datacenter" "datacenter" {
  name = "sandbox"
}

data "vsphere_datastore" "datastore" {
  name          = "VM-DS"
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

data "vsphere_compute_cluster" "cluster" {
  name          = "sandbox"
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

data "vsphere_resource_pool" "default" {
  name          = format("%s%s", data.vsphere_compute_cluster.cluster.name, "/Resources")
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

data "vsphere_host" "host" {
  name          = "172.16.115.21"
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

data "vsphere_network" "network" {
  name          = "VM Network"
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

data "vsphere_network" "network2" {
  name          = "VM Network"
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

## Remote OVF/OVA Source
data "vsphere_ovf_vm_template" "ovfRemote" {
  name              = "CatC-SW-EVA-2.3.7.10-75300.10.ova"
  disk_provisioning = "thick"
  resource_pool_id  = data.vsphere_resource_pool.default.id
  datastore_id      = data.vsphere_datastore.datastore.id
  host_system_id    = data.vsphere_host.host.id
  remote_ovf_url    = "http://172.16.112.8/catalystCenter/CatC-SW-EVA-2.3.7.10-75300.10.ova"
  ovf_network_map = {
    "Network 1" : data.vsphere_network.network.id,
    "Network 2" : data.vsphere_network.network2.id
  }
}

## Deployment of VM from Remote OVF
resource "vsphere_virtual_machine" "vmFromRemoteOvf" {
  name                 = "TF-CatC-SW"
  datacenter_id        = data.vsphere_datacenter.datacenter.id
  datastore_id         = data.vsphere_datastore.datastore.id
  host_system_id       = data.vsphere_host.host.id
  resource_pool_id     = data.vsphere_resource_pool.default.id
  guest_id             = data.vsphere_ovf_vm_template.ovfRemote.guest_id
  num_cpus             = 32
  memory               = 256000
  dynamic "network_interface" {
    for_each = data.vsphere_ovf_vm_template.ovfRemote.ovf_network_map
    content {
      network_id = network_interface.value
    }
  }
  wait_for_guest_net_timeout = 0
  wait_for_guest_ip_timeout  = 0

  ovf_deploy {
    allow_unverified_ssl_cert = true
    remote_ovf_url            = data.vsphere_ovf_vm_template.ovfRemote.remote_ovf_url
    disk_provisioning         = data.vsphere_ovf_vm_template.ovfRemote.disk_provisioning
    ovf_network_map           = data.vsphere_ovf_vm_template.ovfRemote.ovf_network_map
  }

  vapp {
    properties = {
      # "hostname"    = data.vault_generic_secret.ubuntu.data["ubuntu-username"],
      # "password"    = data.vault_generic_secret.ubuntu.data["ubuntu-password"],
      # "public-keys" = data.vault_generic_secret.ubuntu.data["ubuntu-ssh-keys"]
      "guestinfo.CatcHostname"        = "tf-catc-sw",
      "guestinfo.CatcNetworkIP"       = "172.16.14.236",
      "guestinfo.CatcNetworkPrefix"   = tostring(24),
      "guestinfo.CatcNetworkGateway"  = "172.16.14.254",
      "guestinfo.CatcNetworkDNS"      = "172.16.10.100",
      "guestinfo.ciscoNtpServer"      = "172.20.1.254",
      "guestinfo.ciscoSystemAdminPassword" = data.vault_generic_secret.ubuntu.data["dnac-password"],
      "guestinfo.ciscoCliPassword"         = data.vault_generic_secret.ubuntu.data["dnac-password"]
    }
  }
  cdrom {
    client_device = true
  }
  lifecycle {
    ignore_changes = [
      annotation,
      disk[0].io_share_count,
      disk[1].io_share_count,
      disk[2].io_share_count,
      vapp[0].properties,
    ]
  }
}

