title: VM runs on this host
---
# VM runs on this host

The [VM](concept:vm) is currently scheduled on this [ESX host](concept:esx_host). Its CPU, RAM, and vNIC live on that host's hardware until [vMotion](concept:vmotion) or HA moves it.

This relationship is dynamic — when a VM vMotions, the line redraws to the new host. Faults that target the host (pNIC failure, MTU mismatch on its uplinks) hit every VM with this relationship to it.
