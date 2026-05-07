title: GENEVE
---
# GENEVE (Generic Network Virtualization Encapsulation)

**GENEVE** is the encapsulation protocol NSX uses to carry overlay traffic over an IP underlay. It's the wrapper around your VM's actual packet that lets it travel through a routed physical network and arrive on what looks like the same Layer 2 as the destination VM.

When a VM on host-01 sends a packet to a VM on host-02:

```
[ Original VM packet, ~1500 bytes ]
         │
         ▼ (TEP wraps it)
[ Outer Eth | Outer IP | UDP | GENEVE header | Original packet ]
~50 bytes of overhead
```

The outer IP source is host-01's [TEP](concept:tep) IP; the outer IP destination is host-02's TEP IP. The GENEVE header carries metadata: the VNI (virtual network identifier — which [segment](concept:segment) this belongs to), and option fields NSX uses for service chaining and policy.

Two practical consequences:

1. **MTU matters.** A 1500-byte VM packet becomes a 1550+ byte underlay packet. If any link in the path has [MTU](concept:mtu) below ~1700, GENEVE-wrapped traffic gets dropped. Best practice: jumbo frames (9000-byte MTU) on the underlay end-to-end.
2. **The underlay sees opaque IP traffic.** A switch can't inspect what's inside the GENEVE tunnel without decapsulating it. That's the whole point of the overlay: separation of concerns. It also means underlay troubleshooting tools won't show you per-VM flow information — for that you need NSX Intelligence or per-TEP telemetry.

**See also:** [TEP](concept:tep), [encapsulation](concept:encapsulation), [MTU](concept:mtu).
