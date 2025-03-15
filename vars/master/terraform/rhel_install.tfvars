# Intersight Access API Key
# Common
org_name = "default"
server_serial = "WMP253400KA"
os_config_file = "RHEL8ConfigFile"

os_repo_name = "RHEL-8.9"
scu_repo_name = "SCU-6.3.2c"

# os_install
# Configuration Source : Cisco
# Configuration File :
# ESXi  : ESXi6.7ConfigFile, ESXi6.5ConfigFile,
# Redhat: RHEL8ConfigFile, RHEL7ConfigFile
# Ubuntu: No cisco provided config
# Windows: Windows2019ConfigFile, Windows2016ConfigFile
os_hostname       = "sandbox-rhel89"
os_ip_config_type = "static"

## OS IP Info
os_ipv4_addr         = "172.16.115.11"
os_ipv4_netmask      = "255.255.252.0"
os_ipv4_gateway      = "172.16.115.254"
os_ipv4_dns_ip       = "172.16.10.100"
os_root_password     = "DEVP@ssw0rd"
os_answers_nr_source = "Template" # Template for cisco provided source files
os_answers_netDev    = "eno7"
os_answers_vlanId    = 0
