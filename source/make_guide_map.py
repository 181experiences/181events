#!/usr/bin/env python3
"""Draws the Black Book's two street maps, once, into guide_map.json.

The streets come from OpenStreetMap (c) OpenStreetMap contributors, ODbL,
fetched one time through Overpass into three raw files; this script turns
them into plain line drawings the admin inlines. Nothing in the admin ever
calls a map service: the drawing is ours, static, and two-toned.

  python make_guide_map.py <folder holding osm_near.json, osm_city.json, osm_home.json>

Two maps, both north up:
  near  every street and alley about 1.3 miles each way from the tower
  city  the main streets and shoreline of all San Francisco
Each carries its projection, so the admin can place any latitude and
longitude on it: x = (lon - west) * kx, y = (north - lat) * ky.
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOME_WAY = 445566153          # the 181 Fremont Tower footprint in OpenStreetMap

NEAR = dict(south=37.7700, west=-122.4200, north=37.8095, east=-122.3700, width=1000)
CITY = dict(south=37.7040, west=-122.5200, north=37.8130, east=-122.3550, width=1200)

# class -> (layer, stroke width in drawing units). Layers draw thin to thick.
NEAR_CLASS = {
    "alley": ("c", 1.3), "pedestrian": ("c", 1.3), "living_street": ("c", 1.3),
    "residential": ("b", 2.6), "unclassified": ("b", 2.6), "tertiary": ("b", 2.6), "tertiary_link": ("b", 2.6),
    "secondary": ("a", 3.6), "secondary_link": ("b", 2.6), "primary": ("a", 3.6), "primary_link": ("b", 2.6),
    "trunk": ("a", 3.6), "motorway": ("a", 3.6), "motorway_link": ("b", 2.6), "trunk_link": ("b", 2.6),
}
CITY_CLASS = {"tertiary": ("c", 1.0), "secondary": ("b", 1.6), "primary": ("a", 2.4), "trunk": ("a", 2.4), "motorway": ("a", 2.4)}
WIDTHS = {"near": {"a": 3.6, "b": 2.6, "c": 1.3, "shore": 1.0}, "city": {"a": 2.4, "b": 1.6, "c": 1.0, "shore": 1.2}}


def projector(box):
    kx = box["width"] / (box["east"] - box["west"])
    # one degree of latitude is longer on the ground than one of longitude here
    ky = kx / math.cos(math.radians((box["south"] + box["north"]) / 2))
    height = round((box["north"] - box["south"]) * ky)
    return kx, ky, height


def thin(pts, tol):
    """Drops points that sit within tol of the straight line between their
    neighbours (Ramer-Douglas-Peucker), so a straight street is two points."""
    if len(pts) < 3: return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1e-9
    far, at = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * (pts[i][0] - x1) - dx * (pts[i][1] - y1)) / L if L > 1e-6 else math.hypot(pts[i][0] - x1, pts[i][1] - y1)
        if d > far: far, at = d, i
    if far <= tol: return [pts[0], pts[-1]]
    return thin(pts[:at + 1], tol)[:-1] + thin(pts[at:], tol)


def path_of(points, box, kx, ky, height, close=False, tol=0.35, step=0.5):
    """One way as an SVG path fragment, clipped loosely to the frame."""
    out, run, last = [], [], None
    pad = 30
    for p in points:
        x = (p["lon"] - box["west"]) * kx
        y = (box["north"] - p["lat"]) * ky
        inside = -pad <= x <= box["width"] + pad and -pad <= y <= height + pad
        if inside:
            pt = (round(x / step) * step, round(y / step) * step)
            if pt != last:
                run.append(pt); last = pt
        else:
            if len(run) > 1: out.append(run)
            run, last = [], None
    if len(run) > 1: out.append(run)
    frag = ""
    for r in out:
        r = thin(r, tol)
        frag += "M" + " ".join(f"{x:g},{y:g}" for x, y in r)      # pairs after M are implicit line-tos
        if close: frag += "Z"
    return frag


def draw(raw, box, classes, with_piers, tol=0.35, step=0.5):
    kx, ky, height = projector(box)
    def line(g, close=False): return path_of(g, box, kx, ky, height, close, tol, step)
    layers = {"a": [], "b": [], "c": [], "shore": [], "pier": []}
    for e in raw["elements"]:
        g = e.get("geometry")
        if not g: continue
        t = e.get("tags", {})
        if t.get("natural") == "coastline":
            layers["shore"].append(line(g)); continue
        if t.get("man_made") == "pier":
            # the big finger piers read as the waterfront; boat slips are noise
            span = max(max(p["lat"] for p in g) - min(p["lat"] for p in g), (max(p["lon"] for p in g) - min(p["lon"] for p in g)) * 0.79)
            if with_piers and span > 0.0006: layers["pier"].append(line(g, close=g[0] == g[-1]))
            continue
        hw = t.get("highway")
        if hw == "service": hw = "alley" if t.get("service") == "alley" else None
        if hw == "pedestrian" and (t.get("area") == "yes" or g[0] == g[-1]): continue   # plazas, not streets
        if hw not in classes: continue
        if t.get("tunnel") in ("yes", "building_passage"): continue
        layers[classes[hw][0]].append(line(g))
    return {"w": box["width"], "h": height, "west": box["west"], "north": box["north"], "kx": round(kx, 3), "ky": round(ky, 3),
            "layers": {k: "".join(v) for k, v in layers.items() if v}}


def main():
    src = sys.argv[1]
    load = lambda n: json.load(open(os.path.join(src, n), encoding="utf-8"))
    near = draw(load("osm_near.json"), NEAR, NEAR_CLASS, True)
    city = draw(load("osm_city.json"), CITY, CITY_CLASS, False, tol=0.5, step=1)
    near["widths"], city["widths"] = WIDTHS["near"], WIDTHS["city"]
    home = next(e for e in load("osm_home.json")["elements"] if e["type"] == "way" and e["id"] == HOME_WAY)["geometry"]
    lat = sum(p["lat"] for p in home[:-1]) / (len(home) - 1)
    lon = sum(p["lon"] for p in home[:-1]) / (len(home) - 1)
    kx, ky, h = projector(NEAR)
    near["home"] = path_of(home, NEAR, kx, ky, h, close=True, tol=0.02, step=0.1)
    out = {"credit": "Streets: OpenStreetMap contributors", "home": {"lat": round(lat, 6), "lon": round(lon, 6)},
           "near": near, "city": city}
    dest = os.path.join(HERE, "guide_map.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), separators=(",", ":"))
    print("wrote", dest, os.path.getsize(dest), "bytes; near", near["w"], "x", near["h"], "city", city["w"], "x", city["h"],
          "home", out["home"])


if __name__ == "__main__":
    main()
