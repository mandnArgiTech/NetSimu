title: Project owns this VPC
---
# Project owns this VPC

A [VPC](concept:vpc) belongs to exactly one [NSX Project](concept:nsx_project). The project supplies tenancy boundary, shared services like the [DFW](concept:dfw), and the [Transit Gateway](concept:transit_gateway) the VPC attaches to.

You can have many VPCs in a project (web, app, db tiers — typical) and they all share the project's TGW for east-west traffic.
