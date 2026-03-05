# FreeCAD Macro: JINR-style dp polarimeter chamber (box) + JIS beam ports + 4-side windows + target support
# Also places 12 detector "outer shells" (phi50) as reference solids at the positions you specified.
#  freecadcmd -c "import runpy; runpy.run_path('infrontofSamuraiMag/build_polarimeter.py', run_name='__main__')"
# How to use:
# 1) FreeCAD → Macro → Macros... → Create → paste this → Save
# 2) Run. It will create a new document and build the model.
#
# Notes:
# - Units: mm
# - Coordinate convention: target at origin (0,0,0), beam along +Z
# - Chamber is centered at origin.

import FreeCAD as App
import Part
import math
import os
from pathlib import Path

DOC_NAME = "dp_polarimeter_chamber"
App.newDocument(DOC_NAME)
doc = App.ActiveDocument

# -------------------------
# Parameters (edit these)
# -------------------------

# Chamber outer size (box) and wall thickness
CH_OUT_X = 1200.0  # outer width in X
CH_OUT_Y = 1200.0  # outer width in Y
CH_OUT_Z = 1200.0  # outer length in Z
WALL     = 50.0    # wall thickness

# Beam pipe holes and short "nozzles" (generic; you will adapt to your exact JIS flange/pipe ID/OD)
BEAM_HOLE_D = 150.0  # through-hole diameter
NOZZLE_OD   = 200.0  # nozzle outer diameter
NOZZLE_LEN  = 120.0  # nozzle length (each end)
NOZZLE_WALL = 10.0   # nozzle wall thickness (for reference)

# Side windows / detector-exit windows (auto-placed by trajectory-box intersection)
WIN_HIGH_D = 80.0      # window diameter for small-theta channel(s)
WIN_LOW_D  = 120.0     # window diameter for larger-theta channel(s)
# Optional short tubes outside each window (for detector mounting)
WIN_TUBE_LEN = 80.0
WIN_TUBE_OD  = 170.0   # outer diameter of window tube (mount stub)
WIN_TUBE_WALL = 8.0

# Target support (inside)
ROD_D   = 10.0
ROD_LEN = 500.0
FRAME_OUT = 40.0
FRAME_THK = 2.0
FRAME_BAR = 4.0  # frame border width

# Detector outer shells for reference (phi50)
DET_OD = 50.0
DET_LEN = 80.0  # arbitrary "housing length" for visualization

# Your channels: (particle, theta_deg, r_m)
CHANNELS = [
    ("deuteron", 20.9, 0.40),
    ("proton",   11.2, 0.62),
    ("proton",   53.4, 0.62),
]
# Place 4 azimuths: +x, -x, +y, -y (phi = 0, 180, 90, 270)
AZIMUTHS_DEG = [0.0, 180.0, 90.0, 270.0]


# -------------------------
# Helpers
# -------------------------

def deg2rad(d): return d * math.pi / 180.0

def vec(x,y,z): return App.Vector(x,y,z)

def make_cyl(d, h, base_center, axis_vec):
    """
    Create a cylinder of diameter d and height h, with its base center at base_center,
    oriented along axis_vec (must be non-zero).
    """
    axis = axis_vec
    if axis.Length == 0:
        axis = App.Vector(0,0,1)
    axis = axis.normalize()

    # Part.makeCylinder(radius, height, pnt, dir)
    return Part.makeCylinder(d/2.0, h, base_center, axis)

def add_shape_obj(name, shape):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


def resolve_output_dir():
    """
    Output directory priority:
    1) POLARIMETER_OUT_DIR env var
    2) script directory (when __file__ is available)
    3) current working directory
    """
    env_out = os.environ.get("POLARIMETER_OUT_DIR")
    if env_out:
        out_dir = Path(env_out).expanduser().resolve()
    elif "__file__" in globals():
        out_dir = Path(__file__).resolve().parent
    else:
        out_dir = Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def save_outputs(document, base_name):
    out_dir = resolve_output_dir()
    fcstd_path = out_dir / f"{base_name}.FCStd"
    step_path = out_dir / f"{base_name}.step"
    document.saveAs(str(fcstd_path))
    export_objs = [obj for obj in document.Objects if hasattr(obj, "Shape")]
    Part.export(export_objs, str(step_path))
    return fcstd_path, step_path


