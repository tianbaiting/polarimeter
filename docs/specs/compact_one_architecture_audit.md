# CompactInVacuum Architecture Audit

> Status: dated implementation snapshot from 2026-07-29. It is not a requirement authority.
> `compact_one_requirement_baseline.md` and the current resolved deployment configuration supersede
> any conflicting dimension, access, support, or extraction statement below.

## Audit scope

Audit date: 2026-07-29

Implementation branch: `redesign/compact-detector-holder-v2`

Baseline deployments:

- `CompactInVacuum-afterSRC`
- `CompactInVacuum-preSAMURAI`

Preserved external routes remain outside the redesign scope. No file in the legacy afterSRC or SAMURAI-front external implementations is intentionally changed.

## Diagnosis of the superseded design

The former common detector package was mechanically misleading:

- a 5.5 mm active plastic was placed inside a 35 mm nose and 44 mm rectangular cassette;
- the SiPM/optical readout relationship was visually lost inside oversized packaging;
- a long `CassetteThermalBridge` existed to satisfy an abstract graph rather than a credible conductive assembly;
- every detector had its own mount pad, long wall rail, wall anchor, and cylindrical thermal strap;
- the three channels did not form one serviceable sector mechanism;
- temperature sensors, four temperature harnesses, twelve required channels, and a housekeeping feedthrough were treated as mandatory despite no current platform requirement;
- physical objects, keepouts, datums, service paths, and acceptance volumes opened together as one visually confusing assembly.

Passing geometric tests did not make the support manufacturable or the detector package credible.

## Implemented architecture

### Detector head

The detector is now an explicit short axial stack:

`active plastic -> optical coupling -> SiPM package -> sensor PCB/carrier -> rear mounting face`

A thin reflector envelope surrounds the active plastic. A shallow light-tight sleeve and rear face replace the long nose and box. The default housing depth is calculated as 9.70 mm and is below the 18 mm gate. Cable exit and connector keepout remain separately classified and excluded from this depth.

The protruding anti-rotation key initially shadowed a neighboring proton acceptance volume during redesign validation. It was replaced by a rear-flange D-flat and matching nest land.

### Sector holder

Each sector now has one connected carrier plate, three rear nests, three insertion stops, three removable clamp bridges, six simplified M3 fastener envelopes, a common rear cable lane, and one plane–pin–slot chamber interface.

The carrier is relieved against all three complete-disc acceptance volumes. Fasteners are oriented along the local azimuthal tangent so they do not enter a neighboring channel’s cone. Each detector has a 12 mm sampled rearward withdrawal path after clamp release. At the audit date, each sector also had five exact solid poses along a 70 mm radial comparison path. That path has since been superseded for the afterSRC fixed-wall/ICF305 design: current exact poses establish only the first 12 mm support-release stage, not complete translation, reorientation, or lift through the maintenance port.

The displayed extraction boxes are diagnostic overlays. Exact holder solids are used for collision validation.

### Services and thermal semantics

Only rotary and signal service-port roles remain. The dedicated monitoring system and housekeeping feedthrough are removed.

The passive conductive contract follows actual contacting parts:

`SiPM -> carrier -> rear face -> nest -> sector plate -> chamber interface`

No artificial long thermal bridge remains.

### Display architecture

Every generated object is assigned one of seven engineering roles. Only physical and purchased-component/interface objects are visible by default. Keepouts, datums, service centerlines, acceptance volumes, and optional references are hidden.

Documents are grouped by detector head, sector holder, target, services, chamber, keepouts, datums, and physics acceptance as applicable.

## Retained architecture

- Four sectors and three configured channels per sector.
- Twelve active detector faces.
- Target-centered axes and active-center radius semantics.
- Repository channel angles and coincidence pairing.
- Complete target-to-active-disc acceptance construction.
- Target WORK/PARK motion semantics.
- Square and cylindrical deployment chamber candidates.
- Stateful generation and stable geometry metrics.
- Independent afterSRC and pre-SAMURAI deployment generation.
- Legacy external-route isolation.

Both current deployment profiles select square screening chambers: 440 × 440 mm for
afterSRC and 450 × 450 mm for pre-SAMURAI. The former afterSRC cylindrical candidate was
removed by project direction; it is not an active alternative in that deployment profile.

## Schema disposition

Schema version 3 replaces the oversized cassette and procedural cartridge fields with `detector.head` and `sector_holder`.

Removed temperature/housekeeping fields are recursively rejected. They are not accepted as dead configuration and do not produce hidden geometry.

Legacy schema-1 entry-point profiles remain available without a housekeeping block. They are compatibility inputs, not the preferred architecture.

## Validation outcome

The redesigned non-strict FreeCAD validation passes all geometry and engineering-intent checks. Expected warnings remain for unresolved supplier/site/material/pressure-vessel evidence.

The redesigned test intent includes:

- component-complete detector stack;
- SiPM/coupling axial alignment;
- 18 mm housing-depth gate;
- no monitoring geometry or required channels;
- exactly three heads per coherent sector holder;
- no obsolete rails or thermal straps;
- no head/head or holder/holder overlap;
- clear detector-head withdrawal and sampled initial holder release; complete holder extraction is
  deployment-specific and remains unresolved where the current baseline says so;
- no full-acceptance obstruction, including provisional fastener envelopes;
- clear cable/service routes;
- valid solids;
- default role visibility;
- independent deployment generation.

## Unresolved decisions

- Evidence for changing repository `proton_large.angle_deg` from 53.4° toward the previously supplied approximately 55.9° nominal.
- Evidence for changing `proton_small.angle_deg` from 11.2° toward approximately 11.3°.
- PCB/carrier drawing and mounting details.
- Connector, cable exit, and strain-relief selection.
- Reflector and optical-coupling material.
- Final fasteners, tolerances, surface treatment, and survey tooling.
- Chamber closure, tool access, and the complete holder reorientation/lift path.
- Purchased interface drawings, site envelopes, vacuum qualification, and chamber FEA.

The current carrier is a provisional, mechanically defensible concept. It is not a fabrication release.
