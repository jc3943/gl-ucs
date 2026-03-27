#Authored: Jeff Comer

# ---------------------------------------------------------------------------
# This policy pins the firmware bundle version for the specified server
# model family. The firmware upgrade will be applied when a server profile
# using this template is deployed and the "action" is set to "Deploy".
#
# target_platform must be "Standalone" for direct-attached C-series servers.
# ---------------------------------------------------------------------------

resource "intersight_firmware_policy" "this" {
  name        = "${var.policy_prefix}-firmware"
  description = "Firmware policy targeting HUU ${var.firmware_bundle_version} for ${var.firmware_model_family}."

  organization {
    object_type = "organization.Organization"
    moid = data.intersight_organization_organization.default.results[0].moid
  }

  # "Standalone" for C-series servers managed directly (not via FI)
  target_platform = "Standalone"

  # One entry per server model family; add additional blocks for mixed fleets
  model_bundle_combo {
    # Must match the PID family shown in the Intersight firmware catalog
    # e.g. "UCSC-C220-M5", "UCSC-C240-M5", "UCSC-C480-M5"
    model_family   = var.firmware_model_family

    # Version string format: <major>.<minor>(<patch>.<build>)
    bundle_version = var.firmware_bundle_version
  }
}