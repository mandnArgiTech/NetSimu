title: MTU (Maximum Transmission Unit)
---
# MTU (Maximum Transmission Unit)

**MTU** is the largest IP packet a link can carry without fragmenting. The default for Ethernet is 1500 bytes. *Jumbo frames* push that to 9000 bytes; on a modern data center underlay you almost always want jumbo because of [GENEVE](concept:geneve) overhead.

Here's why it matters in NSX: a VM sends a 1500-byte packet. The host's [TEP](concept:tep) wraps it in GENEVE — adding ~50 bytes — and the result is a ~1550-byte underlay packet. If the underlay link has MTU 1500, that wrapped packet is *too big*: the switch drops it, the kernel logs a fragmentation error, and the original VM-to-VM communication silently fails. From the VM's perspective the network just doesn't work; from the switch's perspective the only signal is `in_errors` going up.

This is the heart of the lab's `mtu_mismatch` scenario. An ansible playbook standardizes a port back to MTU 1500, the GENEVE-wrapped frames start being dropped, the [TEP](concept:tep) loses connectivity to its peers, and the application breaks 60 seconds later. Underlay link is "up", port has no link errors, only `in_errors` is climbing — but unless you know to look at it relative to encapsulation overhead, the connection between cause and effect is invisible.

**Rule of thumb:** MTU on every underlay link from pNIC to ToR to spine should be at least 1700 (the VCF practical minimum), better 9000.

**See also:** [GENEVE](concept:geneve), [TEP](concept:tep).
