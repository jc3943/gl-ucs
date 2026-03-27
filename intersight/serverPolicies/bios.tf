#Authored: Jeff Comer

data "intersight_organization_organization" "default" {
  name = "default"
}

resource "intersight_bios_policy" "this" {
  name = "${var.policy_prefix}-bios"
  organization {
    object_type = "organization.Organization"
    moid = data.intersight_organization_organization.default.results[0].moid
  }
  intel_hyper_threading_tech = "disabled"
}