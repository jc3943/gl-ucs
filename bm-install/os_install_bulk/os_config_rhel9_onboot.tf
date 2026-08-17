# =============================================================================
# Custom RHEL 9 OS Configuration File with the --onboot=yes network fix.
#
# WHY THIS EXISTS:
# Intersight requires that EVERY {{ .answers.* }} token in the answer file be
# declared as a registered placeholder. The UI "upload" path does not register
# them, which is why pasting rhel96.cfg fails with:
#   "The uploaded answer file placeholder must conform to the proper Golang
#    template syntax."
# Creating the file via Terraform with the placeholders block below registers
# each token, so it validates and stays dynamic for per-server (bulk) installs.
#
# The catalog + distribution MOIDs below were taken from your tenant's built-in
# RHEL9ConfigFile so this custom file is valid for the same RHEL 9.x releases.
# =============================================================================

locals {
  # One entry per distinct {{ .answers.* }} token used in rhel96.cfg.
  rhel9_onboot_placeholders = [
    ".answers.NetworkDevice",
    ".answers.IpV4Config.Gateway",
    ".answers.IpV4Config.IpAddress",
    ".answers.NameServer",
    ".answers.IpV4Config.Netmask",
    ".answers.Hostname",
    ".answers.RootPassword",
  ]

  # hcl.OperatingSystem MOIDs (RHEL 9.x) copied from the built-in RHEL9ConfigFile.
  rhel9_distributions = [
    "6457c4876f7274301f9fadb7",
    "6457c4876f7274301f9fadb8",
    "65dd6c866f7274301f37dc53",
    "663b97566f7274301ffa7332",
    "66acde476f7274301fe43e66",
    "67d8978d6f7274301f50aa63",
    "69134e966f7274301f6547eb",
  ]
}

resource "intersight_os_configuration_file" "rhel9_onboot" {
  name         = "RHEL9ConfigFile-onboot"
  description  = "RHEL 9 answer file with --onboot=yes + NetworkManager enablement"
  file_content = file("${path.module}/rhel96.cfg")

  # os.Catalog MOID from your tenant (same one the built-in RHEL9ConfigFile uses).
  catalog {
    object_type = "os.Catalog"
    moid        = "6457caad4c676b5915cf22c3"
  }

  dynamic "distributions" {
    for_each = local.rhel9_distributions
    content {
      object_type = "hcl.OperatingSystem"
      moid        = distributions.value
    }
  }

  # Register every {{ .answers.* }} token so Intersight accepts the template.
  dynamic "placeholders" {
    for_each = local.rhel9_onboot_placeholders
    content {
      class_id     = "os.PlaceHolder"
      object_type  = "os.PlaceHolder"
      is_value_set = false
      type {
        class_id    = "workflow.PrimitiveDataType"
        object_type = "workflow.PrimitiveDataType"
        name        = placeholders.value
        label       = placeholders.value
        required    = false
        properties {
          class_id    = "workflow.PrimitiveDataProperty"
          object_type = "workflow.PrimitiveDataProperty"
          secure      = false
          type        = "string"
        }
        display_meta {
          class_id           = "workflow.DisplayMeta"
          object_type        = "workflow.DisplayMeta"
          inventory_selector = true
          widget_type        = "None"
        }
      }
    }
  }
}

output "rhel9_onboot_config_moid" {
  value = intersight_os_configuration_file.rhel9_onboot.moid
}
