title: NSX Project
---
# NSX Project

An **NSX Project** is a multi-tenant boundary inside an NSX deployment. Think of it as a folder that owns its own [VPCs](concept:vpc), [segments](concept:segment), [DFW rules](concept:dfw_rule), and policy: changes inside a project don't bleed into other projects, and project-scoped admin roles let different teams (or different applications) manage their own networking without stepping on each other.

In NetSimu the single project (`proj-app`) owns the application VPCs, the segments, the DFW rules, and connects to the [Transit Gateway](concept:transit_gateway) (which connects to the [Tier-0](concept:tier0)). All of NetSimu's workloads live in this one project — but in production VCF you might see one project per business unit, or one per environment (dev/test/prod), with a separate Transit Gateway peered in.

Projects are a relatively new concept (VCF 9.0 era). Older NSX deployments used a flat model where everything shared one global namespace; projects let you slice that up cleanly.

**See also:** [VPC](concept:vpc), [Transit Gateway](concept:transit_gateway), [DFW](concept:dfw).
