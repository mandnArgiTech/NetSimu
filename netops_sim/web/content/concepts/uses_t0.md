title: TGW uses this T0
---
# Transit Gateway uses this T0

The [Transit Gateway](concept:transit_gateway) hands its north-south traffic up to this [T0 gateway](concept:tier0). The T0 is the lab's edge to the outside world — it speaks BGP with the physical fabric and is where NAT happens.

If you trace a packet from a VM out to the internet: VM → segment → VPC → TGW → **T0** → ToR → spine → upstream.
