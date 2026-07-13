###############################################################################
# APIC OVA -> vCenter deployment (Terraform equivalent of the Ansible playbook)
# Provider: hashicorp/vsphere
###############################################################################

terraform {
  required_providers {
    vsphere = {
      source  = "hashicorp/vsphere"
      version = ">= 2.6.0"
    }
  }
}

###############################################################################
# Variables (mirrors the playbook's `vars:` block)
# Move secrets to a terraform.tfvars / env vars (TF_VAR_*) in real use.
###############################################################################

variable "vsphere_server" { default = "172.16.14.137" }            # vCenter, not the ESXi host
variable "vsphere_user" { default = "administrator@vsphere.local" }
variable "vsphere_password" {
  default   = "DEVP@ssw0rd"
  sensitive = true
}

variable "datacenter" { default = "HX-DEV" }
variable "cluster" { default = "hx-dev" }
variable "datastore" { default = "DEV" }

variable "vm_name" { default = "apic_test" }

# OVF network names (left side) come from <NetworkSection> in the OVF.
# Portgroup names (right side) are the vapic_net1 / vapic_net2 from the playbook.
variable "vapic_net1" { default = "CG61|CL-PODS|EPG_POD1" } # -> "OOB Network"
variable "vapic_net2" { default = "CG61|CL-PODS|EPG_POD2" } # -> "Infra Network"

# Source OVA. Use the HTTP URL (equivalent of the get_url task)...
variable "remote_ovf_url" {
  default = "http://172.16.112.8/aci/6.2.2e/aci-apic-dk9.6.2.2e.ova"
}
# ...or set this and switch the ovf_deploy block below to local_ovf_path.
variable "local_ovf_path" {
  default = "/mnt/data/aci/6.2.2e/aci-apic-dk9.6.2.2e.ova"
}

# OVF / vApp properties (the `properties:` block)
variable "admin_password" {
  default   = "DEVP@ssw0rd"
  sensitive = true
}
variable "oob_gw" { default = "172.0.1.254" }
variable "oob_ip" { default = "172.0.1.138/24" }

###############################################################################
# Provider
###############################################################################

provider "vsphere" {
  vsphere_server       = var.vsphere_server
  user                 = var.vsphere_user
  password             = var.vsphere_password
  allow_unverified_ssl = true # == validate_certs: no
}

###############################################################################
# Lookups
###############################################################################

data "vsphere_datacenter" "dc" {
  name = var.datacenter
}

data "vsphere_compute_cluster" "cluster" {
  name          = var.cluster
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_datastore" "datastore" {
  name          = var.datastore
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_network" "net1" {
  name          = var.vapic_net1
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_network" "net2" {
  name          = var.vapic_net2
  datacenter_id = data.vsphere_datacenter.dc.id
}

# Reads sizing, guest_id, scsi_type, etc. straight out of the OVF,
# and validates the OVF network-name -> portgroup mapping.
data "vsphere_ovf_vm_template" "apic" {
  name             = var.vm_name
  resource_pool_id = data.vsphere_compute_cluster.cluster.resource_pool_id
  datastore_id     = data.vsphere_datastore.datastore.id

  remote_ovf_url = var.remote_ovf_url
  # local_ovf_path = var.local_ovf_path   # <-- use this instead of remote_ovf_url if deploying from disk

  ovf_network_map = {
    "OOB Network"   = data.vsphere_network.net1.id
    "Infra Network" = data.vsphere_network.net2.id
  }
}

###############################################################################
# Deploy
###############################################################################

resource "vsphere_virtual_machine" "apic" {
  name             = var.vm_name
  resource_pool_id = data.vsphere_compute_cluster.cluster.resource_pool_id
  datastore_id     = data.vsphere_datastore.datastore.id

  # Pulled from the OVF so we don't hardcode them
  num_cpus             = data.vsphere_ovf_vm_template.apic.num_cpus
  num_cores_per_socket = data.vsphere_ovf_vm_template.apic.num_cores_per_socket
  memory               = data.vsphere_ovf_vm_template.apic.memory
  guest_id             = data.vsphere_ovf_vm_template.apic.guest_id
  scsi_type            = data.vsphere_ovf_vm_template.apic.scsi_type
  alternate_guest_name = data.vsphere_ovf_vm_template.apic.alternate_guest_name

  # == wait_for_ip_address: false
  wait_for_guest_net_timeout = 0
  wait_for_guest_ip_timeout  = 0

  # Explicit, ordered NICs. Order matters for APIC (NIC1 = OOB). See note below.
  network_interface {
    network_id = data.vsphere_network.net1.id # OOB Network
  }
  network_interface {
    network_id = data.vsphere_network.net2.id # Infra Network
  }

  ovf_deploy {
    allow_unverified_ssl_cert = true
    disk_provisioning         = "thin"

    remote_ovf_url = var.remote_ovf_url
    # local_ovf_path = var.local_ovf_path   # <-- match whichever you used in the data source

    ovf_network_map = data.vsphere_ovf_vm_template.apic.ovf_network_map
  }

  # == properties: + inject_ovf_env: true (vApp props are injected automatically)
  vapp {
    properties = {
      "com.cisco.vapic.adminpassword" = var.admin_password
      "com.cisco.vapic.oobgw"         = var.oob_gw
      "com.cisco.vapic.oobip"         = var.oob_ip
    }
  }

  lifecycle {
    # The OVF import sets a lot of computed fields; avoid noisy diffs on re-plan.
    ignore_changes = [
      vapp,
      disk,
      annotation,
    ]
  }
}
