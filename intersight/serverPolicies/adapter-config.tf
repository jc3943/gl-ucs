# data "intersight_adapter_config_policy" "adapter_settings" {
#     name = "RHEL-adapter-config-policy"
# }

# output "adapter_config" {
#     value = data.intersight_adapter_config_policy.adapter_settings
# }

resource "intersight_adapter_config_policy" "fec_cl74" {
  name = "Adapter_FEC_CL74"
  organization {
    object_type = "organization.Organization"
    moid = data.intersight_organization_organization.default.results[0].moid
  }
  settings = [
    {
        "additional_properties" = ""
        "class_id" = "adapter.AdapterConfig"
        "dce_interface_settings" = [
            {
              "additional_properties" = ""
              "class_id" = "adapter.DceInterfaceSettings"
              "fec_mode" = "cl74"
              "interface_id" = 0
              "object_type" = "adapter.DceInterfaceSettings"
            },
            {
              "additional_properties" = ""
              "class_id" = "adapter.DceInterfaceSettings"
              "fec_mode" = "cl74"
              "interface_id" = 1
              "object_type" = "adapter.DceInterfaceSettings"
            },
            {
              "additional_properties" = ""
              "class_id" = "adapter.DceInterfaceSettings"
              "fec_mode" = "cl74"
              "interface_id" = 2
              "object_type" = "adapter.DceInterfaceSettings"
            },
            {
              "additional_properties" = ""
              "class_id" = "adapter.DceInterfaceSettings"
              "fec_mode" = "cl74"
              "interface_id" = 3
              "object_type" = "adapter.DceInterfaceSettings"
            },
        ]
        "eth_settings" = [
            {
              "additional_properties" = ""
              "class_id" = "adapter.EthSettings"
              "lldp_enabled" = true
              "object_type" = "adapter.EthSettings"
            },
        ]
        "fc_settings" = [
            {
              "additional_properties" = ""
              "class_id" = "adapter.FcSettings"
              "fip_enabled" = true
              "object_type" = "adapter.FcSettings"
            },
        ]
        "object_type" = "adapter.AdapterConfig"
        "physical_nic_mode_settings" = [
            {
              "additional_properties" = ""
              "class_id" = "adapter.PhysicalNicModeSettings"
              "object_type" = "adapter.PhysicalNicModeSettings"
              "phy_nic_enabled" = false
            },
        ]
        "port_channel_settings" = [
            {
              "additional_properties" = ""
              "class_id" = "adapter.PortChannelSettings"
              "enabled" = false
              "object_type" = "adapter.PortChannelSettings"
            },
        ]
          "slot_id" = "MLOM"
    }    
  ]
}