title: VM attached to segment
---
# VM attached to a segment

The VM's vNIC is plugged into this overlay [segment](concept:segment). Every VM attached to the same segment behaves like it's on the same Layer-2 LAN, even when the VMs sit on different ESX hosts in different racks.

That illusion is what [GENEVE](concept:geneve) and the [TEPs](concept:tep) make possible: the underlay does not actually share a broadcast domain, but the segment does.
