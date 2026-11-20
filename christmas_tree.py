#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Christmas Tree — a 3D interactive particle Christmas tree.

Python procedurally builds the tree geometry, then writes a single,
dependency-free HTML file (Three.js is inlined) that opens in any modern
browser. Drag to orbit, scroll to zoom, click the scene to make a wish.

Usage:
    python christmas_tree.py
    python christmas_tree.py --particles 18000 --seed 42 --no-open
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
VENDOR = ROOT / "vendor"

# Load order matters for the non-module Three.js example scripts.
VENDOR_FILES = [
    "three.min.js",
    "CopyShader.js",
    "LuminosityHighPassShader.js",
    "EffectComposer.js",
    "RenderPass.js",
    "ShaderPass.js",
    "UnrealBloomPass.js",
    "OrbitControls.js",
]

# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

BASE_Y = 0.32
TREE_H = 9.66
BASE_RADIUS = 4.0
GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def radius_at(u: float) -> float:
    """Tree silhouette radius at normalized height u (0 = base, 1 = tip)."""
    return BASE_RADIUS * (1.0 - u) ** 1.08 + 0.075


def rounded(value: float, digits: int = 3) -> float:
    return round(value + 0.0, digits)


class ParticleBuilder:
    """Collects flat attribute arrays, ready for BufferGeometry."""

    def __init__(self) -> None:
        self.position: list[float] = []
        self.mix: list[float] = []
        self.accent: list[float] = []
        self.spark: list[float] = []
        self.size: list[float] = []
        self.phase: list[float] = []

    def add(
        self,
        x: float,
        y: float,
        z: float,
        mix: float,
        accent: float,
        spark: float,
        size: float,
        phase: float,
    ) -> None:
        self.position.extend((rounded(x), rounded(y), rounded(z)))
        self.mix.append(rounded(clamp(mix), 3))
        self.accent.append(1.0 if accent else 0.0)
        self.spark.append(1.0 if spark else 0.0)
        self.size.append(rounded(size, 3))
        self.phase.append(rounded(phase % 1.0, 4))

    def __len__(self) -> int:
        return len(self.size)

    def as_dict(self) -> dict[str, list[float]]:
        return {
            "position": self.position,
            "mix": self.mix,
            "accent": self.accent,
            "spark": self.spark,
            "size": self.size,
            "phase": self.phase,
        }


def build_foliage(rng: random.Random, target: int) -> ParticleBuilder:
    """Layered drooping branches plus a volumetric needle cloud."""
    tree = ParticleBuilder()
    tiers = 19

    # 1. Branches: each tier is a whorl of slightly drooping boughs.
    for tier in range(tiers):
        u = tier / (tiers - 1)
        y = BASE_Y + u * TREE_H
        tier_radius = radius_at(u)
        branch_count = max(5, round(15 - 7 * u))

        for branch in range(branch_count):
            base_angle = (
                tier * GOLDEN_ANGLE
                + branch * (math.tau / branch_count)
                + rng.uniform(-0.17, 0.17)
            )
            length = tier_radius * rng.uniform(0.68, 1.045) + 0.07
            droop = (0.10 + 0.42 * length / BASE_RADIUS) * rng.uniform(0.82, 1.18)
            branch_points = int(16 + 24 * (1.0 - u))

            for j in range(branch_points):
                s = (j + rng.random()) / branch_points
                radius = 0.10 + s * length
                angle = (
                    base_angle
                    + math.sin(s * 4.2 + branch) * 0.032
                    + rng.gauss(0.0, 0.032)
                )
                x = math.cos(angle) * radius + rng.gauss(0.0, 0.045)
                z = math.sin(angle) * radius + rng.gauss(0.0, 0.045)
                yy = max(
                    0.06,
                    y
                    - droop * (s ** 1.7)
                    + math.sin(s * math.pi) * 0.035
                    + rng.gauss(0.0, 0.045),
                )
                mix = 0.05 + 0.70 * u + 0.30 * s + rng.gauss(0.0, 0.065)
                accent = rng.random() < 0.0055
                spark = (not accent) and rng.random() < 0.016
                size = (
                    rng.uniform(1.05, 2.25)
                    * (1.0 + 0.20 * s)
                    * (1.0 - 0.20 * u)
                )
                tree.add(x, yy, z, mix, accent, spark, size, rng.random())

    # 2. Needle cloud: fills the cone with a bias toward the illuminated shell.
    while len(tree) < target:
        u = rng.random() ** 0.74
        y = BASE_Y + u * TREE_H
        rim = radius_at(u)
        radial = rim * (0.20 + 0.83 * math.sqrt(rng.random()))
        angle = rng.random() * math.tau
        x = math.cos(angle) * radial + rng.gauss(0.0, 0.035)
        z = math.sin(angle) * radial + rng.gauss(0.0, 0.035)
        yy = y + rng.gauss(0.0, 0.075)
        mix = 0.08 + 0.67 * u + 0.27 * rng.random() + rng.gauss(0.0, 0.045)
        accent = rng.random() < 0.0035
        spark = (not accent) and rng.random() < 0.013
        size = rng.uniform(0.95, 2.0) * (1.0 - 0.18 * u)
        tree.add(x, yy, z, mix, accent, spark, size, rng.random())

    # A few bright needles right at the crown.
    for _ in range(70):
        a = rng.random() * math.tau
        r = rng.uniform(0.0, 0.16)
        tree.add(
            math.cos(a) * r,
            BASE_Y + TREE_H + rng.uniform(-0.04, 0.22),
            math.sin(a) * r,
            rng.uniform(0.88, 1.0),
            0,
            1,
            rng.uniform(1.5, 2.8),
            rng.random(),
        )
    return tree


