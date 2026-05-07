title: vMotion
---
# vMotion

**vMotion** is the VMware feature that moves a running [VM](concept:vm) from one [ESX host](concept:esx_host) to another with no downtime. The VM's memory is copied across the network while it's still running, then the source pauses for a few milliseconds while the last dirty pages and CPU state are shipped, and the VM resumes execution on the target host. From the VM's point of view, network connections stay open and clock barely jumps.

There are two flavors that matter operationally:

- **Planned vMotion** — you trigger it (e.g. before a host maintenance) or DRS triggers it (load balancing). Smooth, no application impact.
- **Unplanned vMotion via HA** — a host fails or is isolated, and HA evacuates surviving VMs (or restarts crashed ones) on healthy hosts. Less smooth: there's a detect-and-react window where VMs are briefly unreachable, plus a brief application latency spike while everything settles.

Either way, vMotion needs its own dedicated network: a [VLAN](concept:vlan) on the underlay, vmkernel adapters on each host, and ideally jumbo frames because memory-copy traffic is high-bandwidth. NetSimu's `pnic_failure_vmotion` scenario walks through an HA-driven evacuation: both pNICs on host-03 die, HA marks the host isolated, and the VMs on it migrate to host-01 and host-04 with a transient latency blip until everything restabilizes.

The pedagogical point: vMotion *changes the topology mid-incident*. A VM that was running on host-03 is now running on host-01. RCA tools without time-versioned topology data get confused by this.

**See also:** [ESX host](concept:esx_host), [VM](concept:vm).
