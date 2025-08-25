# Intersight Access API Key
# Common
org_name = "default"
server_serial = "WZP28310Q1B"
os_config_file = "ESXi7.0ConfigFile"

os_repo_name = "ESXi-7.0"
scu_repo_name = "SCU-6.3.2c"

# os_install
# Configuration Source : Cisco
# Configuration File :
# ESXi  : ESXi6.7ConfigFile, ESXi6.5ConfigFile,
# Redhat: RHEL8ConfigFile, RHEL7ConfigFile
# Ubuntu: No cisco provided config
# Windows: Windows2019ConfigFile, Windows2016ConfigFile
os_hostname       = "sandbox-bm-esxi.thor.iws.nayv.mil"
os_ip_config_type = "static"

## OS IP Info
os_ipv4_addr         = "172.16.115.43"
os_ipv4_netmask      = "255.255.252.0"
os_ipv4_gateway      = "172.16.115.254"
os_ipv4_dns_ip       = "172.16.20.101"
os_root_password     = "somepassword"
os_answers_nr_source = "Template" # Template for cisco provided source files
os_answers_netDev    = "vmnic4"
os_answers_vlanId    = 1200
