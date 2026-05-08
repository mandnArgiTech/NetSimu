title: Switch port
---
# Switch port

A **switch port** is a single physical interface on a [ToR](concept:tor) or [spine](concept:spine). Each port has independent settings: speed (10G / 25G / 100G), [MTU](concept:mtu), administrative state (up/down), [VLAN](concept:vlan) membership, and whether it's an *access* port (one VLAN, untagged) or a *trunk* port (multiple VLANs, tagged with 802.1Q headers).

Switch ports are where most of the operational pain in a network actually lives. A misconfigured MTU, a flapping link, a port stuck in error-disabled state — these are the everyday faults that cascade into application outages. Counters on each port (`in_octets`, `in_errors`, `in_discards`, `crc_errors`) tell you what's happening at line rate; getting these into your observability pipeline (SNMP, gNMI streaming) is the foundation of any working ops practice.

In NetSimu, ports come in two flavours: *spine-facing* (between spines and ToRs, carrying inter-rack fabric traffic) and *host-facing* (connecting hosts via cables to the ToR). Host-facing ports usually trunk multiple VLANs — management, vMotion, [TEP](concept:tep) — onto the same physical link.

**See also:** [VLAN](concept:vlan), [MTU](concept:mtu), [pNIC](concept:pnic).
