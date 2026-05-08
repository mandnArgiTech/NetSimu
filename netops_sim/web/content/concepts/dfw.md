title: Distributed Firewall (DFW)
---
# Distributed Firewall (DFW)

The **DFW** is NSX's stateful firewall, with one critical twist: it's *distributed*. Instead of a few centralized firewall appliances that all traffic has to traverse, every ESX host runs a piece of the firewall in its own vSwitch. When VM-A on host-01 talks to VM-B on host-02, the DFW rule check happens at the source host's vSwitch — before the packet even leaves the host.

This means:

1. **East-west traffic gets filtered without hairpinning** through a central appliance. Latency stays low, throughput stays high, the policy applies even between two VMs on the same host.
2. **The data plane looks clean when DFW blocks something.** No port counters increment, no underlay errors, no [TEP](concept:tep) drops — the packet just gets discarded by the source host's filter and never enters the wire.
3. **Debugging is harder than with a centralized firewall.** You can't tcpdump on a single chokepoint and see all denied packets. You have to look at per-host DFW logs, or NSX's policy realization state, or audit logs of recent rule changes.

NetSimu's `dfw_rule_break` scenario flips the web→api allow rule to deny. The result: web tier 5xx errors climb, api connection counts crash to zero, but every underlay and overlay metric is pristine. Only an audit log entry tells you the rule changed. That's the realistic shape of DFW-caused incidents — and why audit-log integration is non-negotiable in any serious NSX deployment.

**See also:** [DFW rule](concept:dfw_rule), [segment](concept:segment), [VPC](concept:vpc).
