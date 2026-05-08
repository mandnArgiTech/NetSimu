title: Virtual Machine (VM)
---
# Virtual Machine (VM)

A **VM** is a guest operating system running on an [ESX host](concept:esx_host). From the VM's point of view it has its own network adapter (a vNIC), gets an IP from a [segment](concept:segment) it's attached to, and talks to other VMs as if they were on a normal Layer 2 network. The host's vSwitch and the [TEP](concept:tep) take care of the underlay plumbing transparently.

NetSimu has 7 VMs distributed across 3 application tiers: 3 web tier, 2 api tier, 2 db tier. They're spread across hosts on purpose — `vm-web-01` on host-01, `vm-web-02` on host-02, etc. — so when a host fails, [vMotion](concept:vmotion) can migrate the affected VMs to surviving hosts and the application as a whole keeps running.

Two things matter operationally: which host a VM is currently running on (changes when vMotion happens, including unplanned HA failovers), and which segment it's attached to (rarely changes). Both are visible at the topology level; the [DFW](concept:dfw) decides whether traffic between two specific VMs is allowed.

**See also:** [ESX host](concept:esx_host), [segment](concept:segment), [vMotion](concept:vmotion).