def validate_parameters():
    positive_params = {
        "CH_OUT_X": CH_OUT_X,
        "CH_OUT_Y": CH_OUT_Y,
        "CH_OUT_Z": CH_OUT_Z,
        "WALL": WALL,
        "BEAM_HOLE_D": BEAM_HOLE_D,
        "NOZZLE_OD": NOZZLE_OD,
        "NOZZLE_LEN": NOZZLE_LEN,
        "NOZZLE_WALL": NOZZLE_WALL,
        "WIN_HIGH_D": WIN_HIGH_D,
        "WIN_LOW_D": WIN_LOW_D,
        "WIN_TUBE_LEN": WIN_TUBE_LEN,
        "WIN_TUBE_OD": WIN_TUBE_OD,
        "WIN_TUBE_WALL": WIN_TUBE_WALL,
        "ROD_D": ROD_D,
        "ROD_LEN": ROD_LEN,
        "FRAME_OUT": FRAME_OUT,
        "FRAME_THK": FRAME_THK,
        "FRAME_BAR": FRAME_BAR,
        "DET_OD": DET_OD,
        "DET_LEN": DET_LEN,
    }
    for name, value in positive_params.items():
        if value <= 0.0:
            raise ValueError(f"{name} must be > 0, got {value}")

    if (2.0 * WALL) >= min(CH_OUT_X, CH_OUT_Y, CH_OUT_Z):
        raise ValueError("WALL is too large for chamber dimensions")
    if NOZZLE_OD <= (2.0 * NOZZLE_WALL):
        raise ValueError("NOZZLE_OD must be greater than 2*NOZZLE_WALL")
    if WIN_TUBE_OD <= (2.0 * WIN_TUBE_WALL):
        raise ValueError("WIN_TUBE_OD must be greater than 2*WIN_TUBE_WALL")
    if WIN_TUBE_OD <= max(WIN_HIGH_D, WIN_LOW_D):
        raise ValueError("WIN_TUBE_OD must be greater than both window diameters")
    if FRAME_OUT <= (2.0 * FRAME_BAR):
        raise ValueError("FRAME_OUT must be greater than 2*FRAME_BAR")

def hollow_box(outer_x, outer_y, outer_z, wall):
    """
    Returns a hollow box centered at origin, with uniform wall thickness.
    """
    outer = Part.makeBox(outer_x, outer_y, outer_z,
                         vec(-outer_x/2, -outer_y/2, -outer_z/2))
    inner_x = outer_x - 2*wall
    inner_y = outer_y - 2*wall
    inner_z = outer_z - 2*wall
    inner = Part.makeBox(inner_x, inner_y, inner_z,
                         vec(-inner_x/2, -inner_y/2, -inner_z/2))
    return outer.cut(inner)

def window_diameter_mm(theta_deg):
    return WIN_HIGH_D if theta_deg <= 15.0 else WIN_LOW_D


def detector_direction(theta_deg, phi_deg):
    theta = deg2rad(theta_deg)
    phi = deg2rad(phi_deg)
    direction = vec(
        math.sin(theta) * math.cos(phi),
        math.sin(theta) * math.sin(phi),
        math.cos(theta),
    )
    return direction.normalize()


