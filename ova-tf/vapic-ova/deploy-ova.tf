variable "csv_file" { default = "vapic-specs.csv" }

locals {
  vapics = {
    for row in csvdecode(file("${path.module}/${var.csv_file}")) :
    row.vapic_name => row
  }
}

data "vsphere_datacenter" "dc" {
  for_each = local.vapics
  name     = each.value.datacenter
}

data "vsphere_datastore" "datastore" {
  for_each      = local.vapics
  name          = each.value.datastore
  datacenter_id = data.vsphere_datacenter.dc[each.key].id
}

data "vsphere_compute_cluster" "cluster" {
  for_each      = local.vapics
  name          = each.value.cluster
  datacenter_id = data.vsphere_datacenter.dc[each.key].id
}

data "vsphere_resource_pool" "pool" {
  for_each = local.vapics
  # "default" -> cluster root pool; anything else used as a literal pool name
  name          = each.value.resource_pool == "default" ? "${each.value.cluster}/Resources" : each.value.resource_pool
  datacenter_id = data.vsphere_datacenter.dc[each.key].id
}

data "vsphere_host" "host" {
  for_each      = local.vapics
  name          = each.value.esxi_host
  datacenter_id = data.vsphere_datacenter.dc[each.key].id
}

data "vsphere_network" "oob" {
  for_each      = local.vapics
  name          = each.value.vapic_oob_nic
  datacenter_id = data.vsphere_datacenter.dc[each.key].id
}

data "vsphere_network" "infra" {
  for_each      = local.vapics
  name          = each.value.vapic_infra_nic
  datacenter_id = data.vsphere_datacenter.dc[each.key].id
}

## Remote OVF/OVA Source
## Remote OVF/OVA Source — one template read per VM
data "vsphere_ovf_vm_template" "ovf" {
  for_each          = local.vapics
  name              = each.value.vapic_name
  disk_provisioning = "thick"
  resource_pool_id  = data.vsphere_resource_pool.pool[each.key].id
  datastore_id      = data.vsphere_datastore.datastore[each.key].id
  host_system_id    = data.vsphere_host.host[each.key].id
  remote_ovf_url    = each.value.vapic_ova_url

  ovf_network_map = {
    "OOB Network"   = data.vsphere_network.oob[each.key].id
    "Infra Network" = data.vsphere_network.infra[each.key].id
  }
}

###############################################################################
# Deploy — one VM per CSV row
###############################################################################

resource "vsphere_virtual_machine" "vapic" {
  for_each = local.vapics

  name             = each.value.vapic_name
  datacenter_id    = data.vsphere_datacenter.dc[each.key].id
  datastore_id     = data.vsphere_datastore.datastore[each.key].id
  host_system_id   = data.vsphere_host.host[each.key].id
  resource_pool_id = data.vsphere_resource_pool.pool[each.key].id
  guest_id         = data.vsphere_ovf_vm_template.ovf[each.key].guest_id

  # Explicit, ordered NICs — OOB is NIC1, Infra is NIC2
  network_interface {
    network_id = data.vsphere_network.oob[each.key].id
  }
  network_interface {
    network_id = data.vsphere_network.infra[each.key].id
  }

  wait_for_guest_net_timeout = 0
  wait_for_guest_ip_timeout  = 0

  # Pulled from the OVF so we don't hardcode them
  num_cpus             = data.vsphere_ovf_vm_template.ovf[each.key].num_cpus
  num_cores_per_socket = data.vsphere_ovf_vm_template.ovf[each.key].num_cores_per_socket
  memory               = data.vsphere_ovf_vm_template.ovf[each.key].memory
  #guest_id             = data.vsphere_ovf_vm_template.ovf[each.key].guest_id
  scsi_type            = data.vsphere_ovf_vm_template.ovf[each.key].scsi_type
  alternate_guest_name = data.vsphere_ovf_vm_template.ovf[each.key].alternate_guest_name

  ovf_deploy {
    allow_unverified_ssl_cert = true
    remote_ovf_url            = each.value.vapic_ova_url
    disk_provisioning         = data.vsphere_ovf_vm_template.ovf[each.key].disk_provisioning
    ovf_network_map           = data.vsphere_ovf_vm_template.ovf[each.key].ovf_network_map
    deployment_option         = "APIC-SERVER-VMWARE-M1"
    ip_allocation_policy      = "fixedPolicy"
    ip_protocol               = "IPv4"
  }

  vapp {
    properties = {
      "adminpassword"  = "SOMEPassw0rd"       # bare OVF keys
      "oobip"         = each.value.vapic_ip
      "oobgw"         = each.value.vapic_gw
    }
  }

  lifecycle {
    ignore_changes = [
      annotation,
      disk[0].io_share_count,
      disk[1].io_share_count,
      disk[2].io_share_count,
      # vapp,   # uncomment if re-plans show a perpetual vapp diff
    ]
  }
}

###############################################################################
# Wait until every vAPIC OOB IP answers before apply completes.
# Tools-independent: checks actual reachability of the injected static OOB IP.
# Runs once per VM, in parallel. Ceiling = 120 tries x 15s = 30 minutes each.
###############################################################################

resource "terraform_data" "wait_for_vapic" {
  for_each = local.vapics

  # Re-run the wait whenever the VM is (re)created. This also creates an
  # implicit dependency, so the wait always runs after the VM exists.
  triggers_replace = vsphere_virtual_machine.vapic[each.key].id

  input = {
    name = each.value.vapic_name
    ip   = split("/", each.value.vapic_ip)[0] # strip the /24 mask
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      ip="${self.input.ip}"
      name="${self.input.name}"
      url="https://$ip/api/aaaListDomains.json"   # served pre-auth once the API is ready
      echo "Waiting for $name API at $ip ..."
      for i in $(seq 1 120); do
        code=$(curl -k -s -o /dev/null -w '%{http_code}' --max-time 5 "$url" || true)
        if [ "$code" = "200" ]; then
          echo "$name API ready (HTTP 200) after ~$((i * 30))s."
          exit 0
        fi
        sleep 30
      done
      echo "ERROR: timed out; last HTTP code was '$code'" >&2
      exit 1
    EOT
  }
}

###############################################################################
# Handy output
###############################################################################

output "vapic_vms" {
  value = {
    for k, vm in vsphere_virtual_machine.vapic :
    k => {
      name   = vm.name
      oob_ip = local.vapics[k].vapic_ip
      moid   = vm.moid
    }
  }
}