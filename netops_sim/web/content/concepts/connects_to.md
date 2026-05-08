title: Physical cable
---
# Physical cable

A literal cable between two switch ports. It carries tagged VLANs — the underlay routing VLAN, the [TEP](concept:tep) transport VLAN that hauls [GENEVE](concept:geneve)-encapsulated overlay traffic, and any other VLANs the trunk allows.

Cables are the lowest thing the lab simulates: pull one out (or set wrong [MTU](concept:mtu) on it) and you'll see the cascade ripple up through pNICs, BGP sessions, and finally the VMs that depend on the path.
