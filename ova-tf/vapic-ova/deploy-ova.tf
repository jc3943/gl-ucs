data "vsphere_datacenter" "datacenter" {
  name = "sandbox"
}

data "vsphere_datastore" "datastore" {
  name          = "NVMe-DS1"
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

data "vsphere_compute_cluster" "cluster" {
  name          = "esxi-sa"
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

data "vsphere_resource_pool" "default" {
  name          = format("%s%s", data.vsphere_compute_cluster.cluster.name, "/Resources")
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

data "vsphere_host" "host" {
  name          = "172.20.104.42"
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

data "vsphere_network" "network" {
  name          = "OOB"
  datacenter_id = data.vsphere_datacenter.datacenter.id
}

## Remote OVF/OVA Source
data "vsphere_ovf_vm_template" "ovfRemote" {
  name              = "aci-apic-dk9.6.0.5h.ova"
  disk_provisioning = "thick"
  resource_pool_id  = data.vsphere_resource_pool.default.id
  datastore_id      = data.vsphere_datastore.datastore.id
  host_system_id    = data.vsphere_host.host.id
  remote_ovf_url    = "http://172.0.1.10:8080/aci/aci-apic-dk9.6.0.5h.ova"
  ovf_network_map = {
    "Network 1" : data.vsphere_network.network.id
  }
}

## Deployment of VM from Remote OVF
resource "vsphere_virtual_machine" "vmFromRemoteOvf" {
  name                 = "apic602h-test"
  datacenter_id        = data.vsphere_datacenter.datacenter.id
  datastore_id         = data.vsphere_datastore.datastore.id
  host_system_id       = data.vsphere_host.host.id
  resource_pool_id     = data.vsphere_resource_pool.default.id
  guest_id             = data.vsphere_ovf_vm_template.ovfRemote.guest_id
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
      "com.cisco.vapic.adminpassword"  = "somepassw0rd",
      "com.cisco.vapic.oobip"          = "172.0.1.102/24",
      "com.cisco.vapic.oobgw"          = "172.0.1.254"
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

