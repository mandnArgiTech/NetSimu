title: VLAN (Virtual LAN)
---
# VLAN (Virtual LAN)

A **VLAN** is a way to slice a single physical Ethernet network into multiple logical broadcast domains using an 802.1Q tag (12 bits — values 1–4094). Two devices on different VLANs can't talk to each other directly even if they're plugged into the same physical switch; they need a router to bridge between them.

In a VCF underlay you'll see a small handful of VLANs on each host's trunked link to its [ToR](concept:tor):

- **Management VLAN** — vCenter, NSX Manager, host management traffic.
- **vMotion VLAN** — VM live-migration traffic (high bandwidth, latency sensitive).
- **TEP transport VLAN** — overlay [GENEVE](concept:geneve) traffic between [TEPs](concept:tep). NetSimu uses VLAN 1647.
- **vSAN VLAN** (if vSAN is in use) — storage traffic.

These all share the same physical link (the [pNIC](concept:pnic) → ToR cable) but are kept logically separate by VLAN tagging. An *access port* carries one VLAN untagged; a *trunk port* carries multiple VLANs each with its own tag — host-facing ToR ports are almost always trunks.

The overlay VMs themselves live on [segments](concept:segment), which are NOT VLANs — they're virtualized at a higher layer, identified by GENEVE VNIs, and ride the TEP VLAN as their underlay transport.

**See also:** [pNIC](concept:pnic), [TEP](concept:tep), [switch port](concept:switch_port).
