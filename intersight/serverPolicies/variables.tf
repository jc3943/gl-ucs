# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------

variable "organization_name" {
  description = "Name of the Intersight organization to create resources in."
  type        = string
  default     = "default"
}

# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------

variable "policy_prefix" {
  description = "Short prefix applied to every policy and template name (e.g. 'prod', 'lab')."
  type        = string
  default     = "c220m5"
}

variable "template_name" {
  description = "Name of the server profile template."
  type        = string
  default     = "c220m5-standalone-template"
}

variable "template_description" {
  description = "Description for the server profile template."
  type        = string
  default     = "Standalone C220 M5 server profile template."
}

# ---------------------------------------------------------------------------
# Adapter config
# ---------------------------------------------------------------------------

variable "mlom_port_count" {
  description = "Number of DCE (physical) ports on the MLOM VIC to configure (2 for VIC 1387/1457, 4 for VIC 1455/1467)."
  type        = number
  default     = 2

  validation {
    condition     = contains([2, 4], var.mlom_port_count)
    error_message = "mlom_port_count must be 2 or 4."
  }
}

# ---------------------------------------------------------------------------
# Network connectivity / DNS
# ---------------------------------------------------------------------------

variable "preferred_dns_server" {
  description = "Primary DNS server IPv4 address."
  type        = string
  default     = "208.67.222.222"
}

variable "alternate_dns_server" {
  description = "Alternate (secondary) DNS server IPv4 address. Set to empty string to omit."
  type        = string
  default     = "208.67.220.220"
}

variable "enable_ipv6" {
  description = "Enable IPv6 on the management interface."
  type        = bool
  default     = false
}

# ---------------------------------------------------------------------------
# Firmware
# ---------------------------------------------------------------------------

variable "firmware_bundle_version" {
  description = <<-EOT
    HUU firmware bundle version string as displayed in Intersight
    (e.g. "4.3(2.250045)" for ucs-c220m5-huu-4.3.2.250045.iso).
  EOT
  type        = string
  default     = "4.3(2.250045)"
}

variable "firmware_model_family" {
  description = "Server model family identifier used by the firmware policy (e.g. 'UCSC-C220-M5')."
  type        = string
  default     = "UCSC-C220-M5"
}