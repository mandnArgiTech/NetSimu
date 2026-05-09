title: Application
---
# Application

An **application** in NetSimu is a logical grouping of [VMs](concept:vm) that together provide a service. NetSimu models the canonical three-tier app: `app-web` (front-end VMs that serve HTTP), `app-api` (mid-tier VMs that handle business logic), `app-db` (database VMs).

The dependency chain is `app-web → app-api → app-db`: the web tier calls the api tier on port 8080, the api tier calls the database tier on port 5432. When any tier degrades — slow queries, failed connections, [DFW](concept:dfw) rule blocking traffic — the upstream tier degrades with it. That cascade is what makes the lab's fault scenarios end with "the application is broken" rather than just "this network counter is high."

Applications aren't really NSX objects; they're a useful abstraction for talking about *the thing the user cares about* on top of the NSX/VCF infrastructure. The lab uses them to make the impact of underlay/overlay faults concrete: an MTU mismatch on a switch port doesn't sound dramatic, but watching it kill `app-web` 60 seconds later in real time does.

**See also:** [VM](concept:vm), [segment](concept:segment), [DFW](concept:dfw).
