title: Project's DFW rule
---
# Project's distributed-firewall rule

A [DFW rule](concept:dfw_rule) belongs to a [project](concept:nsx_project). The rule is enforced on every VM in that project — distributed at the hypervisor's vSwitch, not at a perimeter firewall.

That is the *distributed* part of DFW: there is no single chokepoint. If you change a rule, every host in the project picks up the new policy independently.
