title: Encapsulation (overlay vs underlay)
---
# Encapsulation (overlay vs underlay)

**Encapsulation** is taking one packet and wrapping it inside another. It's how an overlay network gets data through a physical underlay that doesn't understand the overlay's structure.

In NSX:

- The **underlay** is the physical IP network — [spines](concept:spine), [ToRs](concept:tor), cables, [BGP](concept:bgp), regular IP routing. It carries packets between [TEPs](concept:tep).
- The **overlay** is the virtual network the VMs see — [segments](concept:segment), [VPCs](concept:vpc), [DFW](concept:dfw) rules. Logically, every VM thinks it's on a normal Layer 2 network with its peers.
- **[GENEVE](concept:geneve) encapsulation** is the bridge: the source TEP wraps each VM packet in a GENEVE header so the underlay can carry it as opaque IP traffic; the destination TEP unwraps it and delivers the original packet.

This separation is genuinely useful: you can change the overlay without touching the underlay (add a new segment, move a VM), and you can change the underlay without touching the overlay (replace a spine, re-IP a switch). But it has consequences:

- **East-west traffic** (VM-to-VM within the data center) goes overlay-only — encapsulated, decapsulated, no router needed.
- **North-south traffic** (VM-to-internet, VM-to-on-prem) leaves the overlay through a [Tier-0](concept:tier0) — there's a clear point of egress where overlay becomes underlay reachability.
- **MTU and TEP health** become first-class operational concerns. Many overlay outages have nothing to do with the overlay configuration and everything to do with underlay [MTU](concept:mtu) or unreliable TEP transport.

If you've used VXLAN before, GENEVE is its modern cousin — same idea, more extensible header. If you've used cloud VPCs or Kubernetes pod networks, the encapsulation principle is identical even if the specific protocol differs.

**See also:** [GENEVE](concept:geneve), [TEP](concept:tep), [MTU](concept:mtu).