def ray_box_intersection(direction):
    """
    Intersect ray r(t)=t*direction (t>0) from origin with chamber outer box.
    Returns (hit_point, outward_normal, t).
    """
    hx = CH_OUT_X / 2.0
    hy = CH_OUT_Y / 2.0
    hz = CH_OUT_Z / 2.0
    d = direction.normalize()
    eps = 1e-9

    candidates = []
    if abs(d.x) > eps:
        t = hx / abs(d.x)
        y = t * d.y
        z = t * d.z
        if abs(y) <= (hy + 1e-6) and abs(z) <= (hz + 1e-6):
            candidates.append((t, vec(math.copysign(1.0, d.x), 0.0, 0.0), vec(math.copysign(hx, d.x), y, z)))
    if abs(d.y) > eps:
        t = hy / abs(d.y)
        x = t * d.x
        z = t * d.z
        if abs(x) <= (hx + 1e-6) and abs(z) <= (hz + 1e-6):
            candidates.append((t, vec(0.0, math.copysign(1.0, d.y), 0.0), vec(x, math.copysign(hy, d.y), z)))
    if abs(d.z) > eps:
        t = hz / abs(d.z)
        x = t * d.x
        y = t * d.y
        if abs(x) <= (hx + 1e-6) and abs(y) <= (hy + 1e-6):
            candidates.append((t, vec(0.0, 0.0, math.copysign(1.0, d.z)), vec(x, y, math.copysign(hz, d.z))))

    if not candidates:
        raise ValueError("ray does not intersect chamber box")
    t_hit, normal, hit = min(candidates, key=lambda item: item[0])
    return hit, normal, t_hit


def max_window_diameter_at_hit(hit_point, outward_normal):
    hx = CH_OUT_X / 2.0
    hy = CH_OUT_Y / 2.0
    hz = CH_OUT_Z / 2.0
    eps = 1e-9

    if abs(outward_normal.x) > (1.0 - eps):
        clearance = min(hy - abs(hit_point.y), hz - abs(hit_point.z))
    elif abs(outward_normal.y) > (1.0 - eps):
        clearance = min(hx - abs(hit_point.x), hz - abs(hit_point.z))
    elif abs(outward_normal.z) > (1.0 - eps):
        clearance = min(hx - abs(hit_point.x), hy - abs(hit_point.y))
    else:
        raise ValueError("outward_normal must be axis-aligned")

    return max(0.0, 2.0 * clearance)

def compute_detector_layout():
    """
    Return list of detector dicts for 12 detectors,
    where axis points from detector toward target (i.e., face normal aims at origin).
    """
    dets = []
    for particle, theta_deg, r_m in CHANNELS:
        r = r_m * 1000.0
        for phi_deg in AZIMUTHS_DEG:
            direction_out = detector_direction(theta_deg, phi_deg)
            center = direction_out * r
            # aim detector axis toward target:
            axis = (vec(0,0,0) - center)
            if axis.Length == 0:
                axis = vec(0,0,1)
            det_name = f"DET_{particle}_th{theta_deg:.1f}_phi{phi_deg:.0f}"
            dets.append(
                {
                    "name": det_name,
                    "particle": particle,
                    "theta_deg": theta_deg,
                    "phi_deg": phi_deg,
                    "radius_mm": r,
                    "center": center,
                    "axis_to_target": axis,
                    "direction_out": direction_out,
                    "window_d_mm": window_diameter_mm(theta_deg),
                }
            )
    return dets

# -------------------------
# Build chamber body
# -------------------------

validate_parameters()

chamber = hollow_box(CH_OUT_X, CH_OUT_Y, CH_OUT_Z, WALL)

# Beam pipe holes (through) along Z axis
beam_hole = make_cyl(BEAM_HOLE_D, CH_OUT_Z + 2.0, vec(0,0,-(CH_OUT_Z/2 + 1.0)), vec(0,0,1))
chamber = chamber.cut(beam_hole)

# Add short nozzles on both ends (simple tube geometry fused)
def make_nozzle(z_sign):
    # z_sign = +1 for +Z end, -1 for -Z end
    z_face = z_sign * (CH_OUT_Z/2)
    # nozzle as tube: outer cyl minus inner cyl
    outer = make_cyl(NOZZLE_OD, NOZZLE_LEN, vec(0,0,z_face), vec(0,0,z_sign))
    inner = make_cyl(NOZZLE_OD - 2*NOZZLE_WALL, NOZZLE_LEN+0.5, vec(0,0,z_face), vec(0,0,z_sign))
    tube = outer.cut(inner)
    # also ensure beam hole continues
    tube = tube.cut(make_cyl(BEAM_HOLE_D, NOZZLE_LEN+1.0, vec(0,0,z_face), vec(0,0,z_sign)))
    return tube

chamber = chamber.fuse(make_nozzle(+1))
chamber = chamber.fuse(make_nozzle(-1))

