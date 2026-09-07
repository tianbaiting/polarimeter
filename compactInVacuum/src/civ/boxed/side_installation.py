from __future__ import annotations

from .geometry import V, moved
from .deployment import chamber_environment, flatten, vector
from .motion import Phase, VoidRegion, certify_phase
from .deployment_validation import collisions
from .validation import contact_area


def side_void_candidates(f, s):
    c = f.base.chamber.candidate
    passage = f.base.chamber.keepouts[
        "MaintenanceAccessOpenPassage"
    ].optimalBoundingBox(False, False)
    box = VoidRegion(
        "box",
        (
            -c.inner_size_x_mm / 2,
            c.inner_size_x_mm / 2,
            -c.inner_size_y_mm / 2,
            c.inner_size_y_mm / 2,
            c.center_z_mm - c.length_mm / 2 + c.wall_thickness_mm,
            c.center_z_mm + c.length_mm / 2 - c.wall_thickness_mm,
        ),
    )
    port = VoidRegion(
        "cylinder_x",
        (
            (passage.YMin + passage.YMax) / 2,
            (passage.ZMin + passage.ZMax) / 2,
            passage.YLength / 2,
            -c.inner_size_x_mm / 2,
            s.grip_rod_length_mm + s.lift_mm + 2000,
        ),
    )
    return {
        "ProjectChamberBody": [box, port],
        **{
            n: [port]
            for n in (
                "MaintenanceAccessProjectWeldNeck",
                "MaintenanceAccessProjectWeldBead",
                "MaintenanceAccessFixedICFFlange",
            )
        },
    }


def validate_support_installation(f, s, q, check, voids):
    removable = set(flatten(f.support_bodies)) | set(flatten(f.mount_bolts))
    fixed = {n: sh for n, sh in chamber_environment(f).items() if n not in removable}
    results = []
    complete = True
    for sector in ("left", "down", "up", "right"):
        bodies = f.support_bodies[sector]
        if sector == "up":
            staging = V(0, -q["support_insertion_stage_y_mm"], 0)
        elif sector == "down":
            staging = V(0, q["support_insertion_stage_y_mm"], 0)
        else:
            staging = vector(
                sector,
                -q["support_insertion_inboard_mm"],
                0,
                q["support_insertion_stage_z_mm"] if sector == "right" else 0,
            )
        starts = {
            n: moved(sh, staging + V(q["support_insertion_offset_x_mm"], 0, 0))
            for n, sh in bodies.items()
        }
        rim = f.base.chamber.purchased_interfaces[
            "MaintenanceAccessBlindFlange"
        ].BoundBox.XMax
        outside = (
            min(sh.optimalBoundingBox(False, False).XMin for sh in starts.values())
            > rim + 5
        )
        check(
            f"{sector}_support_starts_outside_chamber",
            outside,
            "The entire support and locating-pin assembly starts outside the closed-flange plane",
        )
        entry = Phase(
            f"{sector}_support_enter_side_window",
            starts,
            dict(fixed),
            delta=V(-q["support_insertion_offset_x_mm"], 0, 0),
        )
        phases = [entry]
        staged = entry.at(1)
        if sector == "right":
            translate = Phase(
                f"{sector}_support_transfer_to_front_wall",
                staged,
                dict(fixed),
                delta=V(0, 0, -q["support_insertion_stage_z_mm"]),
            )
            phases.append(translate)
            staged = translate.at(1)
            staging = V(staging.x, staging.y, 0)
        seat = Phase(
            f"{sector}_support_seat_on_wall_pad",
            staged,
            dict(fixed),
            delta=-staging,
            contacts=frozenset((n, f"FactoryWeldedWallPad_{sector}") for n in bodies),
        )
        phases.append(seat)
        f.support_poses[sector] = {p.name: p.at(1) for p in phases}
        for phase in phases:
            print("CERTIFY", phase.name, flush=True)
            r = certify_phase(phase, s, certified_regions=voids)
            results.append(r)
            check(
                phase.name,
                r["status"] == "pass",
                f"{r['certified_intervals']} continuous installation intervals",
                r["failures"],
            )
            if r["status"] != "pass":
                complete = False
                break
        complete = complete and outside
        fixed.update(bodies)
        fixed.update(f.mount_bolts[sector])
        if not complete:
            break
    bad = collisions(flatten(f.mount_drivers), fixed, s.collision_volume_tolerance_mm3)
    check(
        "wall_mount_fastener_driver_engagement_clear",
        not bad,
        "Short driver engagement envelopes are checked with all supports mounted and detectors absent; complete hand/tool insertion remains a qualification item",
        bad,
    )
    return results, complete and not bad
