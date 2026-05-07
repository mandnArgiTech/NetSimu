title: VPC
---
# VPC

An **NSX VPC** is a self-contained virtual network inside a [Project](concept:nsx_project). It owns a CIDR range, a set of [segments](concept:segment), and its own DHCP and NAT settings. VPCs in NSX are deliberately modeled after AWS VPCs — same mental model, same boundaries: workloads inside a VPC can talk to each other; talking outside the VPC requires going through the [Transit Gateway](concept:transit_gateway).

NetSimu has three VPCs (web, api, db) for the canonical three-tier app — each owns one or two segments, each VPC's CIDR is a /24, and they connect to one another through the project's TGW. This separation is how the [DFW](concept:dfw) policy enforces *web can talk to api*, *api can talk to db*, *web can NOT talk directly to db*: the rules are written in terms of segment-to-segment paths, and the VPC structure makes those paths well-defined.

In practice you'll often see one VPC per logical application or one per data classification level. The exact slicing is a policy decision — VPCs are cheap, so default to more of them rather than fewer.

**See also:** [segment](concept:segment), [Transit Gateway](concept:transit_gateway), [DFW](concept:dfw).
