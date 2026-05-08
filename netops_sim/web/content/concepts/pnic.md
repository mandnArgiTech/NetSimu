title: pNIC (physical NIC)
---
# pNIC (physical NIC)

A **pNIC** is the host's physical network adapter — the piece of hardware that has a Linux/ESXi name like `vmnic0` or `vmnic1` and a cable plugged into it. ESX hosts in NetSimu have two pNICs each (vmnic0 and vmnic1), connected to ToRs in different racks for redundancy.

The pNIC carries multiple kinds of traffic, separated by [VLAN](concept:vlan) tags on the trunk: management, vMotion, [TEP](concept:tep) transport, sometimes vSAN storage. The hypervisor's virtual switching layer (the DVS) decides which VLAN to tag a packet with based on which port group the source VM is attached to. From the underlay switch's perspective, all of that just looks like tagged Ethernet frames coming in on a trunk port.

When a pNIC link drops (cable pull, transceiver failure, switch port shutdown), the host can still survive on the surviving pNIC if it's set up correctly — that's the "dual-homed" model the topology uses. If both pNICs drop, the host is *isolated*: HA kicks in and VMs migrate elsewhere. The MTU on the pNIC must match the ToR's host-facing port; an [MTU](concept:mtu) mismatch is one of the most common ways overlay traffic breaks silently.

**See also:** [ESX host](concept:esx_host), [VLAN](concept:vlan), [MTU](concept:mtu), [TEP](concept:tep).
