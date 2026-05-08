title: ESX host
---
# ESX host

An **ESX host** is a physical server running VMware's ESXi hypervisor. It hosts virtual machines, owns the physical network adapters ([pNICs](concept:pnic)) that connect it to the underlay, and runs the [TEP](concept:tep) (tunnel endpoint) that wraps and unwraps overlay traffic. In a VCF deployment, hosts are grouped into *clusters* — collections of hosts that share storage and migrate VMs among themselves via [vMotion](concept:vmotion).

NetSimu's reference topology has 8 hosts in 3 clusters: `cluster-prod` (4 hosts running application VMs), `cluster-edge` (2 hosts running NSX Edge nodes for north-south routing), and `cluster-mgmt` (2 hosts for vCenter and NSX Manager). Every host is dual-homed: one pNIC connects to a ToR in rack-01, the other to a ToR in rack-02. This cross-rack pairing means a single rack failure doesn't disconnect the host.

When an operator says "I lost a host," that almost always means the host has been *isolated* — either both pNICs went down, or some software-level problem made it unreachable to vCenter. HA (High Availability) reacts to host isolation by restarting affected VMs on healthy hosts. That's the cascade the `pnic_failure_vmotion` scenario in the lab demonstrates.

**See also:** [pNIC](concept:pnic), [TEP](concept:tep), [vMotion](concept:vmotion).
