Tags = [{
    Key   = "DC"
    Value = "DAHL"
  },
  {
    Key   = "ENV"
    Value = "SANDBOX"
  }]

object_type = "https" # Options: https, cifs, nfs
enable_https = true
enable_cifs = false
enable_nfs = false

# create_os_repo
repo_name               = "RHEL-8.9"
repo_nr_version         = "Red Hat Enterprise Linux 8.9"
repo_vendor             = "Red Hat"
repo_description        = "RHEL 8.9 ISO"
repo_source_os_iso_path = "http://172.0.1.10:8080/rhat/rhel-8.9-x86_64-dvd.iso"

# Common attributes between OS/SCU Resources:
repo_source_cifs_mount_options = ""
repo_source_nfs_mount_options  = ""
repo_source_user               = ""
repo_source_password           = ""

# create_scu_repo
repo_source_scu_iso_path = "http://172.0.1.10:8080/Intersight/ucs-scu-6.3.2c.iso"
scu_name                 = "SCU-6.3.2c"
scu_description          = "SCU 6.3.2c software config utility"
scu_nr_version           = "6.3.2c"
scu_supported_models     = ["UCSC-C220-M5SX", "UCSC-C220-M5L", "UCSC-C220-M5SN", "HX220C-M5SX", "HXAF220C-M5SX", "C-series"]