# CLAUDE.md — NetSimu project context

This file is read by Claude Code at the start of every session. It encodes
the persistent context, design decisions, and operating rules for working
on NetSimu so we don't repeat conversations across sessions.

---

## Project at a glance

**NetSimu** is a visual learning lab for VMware Cloud Foundation (VCF) and
NSX networking, built primarily for engineers learning these concepts for
the first time. The lab teaches by showing the topology and by letting the
user break it. The audience is **layman to VCF** — pretend nothing is
obvious, label everything, explain everything in plain language.

The companion project is **NetRCA** (separate repo, similar structure) — a
rule-augmented Bayesian RCA engine that consumes NetSimu's telemetry. NetRCA
is out of scope for the current milestones.

---

## Current state (where we're starting from)

The codebase as of MVP-2 is a Python simulator with a CLI:

- `netops_sim/` — a discrete-event simulator with virtual clock, event bus,
  and behavior state machines for switch ports, pNICs, TEPs, and BGP sessions.
- 6 fault scenarios in `netops_sim/scenarios.py`: mtu_mismatch, bgp_flap,
  silent_packet_loss, tep_ip_collision, dfw_rule_break, pnic_failure_vmotion.
- A reference topology in `netops_sim/topology.py`: 2 spines, 4 ToRs (mixed
  Cisco N9K + Arista 7050), 8 ESX hosts, NSX overlay (T0, TGW, project, VPCs,
  segments), 7 VMs across 3 application tiers.
- Distractor noise generator (`distractors.py`), topology snapshotter
  (`snapshots.py`), vMotion helpers (`vmotion.py`).
- Mock APIs (NSX Policy, Cisco NX-API, gNMI WebSocket) in `netops_sim/emitters/`.
- 28 tests in `tests/`, all passing.
- The CLI entry point is `python -m netops_sim.runner <scenario>`.

**Run `make test` to confirm the baseline still passes before any change.**

---

## What we're building next: the Visual Lab

A browser-based interactive lab. Read `docs/netsimu_visual_lab.md` for the
full design before doing anything else — it's the source of truth for scope,
layout, and milestone breakdown.

The short version: backend is FastAPI + WebSocket on top of the existing
Python simulator. Frontend is React + Cytoscape.js, single page, served
locally on `localhost:8000`. User runs `netsimu web`, opens browser, sees
labeled topology, hovers/clicks for explanations, breaks things from a
"Break Something" panel, watches cascades unfold in real time with narrated
explanations.

### Milestone order (do not skip ahead)

1. **M1** — Static topology rendered in browser (light theme, large fonts)
2. **M2** — Hover tooltips + click-for-details panel
3. **M3** — Live data wiring (WebSocket) + counters
4. **M4** — 6 built-in faults injectable + cascade narration
5. **M5** — Geneve packet flow animation (the pedagogical core)
6. **M6** — Concept Tour mode (guided 12-lesson walkthrough)
7. **M7** — Polish + onboarding doc
8. **M8** — Custom fault builder
9. **M9** — Custom topology editor (drag-create)
10. **M10** — Export to PNG/PDF
11. **M11** — NetRCA integration tab

Do NOT implement M2 until M1 is reviewed and committed. Each milestone is
its own branch + PR-style commit. **Demonstrate working end-to-end after
each milestone before moving on.**

---

## Hard rules (non-negotiable)

These are decisions already made. Do not relitigate them in new sessions.

1. **Light theme only.** No dark mode. Ever. White / off-white backgrounds,
   dark text. Color-coded layers: muted blues for physical fabric, teals for
   overlay, greens for application, red/amber for fault states.

2. **Large readable fonts.** Body 16px minimum. Headings 20-32px. No 11px,
   12px, 13px, 14px text anywhere — not in tooltips, not in legends, not in
   metric tiles, not in code blocks. If something doesn't fit at 16px,
   redesign the layout, don't shrink the font.

3. **Plain-language educational content.** All tooltips and panel content
   must be readable by someone who has never seen VCF before. Avoid jargon
   without definition. Cross-link concepts ("see also: TEP, GENEVE").

4. **No "ship it without testing"**. Every milestone has a working demo
   path: open browser, do X, see Y. If it doesn't work end-to-end, it's
   not done.

5. **Don't write code without confirming the plan.** At the start of each
   milestone, summarize what you're about to do, list the files you'll
   touch, and wait for "go ahead". This is a learning project — surprises
   defeat the point.

6. **Existing CLI/Python tests must still pass.** The web UI is a layer on
   top of the simulator, not a replacement. Run `make test` before and
   after every change. If a test breaks because of a refactor, fix the
   test in the same commit.

7. **No browser localStorage / sessionStorage / cookies for app state.**
   The lab runs locally; state lives in Python (via WebSocket) or in
   React component state. Use real backend round-trips, not browser
   persistence.

8. **No external CDN dependencies that aren't pinned.** If you load a JS
   library, pin the exact version. We don't want a Cytoscape.js update to
   break the lab silently.

---

## Style decisions already made

- **Visual style**: clean professional light theme, between VMware vSphere
  client and AWS console aesthetics. No flashiness, no animations for their
  own sake. Animation only when it teaches something.
- **Tour text style**: senior engineer explaining over coffee for tooltips
  and quick reads (informal, opinionated, anecdotal); textbook-precise for
  deep-dive panels (formal, complete, with diagrams).
- **Animation speed**: 2-3× simulated-time-to-wall-clock by default, with
  slider 1× to 10×.
