#Authored: Jeff Comer
# ---------------------------------------------------------------------------
# Boot Order Policy – UEFI boot, Secure Boot disabled
#
# Boot sequence:
#   1. Local disk (MRAID / RAID controller)
#   2. KVM-mapped virtual DVD (useful for OS installs / recovery)
#
# Adjust or remove boot_devices blocks to match your environment.
# ---------------------------------------------------------------------------

resource "intersight_boot_precision_policy" "this" {
  name        = "${var.policy_prefix}-boot"
  description = "UEFI boot without Secure Boot for ${var.policy_prefix} standalone servers."

  organization {
    object_type = "organization.Organization"
    moid = data.intersight_organization_organization.default.results[0].moid
  }

  # UEFI mode – valid values: "Legacy" | "Uefi" | "None"
  configured_boot_mode = "Uefi"

  # Secure Boot – must be false when no signed boot loader is enrolled
  enforce_uefi_secure_boot = false

  # -------------------------------------------------------------------------
  # Boot device 1 – local disk via the onboard RAID controller
  # -------------------------------------------------------------------------
  boot_devices {
    enabled     = true
    name        = "local-disk"
    object_type = "boot.LocalDisk"
    additional_properties = jsonencode({
      Slot    = "MRAID"
      Bootloader = {
        Description = ""
        Name        = ""
        Path        = ""
      }
    })
  }

  # -------------------------------------------------------------------------
  # Boot device 2 – KVM-mapped virtual DVD (optional; disable if not needed)
  # -------------------------------------------------------------------------
  boot_devices {
    enabled     = true
    name        = "kvm-dvd"
    object_type = "boot.VirtualMedia"
    additional_properties = jsonencode({
      SubType = "kvm-mapped-dvd"
    })
  }
}