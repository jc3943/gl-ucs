#Authored: Jeff Comer

# ---------------------------------------------------------------------------
# Network Connectivity Policy – DNS configuration
#
# Applies to the server's management (IMC/BMC) network interface.
# Configures static DNS servers; DHCP-based DNS is disabled.
# ---------------------------------------------------------------------------

resource "intersight_networkconfig_policy" "this" {
  name        = "${var.policy_prefix}-network-connectivity"
  description = "Static DNS settings for ${var.policy_prefix} standalone servers."

  organization {
    object_type = "organization.Organization"
    moid = data.intersight_organization_organization.default.results[0].moid
  }

  # ---------------------------------------------------------------------------
  # IPv4 DNS
  # ---------------------------------------------------------------------------
  preferred_ipv4dns_server  = var.preferred_dns_server
  alternate_ipv4dns_server  = var.alternate_dns_server

  # Prevent DHCP from overriding the static DNS entries above
  enable_ipv4dns_from_dhcp = false

  # Dynamic DNS registration (requires a domain controller integration)
  enable_dynamic_dns = false

  # ---------------------------------------------------------------------------
  # IPv6 – disabled by default; set var.enable_ipv6 = true to activate
  # ---------------------------------------------------------------------------
  enable_ipv6             = var.enable_ipv6
  enable_ipv6dns_from_dhcp = false
}