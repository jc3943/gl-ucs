#Authored: Jeff Comer

# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------
organization_name = "default"

# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------
policy_prefix        = "c220m5"
template_name        = "c220m5-standalone-template"
template_description = "Standalone C220 M5 server profile template"

# ---------------------------------------------------------------------------
# Adapter config
# ---------------------------------------------------------------------------
# VIC 1387 / 1457  →  mlom_port_count = 2
# VIC 1455 / 1467  →  mlom_port_count = 4
mlom_port_count = 2

# ---------------------------------------------------------------------------
# Network connectivity / DNS
# ---------------------------------------------------------------------------
preferred_dns_server = "172.16.10.100"
alternate_dns_server = "172.0.1.11"
enable_ipv6          = false

# ---------------------------------------------------------------------------
# Firmware
# ---------------------------------------------------------------------------
# Version string must match exactly what Intersight shows in the firmware catalog.
# ISO:  ucs-c220m5-huu-4.3.2.250045.iso  →  "4.3(2.250045)"
firmware_bundle_version = "4.3(2.250045)"
firmware_model_family   = "UCSC-C220-M5"