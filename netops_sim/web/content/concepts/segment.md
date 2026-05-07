title: Segment
---
# Segment

A **segment** is the NSX equivalent of a Layer 2 broadcast domain — it's the logical network a VM gets attached to. From the VM's perspective, every other VM on the same segment is on the same subnet, reachable via ARP, no routing needed. The trick is that those VMs can be running on entirely different ESX hosts in entirely different racks; the [TEP](concept:tep) layer makes them appear adjacent.

A segment has a CIDR (the IP range available to attached VMs), it lives inside a [VPC](concept:vpc), and it's *encapsulated* by every TEP pair in the relevant transport zone. When you attach a VM to a segment, the VM's traffic is wrapped in [GENEVE](concept:geneve) at the source TEP and unwrapped at the destination TEP — that's how the illusion of "same subnet across a routed underlay" is maintained.

NetSimu has four segments: `seg-web`, `seg-web-priv` (in vpc-web), `seg-api` (in vpc-api), `seg-db` (in vpc-db). The [DFW](concept:dfw) rules govern which segments can talk to which.

**See also:** [VPC](concept:vpc), [TEP](concept:tep), [GENEVE](concept:geneve), [DFW](concept:dfw).