def build_garland(rng: random.Random, count: int = 1550) -> ParticleBuilder:
    """A warm spiral of fairy lights wrapping the tree."""
    garland = ParticleBuilder()
    turns = 6.25
    for i in range(count):
        u = i / (count - 1)
        y = BASE_Y + 0.10 + u * (TREE_H - 0.24)
        angle = u * math.tau * turns + 0.45
        rim = radius_at(u)
        radius = rim * 1.012 + 0.055 + math.sin(u * math.pi * 7.0) * 0.018
        x = math.cos(angle) * radius + rng.gauss(0.0, 0.022)
        z = math.sin(angle) * radius + rng.gauss(0.0, 0.022)
        yy = y + rng.gauss(0.0, 0.022)
        spark = rng.random() < 0.24
        size = rng.uniform(1.6, 3.3) if not spark else rng.uniform(2.2, 4.2)
        garland.add(x, yy, z, 0.82, 1, spark, size, rng.random())
    return garland


def build_ornaments(rng: random.Random, count: int = 148) -> dict[str, list[float]]:
    """Glowing baubles: cranberry, amber, ivory and a touch of rose."""
    palette = [
        (1.00, 0.10, 0.08),
        (1.00, 0.54, 0.10),
        (1.00, 0.90, 0.68),
        (1.00, 0.18, 0.42),
    ]
    position: list[float] = []
    color: list[float] = []
    size: list[float] = []
    phase: list[float] = []
    for _ in range(count):
        u = rng.random() ** 0.82 * 0.94 + 0.018
        y = BASE_Y + u * TREE_H + rng.gauss(0.0, 0.05)
        rim = radius_at(u) * rng.uniform(0.95, 1.03)
        angle = rng.random() * math.tau
        x = math.cos(angle) * rim
        z = math.sin(angle) * rim
        r, g, b = palette[rng.choices(range(4), weights=[4, 3, 2, 1])[0]]
        brightness = rng.uniform(0.82, 1.0)
        position.extend((rounded(x), rounded(y), rounded(z)))
        color.extend((round(r * brightness, 3), round(g * brightness, 3), round(b * brightness, 3)))
        size.append(round(rng.uniform(6.0, 11.5), 2))
        phase.append(round(rng.random(), 4))
    return {"position": position, "color": color, "size": size, "phase": phase}


def build_ground(rng: random.Random, count: int = 1250) -> dict[str, list[float]]:
    """A frozen pool of light and snow-dust around the base."""
    position: list[float] = []
    color: list[float] = []
    size: list[float] = []
    phase: list[float] = []
    for i in range(count):
        angle = rng.random() * math.tau
        # Mix an even disc with a sparkling ring near the tree.
        if i % 3 == 0:
            radius = rng.uniform(2.3, 4.7)
        else:
            radius = 2.2 + 5.4 * math.sqrt(rng.random())
        x = math.cos(angle) * radius + rng.gauss(0.0, 0.10)
        z = math.sin(angle) * radius + rng.gauss(0.0, 0.10)
        y = rng.uniform(0.0, 0.10) + rng.gauss(0.0, 0.015)
        warmth = rng.random()
        if warmth < 0.16:
            c = (1.0, 0.70, 0.34)
        elif warmth < 0.55:
            c = (0.58, 0.84, 1.0)
        else:
            c = (0.86, 0.94, 1.0)
        fade = clamp(1.0 - (radius - 2.2) / 6.2) * 0.75 + 0.25
        position.extend((rounded(x), rounded(y), rounded(z)))
        color.extend((round(c[0] * fade, 3), round(c[1] * fade, 3), round(c[2] * fade, 3)))
        size.append(round(rng.uniform(1.1, 3.1), 2))
        phase.append(round(rng.random(), 4))
    return {"position": position, "color": color, "size": size, "phase": phase}


