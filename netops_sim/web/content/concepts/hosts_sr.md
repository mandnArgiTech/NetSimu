title: Edge runs this T0 service router
---
# Edge runs the T0 service router

A [T0 gateway](concept:tier0) has a "service router" component that does the heavy stateful work — north-south routing, NAT, BGP peering with the physical fabric, load balancing. That service router runs on this [Edge node](concept:nsx_edge).

In production you'd run an active-standby pair across two Edges so failure of one Edge doesn't black-hole north-south traffic.
