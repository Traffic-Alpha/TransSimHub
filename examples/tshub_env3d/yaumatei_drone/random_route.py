"""
Generate random mixed-vehicle background traffic for yaumatei_drone via SUMO's
randomTrips.py. Outputs env.rou.xml and enables it in env.sumocfg.

Usage:
    python random_route.py [--seed N] [--duration SEC] [--total-flow F]
                           [--car-ratio R] [--bus-ratio R]
                           [--truck-ratio R] [--moto-ratio R]
                           [--fringe-factor F] [--keep-tmp]
"""
import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

SCRIPT_DIR = Path(__file__).resolve().parent
NET_FILE = SCRIPT_DIR / "map.net.xml"
ROU_FILE = SCRIPT_DIR / "env.rou.xml"
SUMOCFG = SCRIPT_DIR / "env.sumocfg"
TMP_DIR = SCRIPT_DIR / ".random_route_tmp"


@dataclass
class VehicleClass:
    name: str
    vClass: str
    ratio: float
    color: str       # "R,G,B"
    length: float    # meters


def get_vehicle_classes(car_r, bus_r, truck_r, moto_r):
    return [
        VehicleClass("background_car",   "passenger",  car_r,   "220,220,220", 5.0),
        VehicleClass("background_bus",   "bus",        bus_r,   "255,200,0",   12.0),
        VehicleClass("background_truck", "truck",      truck_r, "100,100,200", 8.0),
        VehicleClass("background_moto",  "motorcycle", moto_r,  "200,50,50",   2.2),
    ]


def parse_args():
    p = argparse.ArgumentParser(
        description="Generate random background traffic for yaumatei_drone."
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--duration", type=int, default=600,
                   help="simulation seconds (default: 600 = 10 min)")
    p.add_argument("--total-flow", type=float, default=1.0,
                   help="total veh/sec across all classes (default: 1.0)")
    p.add_argument("--fringe-factor", type=float, default=10.0,
                   help="bias trips to start/end on fringe edges (default: 10)")
    p.add_argument("--car-ratio",   type=float, default=0.70)
    p.add_argument("--bus-ratio",   type=float, default=0.10)
    p.add_argument("--truck-ratio", type=float, default=0.15)
    p.add_argument("--moto-ratio",  type=float, default=0.05)
    p.add_argument("--keep-tmp", action="store_true",
                   help="keep .random_route_tmp/ for debugging")
    args = p.parse_args()

    total = args.car_ratio + args.bus_ratio + args.truck_ratio + args.moto_ratio
    if abs(total - 1.0) > 0.001:
        p.error(
            f"ratios must sum to 1.0 (got {total:.4f}): "
            f"car={args.car_ratio} bus={args.bus_ratio} "
            f"truck={args.truck_ratio} moto={args.moto_ratio}"
        )
    return args


def find_random_trips():
    sumo_home = os.environ.get("SUMO_HOME")
    if not sumo_home:
        sys.exit("error: SUMO_HOME environment variable is not set")
    script = Path(sumo_home) / "tools" / "randomTrips.py"
    if not script.exists():
        sys.exit(f"error: randomTrips.py not found at {script}")
    return script


def run_random_trips(script, cls, args, seed):
    if cls.ratio <= 0:
        return
    period = 1.0 / (cls.ratio * args.total_flow)
    out_file = TMP_DIR / f"{cls.name}.rou.xml"
    cmd = [
        sys.executable, str(script),
        "--net-file",       str(NET_FILE),
        "--route-file",     str(out_file),
        "--vehicle-class",  cls.vClass,
        "--period",         f"{period:.6f}",
        "--seed",           str(seed),
        "--begin",          "0",
        "--end",            str(args.duration),
        "--fringe-factor",  str(args.fringe_factor),
        "--validate",
        "--prefix",         f"{cls.name}_",
    ]
    print(f"  [{cls.name}] vClass={cls.vClass} period={period:.2f}s seed={seed}")
    result = subprocess.run(cmd, cwd=SCRIPT_DIR,
                            capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        sys.exit(f"error: randomTrips.py failed for {cls.name} "
                 f"(exit {result.returncode})")


def merge_routes(classes):
    """Combine per-class rou.xml into env.rou.xml with vType defs at top.

    Returns dict {class_name: vehicle_count}.
    """
    output = ET.Element("routes")

    for cls in classes:
        if cls.ratio <= 0:
            continue
        ET.SubElement(output, "vType",
                      id=cls.name,
                      vClass=cls.vClass,
                      color=cls.color,
                      length=f"{cls.length}")

    all_vehicles = []
    counts = {}
    for cls in classes:
        if cls.ratio <= 0:
            continue
        path = TMP_DIR / f"{cls.name}.rou.xml"
        root = ET.parse(path).getroot()
        vehicles = root.findall("vehicle")
        for v in vehicles:
            v.set("type", cls.name)
            if "vClass" in v.attrib:
                del v.attrib["vClass"]
        counts[cls.name] = len(vehicles)
        all_vehicles.extend(vehicles)

    all_vehicles.sort(key=lambda v: float(v.get("depart", "0")))
    for v in all_vehicles:
        output.append(v)

    tree = ET.ElementTree(output)
    ET.indent(tree, space="  ")
    tree.write(ROU_FILE, encoding="utf-8", xml_declaration=True)
    return counts


def update_sumocfg():
    """Enable <route-files value="./env.rou.xml"/> in env.sumocfg. Idempotent."""
    text = SUMOCFG.read_text(encoding="utf-8")
    active = '<route-files value="./env.rou.xml"/>'
    commented = '<!-- <route-files value="./env.rou.xml"/> -->'

    if commented in text:
        new_text = text.replace(commented, active)
    elif active in text:
        return
    else:
        if "</input>" not in text:
            sys.exit("error: env.sumocfg has no <input> block; refusing to modify")
        new_text = text.replace(
            "</input>",
            f"        {active}\n    </input>"
        )

    tmp = SUMOCFG.with_suffix(SUMOCFG.suffix + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    tmp.replace(SUMOCFG)


def main():
    args = parse_args()
    classes = get_vehicle_classes(
        args.car_ratio, args.bus_ratio, args.truck_ratio, args.moto_ratio
    )
    script = find_random_trips()

    if not NET_FILE.exists():
        sys.exit(f"error: {NET_FILE} not found")

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir()

    try:
        print(f"Generating random trips: duration={args.duration}s, "
              f"total_flow={args.total_flow} veh/s, seed={args.seed}, "
              f"fringe_factor={args.fringe_factor}")
        for i, cls in enumerate(classes):
            run_random_trips(script, cls, args, args.seed + i)

        print(f"\nMerging routes -> {ROU_FILE.name}")
        counts = merge_routes(classes)
        total = sum(counts.values())
        for name, n in counts.items():
            pct = 100.0 * n / total if total else 0
            print(f"  {name}: {n} ({pct:.1f}%)")
        print(f"  total: {total} vehicles")

        print(f"\nEnabling route file in {SUMOCFG.name}")
        update_sumocfg()

        print("\nDone. Run with:")
        print(f"  sumo-gui -c {SUMOCFG.relative_to(SCRIPT_DIR.parent.parent)}")
    finally:
        if not args.keep_tmp and TMP_DIR.exists():
            shutil.rmtree(TMP_DIR)


if __name__ == "__main__":
    main()