# -------------------------
# Detector-exit windows:
# one window per detector by intersecting detector direction with chamber outer wall.
# -------------------------

def make_window_stub(d_hole, hit_point, outward_normal):
    outer = make_cyl(WIN_TUBE_OD, WIN_TUBE_LEN, hit_point, outward_normal)
    inner = make_cyl(WIN_TUBE_OD - 2*WIN_TUBE_WALL, WIN_TUBE_LEN + 0.5, hit_point, outward_normal)
    tube = outer.cut(inner)
    tube = tube.cut(make_cyl(d_hole, WIN_TUBE_LEN + 1.0, hit_point, outward_normal))
    return tube


detectors = compute_detector_layout()
window_holes = []
window_stubs = []
for det in detectors:
    hit_point, outward_normal, _ = ray_box_intersection(det["direction_out"])
    max_d = max_window_diameter_at_hit(hit_point, outward_normal)
    if det["window_d_mm"] > (max_d + 1e-6):
        raise ValueError(
            f"Window diameter too large for {det['name']}: "
            f"requested={det['window_d_mm']:.2f} mm, max={max_d:.2f} mm at hit={hit_point}"
        )
    # Cut only through wall thickness from outside toward inside.
    hole = make_cyl(
        det["window_d_mm"],
        WALL + 2.0,
        hit_point + outward_normal * 1.0,
        outward_normal * -1.0,
    )
    window_holes.append(hole)
    window_stubs.append(make_window_stub(det["window_d_mm"], hit_point, outward_normal))

chamber = chamber.cut(Part.Compound(window_holes))
chamber = chamber.fuse(Part.Compound(window_stubs))

# Add chamber to document
ch_obj = add_shape_obj("Chamber", chamber)

# -------------------------
# Target support (rod + frame)
# -------------------------

# Rod enters from -Z side toward origin; place it along +Z, starting near -Z inner region
# Put rod base at z = -CH_OUT_Z/2 + WALL + 20
rod_base_z = -CH_OUT_Z/2 + WALL + 20.0
rod = make_cyl(ROD_D, ROD_LEN, vec(0,0,rod_base_z), vec(0,0,1))

# Frame at rod end, centered on beam axis, lying in XY plane
frame_center_z = rod_base_z + ROD_LEN
# Make a simple rectangular ring
outer = Part.makeBox(FRAME_OUT, FRAME_OUT, FRAME_THK,
                     vec(-FRAME_OUT/2, -FRAME_OUT/2, frame_center_z))
inner = Part.makeBox(FRAME_OUT-2*FRAME_BAR, FRAME_OUT-2*FRAME_BAR, FRAME_THK+0.5,
                     vec(-(FRAME_OUT-2*FRAME_BAR)/2, -(FRAME_OUT-2*FRAME_BAR)/2, frame_center_z-0.25))
frame = outer.cut(inner)

target_support = rod.fuse(frame)
ts_obj = add_shape_obj("TargetSupport", target_support)

# -------------------------
# Place 12 detector outer shells (phi50) as reference solids
# Each detector is a cylinder centered at your computed (x,y,z) and oriented to point to origin.
# We create the cylinder with its base center at (center - axis_unit*(DET_LEN/2)), so the cylinder is centered.
# -------------------------

det_compounds = []
for det in detectors:
    axis_u = det["axis_to_target"].normalize()
    center = det["center"]
    base = center - axis_u * (DET_LEN/2.0)
    cyl = make_cyl(DET_OD, DET_LEN, base, axis_u)
    det_compounds.append(cyl)

det_all = Part.Compound(det_compounds)
det_obj = add_shape_obj("Detectors_phi50", det_all)

# -------------------------
# Make it pretty-ish
# -------------------------
try:
    ch_obj.ViewObject.Transparency = 80
    ts_obj.ViewObject.ShapeColor = (1.0, 0.8, 0.2)
    det_obj.ViewObject.ShapeColor = (0.2, 0.6, 1.0)
except Exception:
    pass

doc.recompute()

fcstd_file, step_file = save_outputs(doc, DOC_NAME)
print("Done: Chamber + ports + windows + target support + 12 detector shells created.")
print("Saved:", fcstd_file)
print("Saved:", step_file)