- **Layered topology**: physical at bottom, overlay above it, applications
  at the top. Cytoscape.js with `dagre` or `cose-bilkent` layout, locked
  per layer.
- **Vendor icons**: real Cisco N9K and Arista 7050 silhouettes for ToRs,
  VMware ESX host icons. Either ship as bundled SVGs or use the
  Network-Topology-Icons project (verify license first).

---

## Project layout we're heading toward

```
NetSimu/
├── netops_sim/                  # existing simulator (MVP-2)
│   ├── clock.py
│   ├── topology.py
│   ├── entities.py
│   ├── ...
│   └── web/                     # NEW: web layer
│       ├── server.py            # FastAPI + WebSocket
│       ├── routes.py            # REST endpoints
│       ├── stream.py            # WebSocket event multiplexer
│       └── content/             # Markdown educational content
│           ├── concepts/
│           │   ├── tep.md
│           │   ├── vpc.md
│           │   ├── geneve.md
│           │   └── ...
│           └── tour/
│               ├── 01-underlay.md
│               ├── 02-esx-host.md
│               └── ...
├── frontend/                    # NEW: React + Cytoscape.js
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── topology/            # Cytoscape config
│   │   ├── panels/              # detail, break, tour panels
│   │   ├── timeline/            # bottom timeline
│   │   └── styles/              # light-theme tokens
│   └── public/
│       └── icons/               # vendor SVGs
├── tests/                       # existing tests + new
├── docs/
│   ├── netsimu_visual_lab.md    # design doc (READ THIS FIRST)
│   └── architecture.md
├── pyproject.toml
├── Makefile
└── CLAUDE.md                    # this file
```

---

## Operational discipline

### Commits and pushes

Every milestone gets its own branch:
```
git checkout -b m1-static-topology
# ... work, test, demo ...
git add -A
git commit -m "M1: static topology rendered in browser"
git push -u origin m1-static-topology
```

Then merge to main only after the user has reviewed and confirmed the
milestone is done. Use `gh pr create` if `gh` is installed; otherwise
provide the GitHub URL for the PR creation page. The user is
**Devi Prasad** at mandnArgiTech.

Commit messages: imperative mood, milestone tag in subject, short body
explaining what was added/changed/why.

### Tests

- Existing tests in `tests/` must always pass. Run `make test` before any
  change, after any change, and before any commit.
- New web layer needs its own test directory: `tests/web/`. Use FastAPI's
  TestClient + a frontend smoke test (`npm test` or `playwright` for the
  UI smoke test in M5+).
- Don't add tests that require a live browser unless absolutely necessary
  for a milestone — they're slow and flaky.

### Dependencies

- Python: add to `pyproject.toml`, document why in the commit message.
- JS: pin exact versions, no `^` or `~`. Use `npm ci` not `npm install` in
  build steps.
- Don't add a heavy dependency without a justification in the commit
  message — "I want this library" is not a justification.

---

## What to do at the start of each new Claude Code session

1. Read `docs/netsimu_visual_lab.md` if you haven't this session.
2. Run `git status` and `git log --oneline -10` to see where things stand.
3. Run `make test` to confirm baseline is green.
4. Ask the user "what milestone are we on, and what's the next concrete
   step?" — don't assume.
5. Don't write code until you've confirmed the plan.

---

## What NOT to do

- Don't add a dark mode "for completeness" — it'll get used.
- Don't shrink fonts to fit more on screen — redesign instead.
- Don't add "AI/LLM features" to the lab. The lab teaches VCF; LLM-powered
  RCA narrative is NetRCA's job, in a separate repo.
- Don't refactor the existing simulator unless required by the milestone.
- Don't pull in a UI framework that isn't React — Vue/Svelte/Solid are all
  fine technically but the team isn't using them.
- Don't deploy to the cloud. NetSimu runs locally only.
- Don't add authentication. Internal tool, single user per machine.
- Don't add analytics or telemetry phone-home. Anywhere. Ever.

---

## Key concepts the lab needs to teach (the foundation list)

This is the curriculum. Every concept here needs a tooltip, a deep-dive
panel, and a place in the Concept Tour. If you find yourself adding UI for
a concept not on this list, ask first.

**Underlay (physical fabric):**
- Spine switch · ToR (top-of-rack) switch · pNIC · cable · LAG/bond
- VLAN · trunk · access port · MTU · jumbo frames
- BGP · BGP session · ASN · route reflector · prefix advertisement

**Hypervisor + transport:**
- ESX host · cluster · vCenter · vMotion · HA · DRS
- vSwitch · DVS (distributed virtual switch) · port group
- VMkernel adapter · TEP (tunnel endpoint)

**NSX overlay:**
- Transport zone · transport node
- GENEVE · encapsulation · overlay vs underlay
- Segment · logical switch · CIDR
- Tier-0 gateway · Tier-1 gateway · Edge node · Edge cluster
- NSX Project · VPC · Transit Gateway (centralized vs distributed)
- Distributed Firewall (DFW) · DFW rule · security group
- N-S vs E-W traffic

**Operations:**
- Telemetry · counters vs gauges · syslog · audit log
- Realization state · alarms · health check
- vMotion event · HA failover · maintenance mode

If a concept on this list isn't yet covered in the lab, surface that as
a TODO. Do not invent extra concepts beyond this list without asking.

---

## When in doubt

Ask. This is a learning tool for someone learning VCF for the first time —
guessing wrong about pedagogy or visual style wastes more time than asking.
The user explicitly prefers being asked over being surprised.
