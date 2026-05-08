title: Project owns this Transit Gateway
---
# Project owns this Transit Gateway

An [NSX Project](concept:nsx_project) has exactly one [Transit Gateway](concept:transit_gateway) — the hub that all the project's [VPCs](concept:vpc) attach to.

This is a containment relationship: the TGW is *part of* the project, not a peer of it. If the project is deleted, the TGW goes with it.
