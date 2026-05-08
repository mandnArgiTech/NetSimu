title: VPC owns this segment
---
# VPC owns this segment

A [VPC](concept:vpc) carves itself into one or more [segments](concept:segment) — overlay subnets, each with its own CIDR and Layer-2 broadcast domain. Every VM lives on exactly one segment.

This is purely a containment edge. The actual data path between VMs on this segment goes through [GENEVE](concept:geneve) and the host [TEPs](concept:tep), not through the VPC object itself.
