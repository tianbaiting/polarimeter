from dataclasses import replace
from pathlib import Path
import sys

import Part
import FreeCAD as App

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from civ.boxed.config import load_spec
from civ.boxed.motion import Phase, certify_phase, VoidRegion, verify_void_regions
from civ.boxed.validation import contact_area


def main():
    s = load_spec(ROOT / "studies/boxed_sector/config.yaml")
    V = App.Vector
    a = Part.makeBox(1, 1, 1)
    clear = Phase(
        "clear", {"a": a}, {"b": Part.makeBox(1, 1, 1, V(5, 3, 0))}, delta=V(10, 0, 0)
    )
    assert certify_phase(clear, s)["status"] == "pass"
    thin = Phase(
        "thin blocker",
        {"a": a},
        {"b": Part.makeBox(0.001, 1, 1, V(3.37, 0, 0))},
        delta=V(10, 0, 0),
    )
    assert certify_phase(thin, s)["status"] == "fail"
    rotor = Phase(
        "rotational blocker",
        {"a": Part.makeSphere(0.2, V(5, 0, 0))},
        {"b": Part.makeSphere(0.1, V(3.5355339, 3.5355339, 0))},
        pivot=V(),
        angle=90,
    )
    assert certify_phase(rotor, s)["status"] == "fail"
    enclosed = Phase(
        "contained obstacle",
        {"a": a},
        {"b": Part.makeBox(10, 10, 10, V(-4, -4, -4))},
        delta=V(1, 0, 0),
    )
    assert certify_phase(enclosed, s)["status"] == "fail"
    unresolved = certify_phase(clear, replace(s, interval_min_fraction=1.0))
    assert unresolved["status"] == "fail"
    assert unresolved["failures"][0]["kind"] == "uncertified_interval"
    contact = Phase(
        "declared separation",
        {"a": a},
        {"b": Part.makeBox(1, 1, 1, V(1, 0, 0))},
        delta=V(-1, 0, 0),
        contacts=frozenset({("a", "b")}),
    )
    assert certify_phase(contact, s)["status"] == "pass"
    assert abs(contact_area(a, contact.obstacles["b"]) - 1) < 1e-8
    wrong = replace(contact, delta=V(1, 0, 0))
    assert certify_phase(wrong, s)["status"] == "fail"
    unauthorized = replace(thin, excluded_pairs=frozenset({("a", "b")}))
    result = certify_phase(unauthorized, s)
    assert (
        result["status"] == "fail"
        and result["failures"][0]["kind"] == "missing_mating_certificate"
    )
    fake = {"b": [VoidRegion("box", (-1, 12, -1, 5, -1, 2))]}
    certified, records = verify_void_regions(fake, clear.obstacles, 1e-6)
    assert not certified and records[0]["status"] == "fail"
    valid = {"b": [VoidRegion("box", (-1, 12, -1, 2, -1, 2))]}
    certified, records = verify_void_regions(valid, clear.obstacles, 1e-6)
    assert records[0]["status"] == "pass"
    assert certify_phase(clear, s, certified_regions=certified)["status"] == "pass"
    print(
        "PASS: clear motion, thin blocker, rotation blocker, unresolved intervals, mating contacts, finite-area contact and exclusion guard",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
