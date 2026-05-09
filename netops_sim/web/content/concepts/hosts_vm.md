title: Host runs this Edge VM
---
# Host runs this Edge VM

An [NSX Edge node](concept:nsx_edge) is itself a VM — it is just packaged as the appliance that runs T0 services. This edge says which [ESX host](concept:esx_host) the Edge VM currently lives on.

If that host fails, NSX HA fails the Edge over to a sibling host (assuming you ran more than one Edge — and you should). North-south traffic blips for a few seconds.
