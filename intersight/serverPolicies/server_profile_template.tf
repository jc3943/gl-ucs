#Authored: Jeff Comer

# ---------------------------------------------------------------------------
# Server Profile Template – UCS C220 M5 Standalone
#
# Bundles all policies into a single reusable template.
# Derive individual server profiles from this template via the
# Intersight UI, REST API, or the intersight_server_profile resource
# with source_template set to this template's MOID.
#
# target_platform = "Standalone" is required for direct-attached C-series.
# ---------------------------------------------------------------------------

resource "intersight_server_profile_template" "this" {
  name        = var.template_name
  description = var.template_description

  organization {
    object_type = "organization.Organization"
    moid = data.intersight_organization_organization.default.results[0].moid
  }

  # Must be "Standalone" for C-series servers not connected to a Fabric Interconnect
  target_platform = "Standalone"

  # -------------------------------------------------------------------------
  # Policy bucket – attach each policy by MOID and object type
  # -------------------------------------------------------------------------

  # BIOS – disable hyper-threading
  policy_bucket {
    moid        = intersight_bios_policy.this.moid
    object_type = "bios.Policy"
  }

  # Adapter config – CL74 FEC, port-channel disabled, FIP disabled
  policy_bucket {
    moid        = intersight_adapter_config_policy.this.moid
    object_type = "adapter.ConfigPolicy"
  }

  # Boot order – UEFI, Secure Boot off
  policy_bucket {
    moid        = intersight_boot_precision_policy.this.moid
    object_type = "boot.PrecisionPolicy"
  }

  # Network connectivity – static DNS
  policy_bucket {
    moid        = intersight_networkconfig_policy.this.moid
    object_type = "networkconfig.Policy"
  }

  # Firmware – HUU 4.3(2.250045)
  policy_bucket {
    moid        = intersight_firmware_policy.this.moid
    object_type = "firmware.Policy"
  }
}

# ---------------------------------------------------------------------------
# (Optional) Derived server profile example
#
# Uncomment and duplicate this block for each physical server you want to
# manage. The profile inherits all policies from the template above and can
# be assigned to a specific server by setting assigned_server.
#
# resource "intersight_server_profile" "server_01" {
#   name        = "c220m5-server-01"
#   description = "Derived from ${var.template_name}"
#
#   organization {
#     object_type = "organization.Organization"
#     moid        = data.intersight_organization_organization.org.results[0].moid
#   }
#
#   target_platform = "Standalone"
#
#   # Link back to the template so policy changes propagate
#   src_template {
#     moid        = intersight_server_profile_template.this.moid
#     object_type = "server.ProfileTemplate"
#   }
#
#   # Replace with the target server's MOID
#   assigned_server {
#     moid        = "<server-moid>"
#     object_type = "compute.RackUnit"
#   }
#
#   # "Deploy" triggers firmware/config push; use "Validate" or "No-op" first
#   action = "No-op"
# }
# ---------------------------------------------------------------------------