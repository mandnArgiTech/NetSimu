title: TEP (Tunnel Endpoint)
---
# TEP (Tunnel Endpoint)

The **TEP** is the most important entity to understand in NSX. It's the bridge between the *underlay* (boring physical IP fabric, switches and cables) and the *overlay* (the virtual logical network the VMs actually live in).

Every ESX host has one TEP. When a VM sends a packet to another VM on a different host, here's what happens:

1. The packet leaves the source VM and enters the host's vSwitch.
2. The host's TEP wraps that packet inside a [GENEVE](concept:geneve) header — that's [encapsulation](concept:encapsulation). The outer header has a source IP (this TEP's IP) and a destination IP (the peer host's TEP IP).
3. The wrapped packet is sent out on the physical fabric like any other packet. The underlay doesn't know or care that it's overlay traffic.
4. The peer host's TEP receives it, strips off the GENEVE header, and delivers the original packet to the destination VM.

This is why MTU matters so much: the GENEVE header adds about 50 bytes, so a 1500-byte VM packet becomes a 1550+ byte underlay packet. If any switch port along the way has [MTU](concept:mtu) set to 1500, the encapsulated packet gets dropped silently. The underlay shows clean counters, but VM-to-VM communication breaks. That's the `mtu_mismatch` scenario in the lab.

NetSimu's TEPs use VLAN 1647 for transport, IPs in 10.20.0.0/24. Each TEP pairs with every other TEP in the cluster; that pairwise mesh is what lets any VM reach any other VM regardless of which host it's on.

**See also:** [GENEVE](concept:geneve), [encapsulation](concept:encapsulation), [MTU](concept:mtu), [segment](concept:segment).
