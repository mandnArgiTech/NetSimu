# NetSimu Visual Lab — Design Doc

**Audience:** Devi + teammates at mandnArgiTech.
**Goal:** A browser-based interactive lab that teaches VCF/NSX networking by showing it, then by breaking it. Same backend supplies data to NetRCA when you're ready to move on.
**Out of scope:** Public hosting, multi-tenant access control, customer-facing branding. This is internal teaching infrastructure first.

---

## 1. The 30-second first-time experience

You install one Python package, run `netsimu web`, browser opens to `localhost:8000`.

You see:

- A clean light-theme page with the title "NetSimu — VCF Lab" (≥16px body text — see CLAUDE.md style rules).
- The center is a **single layered topology diagram** of a small but realistic VCF deployment: 2 spines, 4 ToRs (mixed Cisco/Arista), 8 ESX hosts, NSX overlay (T0, TGW, VPCs, segments), VMs grouped into three application tiers.
- Layers are visually distinct — physical fabric at bottom in muted blue, ESX/pNIC layer in muted slate, NSX overlay in teal, applications at the top in green. Connections drawn as labeled lines.
- Vendor icons: real Cisco N9K silhouettes for the Cisco ToRs, Arista 7050 for Arista, VMware ESX hosts, NSX Edge appliances. Cables as thin lines, BGP sessions as thicker lines with "BGP" labels.
- A right-side panel says "Welcome. Hover anything to learn what it is. Click anything for a deep dive. Or jump straight into the Concept Tour →"
- A persistent **"Break Something"** panel on the left with a list of faults you can inject.
- A timeline ribbon at the bottom, currently empty ("nothing has happened yet").

Within 30 seconds, even without clicking anything, you should be able to:
- Tell that there are layers (physical → overlay → application).
- See where NSX "sits" relative to the underlay.
- See that VMs live on hosts and are attached to segments inside VPCs inside an NSX project.

---

## 2. Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ NetSimu — VCF Lab                                  [Concept Tour] [⚙]   │
├──────────────┬───────────────────────────────────────────┬──────────────┤
│              │                                           │              │
│ BREAK        │           TOPOLOGY CANVAS                 │   DETAIL     │
│ SOMETHING    │                                           │   PANEL      │
│              │     (Cytoscape-rendered, layered)         │              │
│ ┌──────────┐ │                                           │  When you    │
│ │ MTU      │ │       app-web   app-api   app-db          │  hover or    │
│ │ mismatch │ │          ◯─────────◯─────────◯            │  click, the  │
│ │  ▶ Run   │ │      ⬢       ⬢       ⬢       ⬢           │  detail of   │
│ └──────────┘ │     vm   vm   vm   vm                     │  that entity │
│ ┌──────────┐ │     │    │    │    │                      │  appears     │
│ │ BGP flap │ │     ▣────▣────▣────▣ ESX hosts            │  here, with  │
│ │  ▶ Run   │ │     │/  \│/  \│/  \│                      │  educational │
│ └──────────┘ │     ╳    ╳    ╳    ╳                      │  text and    │
│ ┌──────────┐ │     ┌──┐  ┌──┐  ┌──┐  ┌──┐                │  diagrams.   │
│ │ DFW deny │ │     │T1│  │T2│  │T3│  │T4│ ToRs           │              │
│ │  ▶ Run   │ │     └─┬┘  └─┬┘  └─┬┘  └─┬┘                │  Switches    │
│ └──────────┘ │       │     │     │     │                 │  to "What    │
│              │      ┌┴─────┴┐  ┌─┴─────┴┐                │  just        │
│  …more…      │      │  S1   │  │   S2   │ Spines         │  happened?"  │
│              │      └───────┘  └────────┘                │  during a    │
│              │                                           │  fault.      │
│              │                                           │              │
├──────────────┴───────────────────────────────────────────┴──────────────┤
│                          TIMELINE  (events, color-coded by layer)       │
│  ──────────●──────●●●●●●─●──────────●●●●●●●●●●●─────────────●──         │
│        config-chg   port errs    tep drops   app degraded               │
│  [▶ Live]  [⏸ Pause]  [↺ Reset]                  Sim time: 02:14        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. The four ways to interact

### 3a. **Hover** — the one-liner

Any element. Tooltip appears in 200ms. Example tooltips:

