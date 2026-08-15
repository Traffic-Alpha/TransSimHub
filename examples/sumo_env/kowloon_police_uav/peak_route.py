"""
Generate kowloon background traffic with a **morning-peak** demand profile.

Why this exists next to random_route.py: that script emits a *flat* insertion rate,
which produces no peak shape at all -- traffic simply accumulates until the demand
block ends, then drains. To actually watch congestion build up, saturate and then
dissipate (which is the whole point of the replay dashboard), the insertion rate has
to vary over time.

The profile is a trapezoid:

    rate
     ^
     |            ______________________            <- peak plateau
     |           /                      \\
     |          /                        \\
     |  _______/                          \\_______  <- off-peak base
     +--------------------------------------------> time
        warm-up   ramp      peak      ramp   off-peak

randomTrips.py accepts a *list* for --insertion-rate and splits [begin, end) into
that many equal slices, so the whole profile is expressed as one list of rates.

Usage:
    conda run -n tshub python peak_route.py [--duration SEC] [--base-rate VEH_PER_H]
        [--peak-rate VEH_PER_H] [--peak-start SEC] [--peak-end SEC] [--ramp SEC]
        [--slice SEC] [--seed N] [--output FILE] [--keep-tmp]
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
TMP_DIR = SCRIPT_DIR / ".peak_route_tmp"


@dataclass
class VehicleClass:
    name: str
    vClass: str
    ratio: float
    color: str
    length: float


def get_vehicle_classes(car_r, bus_r, truck_r, moto_r):
    return [
        VehicleClass("background_car", "passenger", car_r, "220,220,220", 5.0),
        VehicleClass("background_bus", "bus", bus_r, "255,200,0", 12.0),
        VehicleClass("background_truck", "truck", truck_r, "100,100,200", 8.0),
        VehicleClass("background_moto", "motorcycle", moto_r, "200,50,50", 2.2),
    ]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate morning-peak background traffic for kowloon.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--duration", type=int, default=7200,
                        help="total simulated seconds")
    parser.add_argument("--slice", type=int, default=300, dest="slice_seconds",
                        help="length of one rate slice; the profile is sampled at slice midpoints")
    parser.add_argument("--base-rate", type=float, default=3600.0,
                        help="off-peak insertion rate, vehicles per hour (all classes combined)")
    parser.add_argument("--peak-rate", type=float, default=14000.0,
                        help="peak insertion rate, vehicles per hour (all classes combined)")
    parser.add_argument("--peak-start", type=int, default=2400,
                        help="second at which the peak plateau begins")
    parser.add_argument("--peak-end", type=int, default=4200,
                        help="second at which the peak plateau ends")
    parser.add_argument("--ramp", type=int, default=1200,
                        help="ramp duration on each side of the plateau, seconds")
    parser.add_argument("--fringe-factor", default="10.0",
                        help="bias trips to start/end on fringe edges")
    parser.add_argument("--car-ratio", type=float, default=0.70)
    parser.add_argument("--bus-ratio", type=float, default=0.10)
    parser.add_argument("--truck-ratio", type=float, default=0.15)
    parser.add_argument("--moto-ratio", type=float, default=0.05)
    parser.add_argument("--output", default="peak.rou.xml",
                        help="output route file (relative to the scenario folder)")
    parser.add_argument("--keep-tmp", action="store_true")
    args = parser.parse_args()

    total = args.car_ratio + args.bus_ratio + args.truck_ratio + args.moto_ratio
    if abs(total - 1.0) > 0.001:
        parser.error(f"ratios must sum to 1.0 (got {total:.4f})")
    if not (0 < args.peak_start < args.peak_end <= args.duration):
        parser.error("need 0 < --peak-start < --peak-end <= --duration")
    if args.peak_start - args.ramp < 0:
        parser.error("--ramp reaches before time 0; lower --ramp or raise --peak-start")
    return args


def build_rate_profile(args):
    """Sample the trapezoid at each slice midpoint -> one rate per slice."""
    n_slices = max(1, args.duration // args.slice_seconds)
    rates = []
    for index in range(n_slices):
        midpoint = (index + 0.5) * args.slice_seconds
        if midpoint < args.peak_start - args.ramp:
            rate = args.base_rate
        elif midpoint < args.peak_start:
            # linear ramp up into the plateau
            progress = (midpoint - (args.peak_start - args.ramp)) / args.ramp
            rate = args.base_rate + (args.peak_rate - args.base_rate) * progress
        elif midpoint <= args.peak_end:
            rate = args.peak_rate
        elif midpoint <= args.peak_end + args.ramp:
            progress = (midpoint - args.peak_end) / args.ramp
            rate = args.peak_rate - (args.peak_rate - args.base_rate) * progress
        else:
            rate = args.base_rate
        rates.append(rate)
    return rates


def describe_profile(rates, args):
    print(f"  demand profile: {len(rates)} slices x {args.slice_seconds}s "
          f"= {len(rates) * args.slice_seconds}s")
    width = 44
    peak = max(rates)
    for index, rate in enumerate(rates):
        bar = "#" * max(1, int(round(rate / peak * width)))
        print(f"    {index * args.slice_seconds:5d}s {rate:8.0f} veh/h |{bar}")
    total = sum(rate * args.slice_seconds / 3600.0 for rate in rates)
    print(f"  expected total: ~{total:.0f} vehicles")


def find_random_trips():
    sumo_home = os.environ.get("SUMO_HOME")
    if not sumo_home:
        sys.exit("error: SUMO_HOME environment variable is not set")
    script = Path(sumo_home) / "tools" / "randomTrips.py"
    if not script.exists():
        sys.exit(f"error: randomTrips.py not found at {script}")
    return script


def run_random_trips(script, cls, args, rates):
    if cls.ratio <= 0:
        return

    # each class gets its share of the combined rate, slice by slice
    class_rates = [f"{rate * cls.ratio:.4f}" for rate in rates]
    out_file = TMP_DIR / f"{cls.name}.rou.xml"
    trip_file = TMP_DIR / f"{cls.name}.trips.xml"
    cmd = [
        sys.executable, str(script),
        "--net-file", str(NET_FILE),
        "--output-trip-file", str(trip_file),
        "--route-file", str(out_file),
        "--vehicle-class", cls.vClass,
        # a list of rates: randomTrips splits [begin, end) into len(rates) equal slices
        "--insertion-rate", *class_rates,
        "--seed", str(args.seed),
        "--begin", "0",
        "--end", str(args.duration),
        "--fringe-factor", str(args.fringe_factor),
        "--validate",
        "--prefix", f"{cls.name}_",
    ]

    print(f"  [{cls.name}] vClass={cls.vClass} "
          f"rate {min(float(r) for r in class_rates):.0f}~{max(float(r) for r in class_rates):.0f} veh/h")
    result = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        sys.exit(f"error: randomTrips.py failed for {cls.name} (exit {result.returncode})")


def merge_routes(classes, output_path):
    output = ET.Element("routes")
    for cls in classes:
        if cls.ratio <= 0:
            continue
        ET.SubElement(output, "vType", id=cls.name, vClass=cls.vClass,
                      color=cls.color, length=f"{cls.length}")

    all_vehicles = []
    counts = {}
    for cls in classes:
        if cls.ratio <= 0:
            continue
        root = ET.parse(TMP_DIR / f"{cls.name}.rou.xml").getroot()
        vehicles = root.findall("vehicle")
        for vehicle in vehicles:
            vehicle.set("type", cls.name)
            vehicle.attrib.pop("vClass", None)
        counts[cls.name] = len(vehicles)
        all_vehicles.extend(vehicles)

    all_vehicles.sort(key=lambda vehicle: float(vehicle.get("depart", "0")))
    for vehicle in all_vehicles:
        output.append(vehicle)

    tree = ET.ElementTree(output)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return counts, all_vehicles


def report_departures(vehicles, slice_seconds):
    """Print the realised departure histogram so the profile can be sanity-checked."""
    if not vehicles:
        return
    buckets = {}
    for vehicle in vehicles:
        bucket = int(float(vehicle.get("depart", "0")) // slice_seconds)
        buckets[bucket] = buckets.get(bucket, 0) + 1
    peak = max(buckets.values())
    width = 44
    print("  realised departures:")
    for bucket in sorted(buckets):
        count = buckets[bucket]
        bar = "#" * max(1, int(round(count / peak * width)))
        print(f"    {bucket * slice_seconds:5d}s {count:6d} |{bar}")


def main():
    args = parse_args()
    if not NET_FILE.exists():
        sys.exit(f"error: {NET_FILE} not found")

    classes = get_vehicle_classes(args.car_ratio, args.bus_ratio,
                                  args.truck_ratio, args.moto_ratio)
    script = find_random_trips()
    rates = build_rate_profile(args)
    describe_profile(rates, args)

    TMP_DIR.mkdir(exist_ok=True)
    try:
        for cls in classes:
            run_random_trips(script, cls, args, rates)
        output_path = SCRIPT_DIR / args.output
        counts, vehicles = merge_routes(classes, output_path)
        print(f"  merged {sum(counts.values())} vehicles -> {output_path}")
        print(f"  per class: {counts}")
        report_departures(vehicles, args.slice_seconds)
    finally:
        if not args.keep_tmp and TMP_DIR.exists():
            shutil.rmtree(TMP_DIR)


if __name__ == "__main__":
    main()
