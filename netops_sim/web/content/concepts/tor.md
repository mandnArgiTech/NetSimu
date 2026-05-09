title: Top-of-Rack (ToR) switch
---
# Top-of-Rack (ToR) switch

A **ToR** is the leaf switch at the bottom of a server rack. It has two kinds of ports: *host-facing* ports (downward-pointing, toward the ESX hosts in the rack) and *spine-facing* ports (upward-pointing, toward the [spines](concept:spine)). Every server in the rack plugs into the ToRs above it, and from there traffic can reach any other rack via the spine layer.

In NetSimu the four ToRs are mixed-vendor on purpose: tor-01 and tor-02 are Cisco Nexus 9000 (NX-OS), tor-03 and tor-04 are Arista 7050 (EOS). This mirrors what you'll find in real VCF deployments — the underlay is rarely single-vendor, and that's why operations tooling has to speak both NX-API/SNMP (Cisco) and gNMI (Arista).

ToRs participate in [BGP](concept:bgp) with the NSX [Tier-0 gateway](concept:tier0) so the underlay can carry routes to overlay-attached destinations. They also carry the [TEP](concept:tep) transport [VLAN](concept:vlan) — when [MTU](concept:mtu) on a ToR port is set incorrectly, [GENEVE](concept:geneve)-encapsulated traffic gets dropped silently and overlay communication degrades.

**See also:** [spine](concept:spine), [BGP](concept:bgp), [MTU](concept:mtu), [VLAN](concept:vlan).
