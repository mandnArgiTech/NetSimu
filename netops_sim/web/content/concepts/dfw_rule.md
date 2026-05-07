title: DFW rule
---
# DFW rule

A **DFW rule** is a single line of policy in the NSX [Distributed Firewall](concept:dfw). Each rule has a *source* (a segment, a security group, or `any`), a *destination*, a *port/protocol*, an *action* (allow or deny), and a *priority* (lower number = evaluated first).

NetSimu's three default rules implement the canonical app dependency chain: rule 100 allows web → api on port 8080, rule 110 allows api → db on port 5432, rule 999 denies everything else to db. The `dfw_rule_break` scenario flips rule 100 from allow to deny — and the consequences are visible immediately: web → api connections start failing, the application latency climbs, but the underlay and overlay show no errors at all. The only diagnostic signal is the audit log entry showing the rule was changed.

This is what makes DFW debugging hard: the whole point of an effective firewall is that the network looks healthy. You have to know to look at the policy plane (rule changes, hits, denies) instead of the data plane to find the cause.

**See also:** [DFW](concept:dfw), [segment](concept:segment).