- *(spine-01)* — "Spine switch. Top-of-fabric router. Forwards traffic between ToRs at line rate."
- *(tor-01)* — "Top-of-rack switch (Cisco N9K). All hosts in rack-01 connect here. Peers BGP with the NSX Tier-0."
- *(tep-host-01)* — "Tunnel Endpoint. Wraps VM traffic into Geneve packets so the underlay can carry it. IP: 10.20.0.11."
- *(seg-web)* — "NSX overlay segment. Logical network — has a CIDR, does not exist on any physical switch."
- *(bgp-t0-tor-01)* — "BGP session between NSX Edge T0 (ASN 65100) and tor-01 (ASN 65001). Currently Established."

### 3b. **Click** — the deep dive

Side panel opens. Tabbed:

| Tab | Contents |
|---|---|
| **What is this?** | 2–4 paragraphs of plain-English explanation. Diagrams where useful. Cross-links: clicking "see also: GENEVE" replaces the panel content. |
| **Live data** | Real-time charts of this entity's metrics. Counters, state, recent events. |
| **Connections** | List of every edge in/out of this entity, annotated. "Connects to: pnic-host-01-vmnic0 via cable cab-r1-001." Clicking a connection moves focus to that entity. |
| **In context** | A miniature focused diagram showing just this entity and its 2-hop neighborhood, with the data path highlighted. |

### 3c. **Break Something** — the fault injector

Left panel. Each fault is a card with:
- A name and one-line description.
- A "▶ Run" button.
- An optional difficulty badge ("Easy / Medium / Hard").
- A "What's it teach?" expandable showing which concepts the fault illustrates.

Faults available at launch (mapped to the 6 NetSimu scenarios you already have):

| Card | Teaches | Difficulty |
|---|---|---|
| **MTU mismatch** | Underlay vs overlay, Geneve overhead, why MTU matters | Easy |
| **BGP session flap** | Routing, T0 ↔ ToR peering, route propagation | Medium |
| **Silent CRC corruption** | Why "no link-down" doesn't mean "no problem" | Hard |
| **TEP IP collision** | Overlay-only faults, clean underlay paradox | Medium |
| **DFW rule break** | NSX security plane, why infra metrics can be clean | Hard |
| **Dual pNIC failure + vMotion** | HA, host isolation, topology that mutates mid-incident | Medium |

Click "Run" → confirmation modal: *"This will inject the [MTU mismatch] fault on [port-tor-01-host-01-vmnic0] in 5 seconds. The cascade will play out over ~3 minutes of simulated time. You'll see counters change, the topology turn red, and the timeline fill in. Continue?"* → button "Inject Now".

### 3d. **Concept Tour** — the guided walkthrough

A linked sequence of "lessons" — each is a topology highlight + side-panel content + optional fault injection.

The full tour, in order:

1. **The Underlay** — highlights spines + ToRs + cables. Explains the physical fabric exists independently of NSX.
2. **The ESX Host** — highlights one host, its pNICs, the cluster.
3. **VLANs and Trunks** — shows how pNICs carry multiple VLANs (mgmt, vMotion, TEP, etc.).
4. **BGP** — highlights the BGP sessions, explains underlay routing.
5. **The TEP** — *the most important lesson.* Highlights one TEP, animates a Geneve-encapsulated packet flowing from VM through TEP, through pNIC, through ToR, through spine, back through another ToR, to another TEP, to the destination VM. Pauses at each step with explanation.
6. **The Overlay Segment** — highlights one segment. Shows that VMs on the same segment can be on different hosts but think they're on the same Layer 2.
7. **The VPC** — highlights one VPC and its segments. Explains the AWS-style abstraction.
8. **The Tier-0 and Edge** — highlights how the overlay reaches the outside world.
9. **The Transit Gateway** — for VCF 9.0 users.
10. **The DFW** — highlights firewall rules as overlay objects, not underlay.
11. **Putting it together** — a "trace this packet" exercise. Click a VM, click a destination, watch the full path animate.
12. **Lesson 12+: each fault scenario** — guided walk through what each fault breaks and why it cascades.

Each lesson is ~2-3 minutes. Whole tour is ~45 minutes. Skip anywhere; resume anywhere.

---

## 4. The animation that does the heavy lifting

One specific animation is worth describing in detail because it's the pedagogical core:

**The Geneve tunnel animation.** When traffic flows between two VMs on different hosts, the visualization shows:

