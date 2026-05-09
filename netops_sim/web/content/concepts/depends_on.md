title: Application dependency
---
# Application dependency

Tier A "depends on" tier B when A's traffic flows to B — e.g. **web → api → db**. The lab uses this to show blast radius: break something on the **db** path and you should see **api** and then **web** start to fail too.

This is purely a logical relationship between [applications](concept:application). It doesn't pin the network path, just the call graph.
