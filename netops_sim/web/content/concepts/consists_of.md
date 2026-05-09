title: Application is realized by this VM
---
# Application is realized by this VM

The [application](concept:application) tier — *web*, *api*, *db* — is implemented by this VM (and usually one or two siblings for redundancy). Several VMs of the same tier all "consist of" the same parent application.

When you reason about an outage at the application level, this is the edge that maps it down to the actual VMs you'd ssh into.
