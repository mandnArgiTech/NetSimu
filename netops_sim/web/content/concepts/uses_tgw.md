title: VPC uses this Transit Gateway
---
# VPC uses this Transit Gateway

The [VPC](concept:vpc) routes east-west traffic via this [Transit Gateway](concept:transit_gateway). The TGW is how the VPC reaches sibling VPCs in the same project, and how it reaches the [T0](concept:tier0) for north-south.

Unlike *has_tgw* (project owns the TGW), this is a usage edge — the VPC *attaches to* the TGW the project provides.