def build_scene(seed: int, target_particles: int) -> tuple[dict, dict[str, int]]:
    rng = random.Random(seed)
    foliage_budget = max(4200, target_particles)
    tree = build_foliage(rng, foliage_budget)
    garland = build_garland(rng)
    ornaments = build_ornaments(rng)
    ground = build_ground(rng)

    data = {
        "tree": tree.as_dict(),
        "garland": garland.as_dict(),
        "ornaments": ornaments,
        "ground": ground,
        "star": [0.0, rounded(BASE_Y + TREE_H + 0.62, 3), 0.0],
        "seed": seed,
    }
    ornament_count = len(ornaments["position"]) // 3
    ground_count = len(ground["position"]) // 3
    stats = {
        "tree": len(tree),
        "garland": len(garland),
        "ornaments": ornament_count,
        "ground": ground_count,
        "total": len(tree) + len(garland) + ornament_count + ground_count,
    }
    return data, stats


# ---------------------------------------------------------------------------
# HTML assembly
# ---------------------------------------------------------------------------


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def vendor_bundle() -> str:
    chunks = ["/* Three.js r128 and official examples — MIT License — https://threejs.org */"]
    for name in VENDOR_FILES:
        path = VENDOR / name
        if not path.exists():
            raise SystemExit(
                f"Missing vendor file: {path}\n"
                "The vendor/ folder must stay next to christmas_tree.py."
            )
        chunks.append(f"\n/* ---- {name} ---- */\n")
        chunks.append(read_text(path))
    bundle = "".join(chunks)
    if "</script" in bundle.lower():
        raise SystemExit("Unexpected </script> inside the vendor bundle.")
    return bundle


def build_html(data: dict, stats: dict[str, int]) -> str:
    template = read_text(WEB / "template.html")
    css = read_text(WEB / "style.css")
    scene_js = read_text(WEB / "scene.js")
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    document = template
    document = document.replace("{{CSS}}", css)
    document = document.replace("{{VENDOR_JS}}", vendor_bundle())
    document = document.replace("{{DATA_JSON}}", data_json)
    document = document.replace("{{SCENE_JS}}", scene_js)
    document = document.replace("{{POINT_COUNT}}", f"{stats['total']:,}")
    document = document.replace("{{TREE_COUNT}}", f"{stats['tree']:,}")
    document = document.replace("{{GARLAND_COUNT}}", f"{stats['garland']:,}")
    document = document.replace("{{ORNAMENT_COUNT}}", f"{stats['ornaments']:,}")
    document = document.replace("{{BUILD_YEAR}}", str(time.localtime().tm_year))
    return document


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a 3D interactive particle Christmas tree."
    )
    parser.add_argument(
        "--particles",
        type=int,
        default=12500,
        help="number of foliage particles (default: 12500)",
    )
    parser.add_argument("--seed", type=int, default=20261224, help="random seed")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "christmas_tree.html",
        help="output HTML path",
    )
    parser.add_argument(
        "--no-open", action="store_true", help="do not open the browser automatically"
    )
    args = parser.parse_args()

    if args.particles < 2000:
        parser.error("--particles must be at least 2000")

    started = time.perf_counter()
    data, stats = build_scene(args.seed, args.particles)
    html = build_html(data, stats)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    elapsed = time.perf_counter() - started

    size_mb = output.stat().st_size / 1024 / 1024
    print("Christmas tree generated")
    print(f"  foliage   : {stats['tree']:,} particles")
    print(f"  garland   : {stats['garland']:,} lights")
    print(f"  ornaments : {stats['ornaments']:,} baubles")
    print(f"  ground    : {stats['ground']:,} snow sparks")
    print(f"  total     : {stats['total']:,} particles")
    print(f"  output    : {output} ({size_mb:.1f} MB, {elapsed:.2f}s)")
    print("  controls  : drag to orbit / scroll to zoom / click to wish")

    if not args.no_open:
        webbrowser.open(output.as_uri())


if __name__ == "__main__":
    main()