1. A small "packet" dot leaves the source VM.
2. It moves to the host (the ESX rectangle).
3. As it crosses into the host, it visibly "wraps" — a halo appears around it, labeled "Geneve". The dot now shows two layers.
4. It travels through the pNIC (label flashes "VLAN 1647 — TEP").
5. Down to the ToR (the ToR's port flashes briefly).
6. Up the underlay path — to spine, to other ToR, etc. The underlay path is highlighted as it traverses.
7. Arriving at the destination host's pNIC, the halo strips off and the original VM packet is delivered.

When NORMAL: this happens subtly in the background, low opacity, easy to ignore.
When you click "show packet flow" on any VM-to-VM pair: it animates clearly, slowly, with explanations.
When BROKEN: the packet visibly *fails* at the broken point — a red flash, a "✗" mark, a tooltip explaining "MTU exceeded — Geneve frame is 1750 bytes, link MTU is 1500."

This single animation is what makes overlay-vs-underlay click in someone's head.

---

## 5. The cascade visualization

When a fault is injected, the topology doesn't just turn red somewhere — it *narrates* the cascade.

Sequence (using MTU mismatch as the example):

- **t=0** (fault injected): the affected switch port pulses orange briefly, with a small popup "Config change: MTU 9216 → 1500 by netadmin@corp". A timeline marker appears.
- **t=10s**: the port turns yellow as input errors start accumulating. Tooltip appears: "input errors growing — 1,200/sec." Yellow propagates upstream toward the ToR.
- **t=20s**: the affected TEP turns yellow, then red. A dashed Geneve tunnel from this TEP to its peers visibly flickers and breaks. Affected segments highlight in red.
- **t=40s**: VMs on those segments start showing "degraded" badges. Application icons turn yellow.
- **t=60s**: the application icon turns red. A small chart in the side panel shows latency and 5xx rate climbing.

Throughout, the right-side panel auto-switches to **"What just happened" mode** and writes a running explanation:

> ### Cascade in progress: MTU mismatch
>
> **Step 1 (just now):** The MTU on `port-tor-01-host-01-vmnic0` was changed from 9216 to 1500 by netadmin@corp. This is the underlying cause.
>
> **Step 2 (10s ago):** Geneve-encapsulated overlay traffic from `tep-host-01` is roughly 1750 bytes per packet. The new 1500-byte MTU drops them. The switch port's `in_errors` counter reflects this.
>
> **Step 3 (20s ago):** With one of its two uplinks failing, `tep-host-01` is losing about half its overlay traffic. Geneve tunnel pairs to other hosts are flaky.
>
> **Step 4 (now):** VMs on segments encapsulated through this TEP can't reliably talk to peers on other hosts. `app-web` is failing because it can't reach `app-api`.
>
> Want to verify? Click any of the highlighted entities to see its current metrics. Or open the Timeline to scrub back through the events.

This is the "build-by-breaking" payoff. You're not reading a textbook about MTU — you watched it kill an application in 60 seconds.

---

## 6. Technical architecture

### Backend — Python, builds on what we have

```
┌────────────────────────────────┐
│  Existing NetSimu engine       │
│  (clock, topology, behaviors,  │
│   scenarios, event bus)        │
│  ── unchanged from MVP-2 ──    │
└─────────────┬──────────────────┘
              │
              │  events
              ▼
┌────────────────────────────────┐
│  netsimu/web/server.py         │
│  FastAPI + WebSockets          │
│                                │
│  - GET /api/topology     →     │
│      initial topology JSON     │
│  - WS /api/stream        →     │
│      live event stream         │
│  - POST /api/inject      →     │
│      trigger a fault scenario  │
│  - POST /api/reset       →     │
│      reset to clean state      │
│  - GET /api/concept/{id} →     │
│      educational text +        │
│      diagrams for a concept    │
└────────────────────────────────┘
```

The web server runs the simulator in real-time mode (the simulator already supports this via the `--real-time` flag I built earlier). Events flow over WebSocket to the browser as they're produced.

### Frontend — React + Cytoscape.js, single page

```
┌────────────────────────────────────────────────────────┐
│ index.html — loads React + Cytoscape + a single bundle │
└────────────────────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   Topology        Detail Panel    Timeline
   (Cytoscape)     (Markdown +     (D3 or
                    charts)         lightweight)
```

- **Cytoscape.js** for the topology canvas. Chosen over D3 because Cytoscape has built-in graph layout, custom nodes, animation primitives, and a much shorter learning curve for graph rendering. It's the right tool for this job.
- **Tailwind CSS** for styling. Light theme only — no dark mode (see CLAUDE.md hard rules).
- **No backend framework dependency in the browser** — plain `fetch` and WebSocket. The whole frontend is one ~2000-line bundle.
- **Educational content as Markdown files** (one per concept) that the backend serves. Easy to edit without recompiling.

### Why these choices

I considered three alternatives and rejected them:

- **Vis.js / Sigma.js instead of Cytoscape**: weaker for the layered-network use case. Cytoscape has node grouping and compound nodes that we'll need for the host-contains-VMs visualization.
- **A full SPA framework (Vue/Svelte)**: unnecessary; React covers it and you and your team likely have at least passing familiarity.
- **A "real" 3D visualization (Three.js)**: looks impressive in demos, terrible for actually understanding networks. A clean 2D layered graph beats a swooping 3D mess every time. (I looked at this seriously.)

### How it deploys

`pip install netsimu`, then `netsimu web` spins everything up on `localhost:8000`. Self-contained. No npm install, no docker. Bundle ships pre-built. Your teammates do the same.

If you want to share with teammates remotely, you can either:
- (a) Each runs locally — simplest, recommended for now.
- (b) Run on a shared box, share a URL — works fine, no auth needed for internal use.

---

## 7. What I'd cut from scope

Things I'd push to v2 in service of getting v1 done:

- ❌ Custom topology editor (you can't drag-create new topologies in the UI yet — the reference topology is fixed for v1).
- ❌ Multi-user editing.
- ❌ Save/restore a particular incident state for sharing.
- ❌ Export to image / PDF.
- ❌ Custom faults beyond the 6 built-in scenarios.
- ❌ NetRCA integration in the same UI.

NetRCA integration is a v2 feature — once you and the team are comfortable with VCF concepts, the next milestone adds the "show NetRCA's guess on the topology" overlay.

---

## 8. What "done" looks like

You and a teammate sit down. Within an hour:
- You can both navigate the topology and explain to each other what each layer does.
- You've each injected at least three faults and watched the cascades.
- You can both correctly explain what GENEVE is, what a TEP is, and why MTU matters for overlay networks — without looking at notes.
- You've completed the Concept Tour at least once.

That's the bar.

---

## 9. Build plan

Roughly two weeks of focused work, broken into milestones I can deliver one at a time:

| Milestone | Deliverable | Days |
|---|---|---|
| **M1. Static topology rendered in browser** | You open localhost, see the diagram with proper icons and labels, no interactivity yet | 2 |
| **M2. Hover tooltips + click-for-details** | Educational content for every entity type. The tour can be navigated. | 2 |
| **M3. Live data wiring** | Backend WebSocket streams events; frontend animates counters and updates state | 2 |
| **M4. Fault injection + cascade narration** | All 6 faults injectable from the UI; cascades animate and narrate themselves | 2 |
| **M5. Geneve packet flow animation** | The crown-jewel animation that teaches overlay vs underlay | 1 |
| **M6. Concept tour mode** | Guided sequence through all 12 lessons | 2 |
| **M7. Polish + docs** | Onboarding doc, README, video walkthrough so teammates can self-onboard | 1 |

**Total: ~12 working days.** Each milestone is independently demonstrable — after M1 you have something to show; after M3 you have something useful.

---

## 10. Open questions for you before I start coding

Three things I want your input on. Be specific or I'll guess wrong.

1. **Visual style.** Reference points: VMware's vSphere client (clean professional, light, lots of metric tiles) and the AWS console aesthetic (light, dense, navigable). The lab uses a clean light theme with muted layer colors — diagram-forward, no chrome, ≥16px text everywhere (CLAUDE.md hard rule).

2. **Concept tour text style.** Should the educational content read more like (a) a textbook chapter (precise, formal, complete), (b) a senior engineer explaining over coffee (informal, anecdotal, opinionated), or (c) something in between? My instinct: (b) for the tooltips and quick reads, (a) for the deep-dive panels.

3. **Real-time speed.** The simulator can run at 1× (wall clock) or 10× (10 minutes simulated in 1 minute). For the cascade animations, what feels right? My instinct: **2-3× real-time by default** — fast enough to not feel boring, slow enough that you can read the narration as it unfolds. Speed slider available.

If you say "you decide on all three," I'll go with my instincts above and we move on.

---

## 11. What's next

You read this doc. You tell me:

- Yes, build this → I start with M1 (static topology in browser).
- Almost — change X → I revise the doc, then start.
- Wrong direction → we talk about why and reset again.

I will NOT write code until you've signed off on this.
