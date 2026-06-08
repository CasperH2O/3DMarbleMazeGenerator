"""
Flange hole/peg angle detector for puzzle case calibration.

Renders a PDF flatbed scan, auto-detects the flange ring, then lets you
interactively tune the annular search band and the zero-reference angle.
You can also place manual markers by right-clicking directly on features.

Dependencies:
    pip install pymupdf opencv-python numpy

Usage:
    python "tools/angle_detector/flange_angle_detector.py"

Interactive controls:
    Scroll wheel    Zoom in / out (centred on cursor)
    Middle-drag     Pan
    Left-click      Rotate the zero-reference line to point toward the cursor
    Right-click     On an auto dot  → exclude it (shown as ✕; right-click again to restore)
                    On a ✕ mark     → restore the excluded feature
                    On a green dot  → remove manual marker
                    Elsewhere       → add manual marker
    A               Toggle auto-detected features on/off
    C               Clear all exclusions (restore all auto features)
    R               Reset everything (centre, band, zoom, exclusions, manual markers)
    I / Shift-I     Grow / shrink inner annular radius (5 px steps)
    O / Shift-O     Grow / shrink outer annular radius (5 px steps)
    [ / ]           Decrease / increase minimum feature area (filter tiny noise)
    { / }           Decrease / increase maximum feature area (filter large blobs)
    , / .           Decrease / increase circularity threshold (0=any shape, 1=perfect circle)
    Z               Anchor 0° to the feature nearest the top of the ring
    S               Save all visible angles to detected_angles.txt and exit
    Q / Escape      Quit without saving
"""

from pathlib import Path
import math

import cv2
import numpy as np

# ── PyMuPDF for PDF → image conversion ───────────────────────────────────
try:
    import fitz  # PyMuPDF
    _HAS_FITZ = True
except ImportError:
    _HAS_FITZ = False

# ── Paths ─────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
SCAN_PDF = SCRIPT_DIR / "scan.pdf"
SCAN_PNG = SCRIPT_DIR / "_scan_render_cache.png"
OUTPUT_TXT = SCRIPT_DIR / "detected_angles.txt"

# ── Render resolution — higher = more precise but slower ──────────────────
DPI = 200

# ── Adaptive threshold parameters ────────────────────────────────────────
BLUR_KERNEL = 5
ADAPTIVE_BLOCK = 51   # must be odd; increase for low-contrast scans
ADAPTIVE_C = 5

# ── Feature filters — the main knobs for reducing false positives ─────────
#
# MIN_AREA / MAX_AREA  Filter by contour area in pixels².
#   Raise MIN_AREA to reject tiny speckles and noise.
#   Lower MAX_AREA to reject large blobs (ring body, dome reflection).
#
# MIN_CIRCULARITY  Ratio 4π·area/perimeter² — 1.0 = perfect circle, 0 = any.
#   The actual holes/pegs score ~0.65–0.90.
#   Raise this to reject elongated or irregular shapes (clips, edge artefacts).
#   Start around 0.5 and increase until false positives disappear.
MIN_AREA = 100
MAX_AREA = 8_000
MIN_CIRCULARITY = 0.0   # disabled by default — raise to ~0.5 to filter non-circular blobs

# ── Initial annular band as fraction of the Hough-detected ring radius ────
INNER_FRAC = 0.82
OUTER_FRAC = 1.08

# ── How close a right-click must be to act on an existing feature ─────────
REMOVE_RADIUS_PX = 15   # in display pixels


# ── PDF loading ───────────────────────────────────────────────────────────

def pdf_to_gray(pdf_path: Path, dpi: int) -> np.ndarray:
    if not _HAS_FITZ:
        raise ImportError("Install PyMuPDF:  pip install pymupdf")
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)


def load_gray(pdf_path: Path, cache_path: Path, dpi: int) -> np.ndarray:
    """Return cached PNG if available, otherwise render from PDF."""
    if cache_path.exists():
        img = cv2.imread(str(cache_path), cv2.IMREAD_GRAYSCALE)
        if img is not None:
            print(f"Using cached render: {cache_path}")
            return img
    print(f"Rendering PDF at {dpi} DPI …")
    img = pdf_to_gray(pdf_path, dpi)
    cv2.imwrite(str(cache_path), img)
    return img


# ── Flange circle auto-detection ──────────────────────────────────────────

def detect_ring(gray: np.ndarray) -> tuple[int, int, int]:
    """Return (cx, cy, radius) of the dominant circular ring."""
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    h, w = gray.shape
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=min(h, w) // 2,
        param1=50,
        param2=30,
        minRadius=min(h, w) // 6,
        maxRadius=min(h, w) // 2,
    )
    if circles is None:
        return w // 2, h // 2, min(h, w) // 3
    cx, cy, r = circles[0, 0]
    return int(cx), int(cy), int(r)


# ── Angle calculation (shared by auto and manual) ─────────────────────────

def point_to_feature(
    x: float, y: float, cx: int, cy: int, zero_offset_deg: float
) -> dict:
    raw = math.degrees(math.atan2(cy - y, x - cx)) % 360
    return {"x": x, "y": y, "raw": raw, "angle": (raw - zero_offset_deg) % 360}


# ── Auto feature detection ────────────────────────────────────────────────

def find_auto_features(
    gray: np.ndarray,
    cx: int,
    cy: int,
    inner_r: float,
    outer_r: float,
    zero_offset_deg: float,
    excluded: list[tuple[float, float]],
    exclude_radius_img: float,
    min_area: float,
    max_area: float,
    min_circularity: float,
) -> tuple[list[dict], list[dict]]:
    """
    Returns (visible_features, excluded_features).
    excluded_features are detected but suppressed because their centroid
    is within exclude_radius_img pixels of a position in `excluded`.
    """
    blurred = cv2.GaussianBlur(gray, (BLUR_KERNEL, BLUR_KERNEL), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        ADAPTIVE_BLOCK,
        ADAPTIVE_C,
    )
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    visible, suppressed = [], []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if not (min_area <= area <= max_area):
            continue
        if min_circularity > 0:
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0:
                continue
            circularity = 4 * math.pi * area / (perimeter ** 2)
            if circularity < min_circularity:
                continue
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue
        fx = M["m10"] / M["m00"]
        fy = M["m01"] / M["m00"]
        if not (inner_r <= math.hypot(fx - cx, fy - cy) <= outer_r):
            continue
        feat = point_to_feature(fx, fy, cx, cy, zero_offset_deg)
        if any(math.hypot(fx - ex, fy - ey) < exclude_radius_img for ex, ey in excluded):
            suppressed.append(feat)
        else:
            visible.append(feat)

    visible.sort(key=lambda f: f["angle"])
    suppressed.sort(key=lambda f: f["angle"])
    return visible, suppressed


# ── Viewport helpers ──────────────────────────────────────────────────────

def clamp_pan(
    pan_x: float, pan_y: float,
    zoom: float, disp_w: int, disp_h: int,
    img_w: int, img_h: int,
) -> tuple[float, float]:
    max_x = max(0.0, img_w - disp_w / zoom)
    max_y = max(0.0, img_h - disp_h / zoom)
    return max(0.0, min(pan_x, max_x)), max(0.0, min(pan_y, max_y))


def display_to_image(
    mx: float, my: float, pan_x: float, pan_y: float, zoom: float
) -> tuple[float, float]:
    return mx / zoom + pan_x, my / zoom + pan_y


def crop_viewport(
    img: np.ndarray,
    pan_x: float, pan_y: float,
    zoom: float, disp_w: int, disp_h: int,
) -> np.ndarray:
    """Crop the viewport region from a full-resolution image and resize to display."""
    ih, iw = img.shape[:2]
    x1 = max(0, int(pan_x))
    y1 = max(0, int(pan_y))
    x2 = min(iw, int(pan_x + disp_w / zoom) + 1)
    y2 = min(ih, int(pan_y + disp_h / zoom) + 1)
    if x2 <= x1 or y2 <= y1:
        return np.zeros((disp_h, disp_w, 3), dtype=np.uint8)
    return cv2.resize(img[y1:y2, x1:x2], (disp_w, disp_h), interpolation=cv2.INTER_LINEAR)


# ── Overlay drawing ───────────────────────────────────────────────────────

def draw_overlay(
    bgr: np.ndarray,
    cx: int,
    cy: int,
    ring_r: int,
    inner_r: float,
    outer_r: float,
    auto_features: list[dict],
    excluded_features: list[dict],
    manual_features: list[dict],
    show_auto: bool,
    zero_offset_deg: float,
) -> np.ndarray:
    out = bgr.copy()

    # Auto-detected ring outline (faint blue)
    cv2.circle(out, (cx, cy), ring_r, (180, 80, 0), 1, cv2.LINE_AA)

    # Annular search band (cyan)
    cv2.circle(out, (cx, cy), int(inner_r), (0, 180, 255), 1, cv2.LINE_AA)
    cv2.circle(out, (cx, cy), int(outer_r), (0, 180, 255), 1, cv2.LINE_AA)

    # Zero-reference ray (green)
    ref_rad = math.radians(zero_offset_deg)
    rx = int(cx + outer_r * math.cos(ref_rad))
    ry = int(cy - outer_r * math.sin(ref_rad))
    cv2.line(out, (cx, cy), (rx, ry), (0, 255, 0), 1, cv2.LINE_AA)

    # Centre cross
    cv2.drawMarker(out, (cx, cy), (0, 255, 0), cv2.MARKER_CROSS, 24, 2)

    # Excluded auto features — faint ✕ marks so you can click to restore them
    for f in excluded_features:
        px, py = int(f["x"]), int(f["y"])
        cv2.drawMarker(out, (px, py), (60, 60, 180), cv2.MARKER_TILTED_CROSS, 12, 1, cv2.LINE_AA)

    # Visible auto features (red/orange)
    if show_auto:
        for f in auto_features:
            px, py = int(f["x"]), int(f["y"])
            cv2.circle(out, (px, py), 7, (0, 60, 255), -1)
            cv2.circle(out, (px, py), 7, (200, 200, 200), 1)
            cv2.putText(out, f"{f['angle']:.1f}°", (px + 9, py + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 180, 255), 1, cv2.LINE_AA)

    # Manual features (lime green) — drawn on top
    for f in manual_features:
        px, py = int(f["x"]), int(f["y"])
        cv2.circle(out, (px, py), 9, (0, 220, 60), -1)
        cv2.circle(out, (px, py), 9, (255, 255, 255), 1)
        cv2.putText(out, f"{f['angle']:.1f}°", (px + 11, py + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 100), 1, cv2.LINE_AA)

    return out


def draw_hud(
    display_img: np.ndarray,
    auto_features: list[dict],
    excluded_features: list[dict],
    manual_features: list[dict],
    show_auto: bool,
    inner_r: float,
    outer_r: float,
    zero_offset_deg: float,
    view_zoom: float,
    state: dict,
) -> None:
    """Draw the HUD text onto the already-cropped display image (in-place)."""
    auto_label = f"auto:{len(auto_features)}" if show_auto else "auto:off"
    excl_label = f"excl:{len(excluded_features)}" if excluded_features else ""
    zoom_label = f"zoom:{view_zoom:.1f}x"
    counts = "  ".join(filter(None, [auto_label, excl_label, f"man:{len(manual_features)}", zoom_label]))
    hud_lines = [
        f"{counts}  band=[{inner_r:.0f},{outer_r:.0f}]  "
        f"area=[{state['min_area']:.0f},{state['max_area']:.0f}]  "
        f"circ≥{state['min_circ']:.2f}  zero={zero_offset_deg:.1f}°",
        "L-click=zero  R=exclude/add  scroll=zoom  M-drag=pan  "
        "[/] area-min  {/} area-max  ,/. circularity  I/i O/o band  Z=snap  R=reset  S=save  Q=quit",
    ]
    for row, text in enumerate(hud_lines):
        cv2.putText(display_img, text, (10, 28 + row * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1, cv2.LINE_AA)


# ── Output ────────────────────────────────────────────────────────────────

def print_and_save(
    auto_features: list[dict],
    manual_features: list[dict],
    show_auto: bool,
    path: Path,
) -> None:
    combined = []
    if show_auto:
        combined.extend({"src": "auto", **f} for f in auto_features)
    combined.extend({"src": "manual", **f} for f in manual_features)
    combined.sort(key=lambda f: f["angle"])

    n_auto = sum(1 for f in combined if f["src"] == "auto")
    n_manual = len(combined) - n_auto

    print(f"\n{len(combined)} features ({n_auto} auto, {n_manual} manual):")
    print("angles_deg = [")
    for f in combined:
        print(f"    {f['angle']:.1f},  # {f['src']}")
    print("]")

    lines = [
        "# Detected flange feature angles",
        "# Convention: 0° = reference (set with Z), counter-clockwise positive",
        f"# {len(combined)} features  ({n_auto} auto-detected, {n_manual} manual)",
        "",
        "angles_deg = [",
    ] + [f"    {f['angle']:.1f},  # {f['src']}" for f in combined] + ["]"]
    path.write_text("\n".join(lines))
    print(f"\nSaved → {path}")


# ── Main loop ─────────────────────────────────────────────────────────────

def run(pdf_path: Path = SCAN_PDF) -> None:
    gray = load_gray(pdf_path, SCAN_PNG, DPI)
    bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    cx0, cy0, ring_r0 = detect_ring(gray)
    print(f"Auto-detected centre ({cx0}, {cy0}), ring radius ≈ {ring_r0} px")

    h, w = gray.shape
    # Fit-to-window scale: image → display at view_zoom=1
    base_scale = min(1.0, 900 / h)
    disp_w, disp_h = int(w * base_scale), int(h * base_scale)

    state = {
        "cx": cx0, "cy": cy0, "ring_r": ring_r0,
        "inner_r": ring_r0 * INNER_FRAC,
        "outer_r": ring_r0 * OUTER_FRAC,
        "zero_offset": 0.0,
        "show_auto": True,
        "min_area": MIN_AREA,
        "max_area": MAX_AREA,
        "min_circ": MIN_CIRCULARITY,
        "excluded": [],      # list of (image_x, image_y) — auto features to suppress
        "manual": [],        # list of (image_x, image_y) — manually placed markers
        "auto_features": [],
        "excluded_features": [],
        "manual_features": [],
        # viewport
        "view_zoom": 1.0,    # user zoom level (1.0 = fit to window)
        "pan_x": 0.0,        # top-left of viewport in image pixels
        "pan_y": 0.0,
        # middle-drag tracking
        "drag_active": False,
        "drag_start_mx": 0,
        "drag_start_my": 0,
        "drag_start_pan_x": 0.0,
        "drag_start_pan_y": 0.0,
    }

    def current_zoom() -> float:
        return base_scale * state["view_zoom"]

    def hit_radius_img() -> float:
        """Click hit-test radius in image pixels, constant in display pixels."""
        return REMOVE_RADIUS_PX / current_zoom()

    def disp_to_img(mx: float, my: float) -> tuple[float, float]:
        return display_to_image(mx, my, state["pan_x"], state["pan_y"], current_zoom())

    def recompute_manual_features():
        state["manual_features"] = [
            point_to_feature(ix, iy, state["cx"], state["cy"], state["zero_offset"])
            for ix, iy in state["manual"]
        ]
        state["manual_features"].sort(key=lambda f: f["angle"])

    def refresh():
        visible, suppressed = find_auto_features(
            gray, state["cx"], state["cy"],
            state["inner_r"], state["outer_r"],
            state["zero_offset"],
            state["excluded"], hit_radius_img(),
            state["min_area"], state["max_area"], state["min_circ"],
        )
        state["auto_features"] = visible
        state["excluded_features"] = suppressed
        recompute_manual_features()
        redraw()

    def redraw():
        """Redraw without re-running the threshold — fast path for interaction."""
        recompute_manual_features()
        annotated = draw_overlay(
            bgr, state["cx"], state["cy"], state["ring_r"],
            state["inner_r"], state["outer_r"],
            state["auto_features"], state["excluded_features"],
            state["manual_features"],
            state["show_auto"], state["zero_offset"],
        )
        display_img = crop_viewport(
            annotated, state["pan_x"], state["pan_y"],
            current_zoom(), disp_w, disp_h,
        )
        draw_hud(
            display_img,
            state["auto_features"], state["excluded_features"],
            state["manual_features"], state["show_auto"],
            state["inner_r"], state["outer_r"],
            state["zero_offset"], state["view_zoom"],
            state,
        )
        cv2.imshow("Flange angle detector", display_img)

    def mouse_cb(event, mx, my, flags, param):
        zoom = current_zoom()

        # ── Scroll to zoom ────────────────────────────────────────────────
        if event == cv2.EVENT_MOUSEWHEEL:
            factor = 1.25 if flags > 0 else (1 / 1.25)
            # Image point under cursor stays fixed
            ix, iy = disp_to_img(mx, my)
            state["view_zoom"] = max(1.0, min(state["view_zoom"] * factor, 20.0))
            new_zoom = current_zoom()
            state["pan_x"] = ix - mx / new_zoom
            state["pan_y"] = iy - my / new_zoom
            state["pan_x"], state["pan_y"] = clamp_pan(
                state["pan_x"], state["pan_y"], new_zoom, disp_w, disp_h, w, h
            )
            redraw()
            return

        # ── Middle-click drag to pan ──────────────────────────────────────
        if event == cv2.EVENT_MBUTTONDOWN:
            state["drag_active"] = True
            state["drag_start_mx"] = mx
            state["drag_start_my"] = my
            state["drag_start_pan_x"] = state["pan_x"]
            state["drag_start_pan_y"] = state["pan_y"]
            return

        if event == cv2.EVENT_MBUTTONUP:
            state["drag_active"] = False
            return

        if event == cv2.EVENT_MOUSEMOVE and state["drag_active"]:
            dx = (mx - state["drag_start_mx"]) / zoom
            dy = (my - state["drag_start_my"]) / zoom
            state["pan_x"], state["pan_y"] = clamp_pan(
                state["drag_start_pan_x"] - dx,
                state["drag_start_pan_y"] - dy,
                zoom, disp_w, disp_h, w, h,
            )
            redraw()
            return

        # ── Left-click: rotate zero-reference line ───────────────────────
        if event == cv2.EVENT_LBUTTONDOWN:
            ix, iy = disp_to_img(mx, my)
            raw = math.degrees(math.atan2(state["cy"] - iy, ix - state["cx"])) % 360
            state["zero_offset"] = raw
            refresh()
            return

        # ── Right-click: exclude / restore / add / remove ─────────────────
        if event == cv2.EVENT_RBUTTONDOWN:
            ix, iy = disp_to_img(mx, my)
            r = hit_radius_img()

            # 1. Restore an excluded auto feature?
            for i, (ex, ey) in enumerate(state["excluded"]):
                if math.hypot(ex - ix, ey - iy) < r:
                    state["excluded"].pop(i)
                    refresh()
                    return

            # 2. Exclude a visible auto feature?
            for f in state["auto_features"]:
                if math.hypot(f["x"] - ix, f["y"] - iy) < r:
                    state["excluded"].append((f["x"], f["y"]))
                    refresh()
                    return

            # 3. Remove a manual marker?
            for i, (px, py) in enumerate(state["manual"]):
                if math.hypot(px - ix, py - iy) < r:
                    state["manual"].pop(i)
                    redraw()
                    return

            # 4. Add a new manual marker
            state["manual"].append((ix, iy))
            redraw()

    cv2.namedWindow("Flange angle detector")
    cv2.setMouseCallback("Flange angle detector", mouse_cb)
    refresh()

    while True:
        key = cv2.waitKey(50) & 0xFF
        if key in (ord("q"), 27):
            break
        elif key == ord("r"):
            state.update({
                "cx": cx0, "cy": cy0, "ring_r": ring_r0,
                "inner_r": ring_r0 * INNER_FRAC,
                "outer_r": ring_r0 * OUTER_FRAC,
                "zero_offset": 0.0,
                "min_area": MIN_AREA,
                "max_area": MAX_AREA,
                "min_circ": MIN_CIRCULARITY,
                "excluded": [],
                "manual": [],
                "view_zoom": 1.0,
                "pan_x": 0.0,
                "pan_y": 0.0,
            })
            refresh()
        elif key == ord("c"):
            state["excluded"] = []
            refresh()
        elif key == ord("["):
            state["min_area"] = max(0, state["min_area"] - 50)
            refresh()
        elif key == ord("]"):
            state["min_area"] = min(state["max_area"] - 50, state["min_area"] + 50)
            refresh()
        elif key == ord("{"):
            state["max_area"] = max(state["min_area"] + 50, state["max_area"] - 500)
            refresh()
        elif key == ord("}"):
            state["max_area"] += 500
            refresh()
        elif key == ord(","):
            state["min_circ"] = max(0.0, round(state["min_circ"] - 0.05, 2))
            refresh()
        elif key == ord("."):
            state["min_circ"] = min(1.0, round(state["min_circ"] + 0.05, 2))
            refresh()
        elif key == ord("a"):
            state["show_auto"] = not state["show_auto"]
            redraw()
        elif key == ord("i"):
            state["inner_r"] = max(10, state["inner_r"] - 5)
            refresh()
        elif key == ord("I"):
            state["inner_r"] = min(state["outer_r"] - 10, state["inner_r"] + 5)
            refresh()
        elif key == ord("o"):
            state["outer_r"] = max(state["inner_r"] + 10, state["outer_r"] - 5)
            refresh()
        elif key == ord("O"):
            state["outer_r"] += 5
            refresh()
        elif key == ord("z"):
            all_feats = state["auto_features"] + state["manual_features"]
            if all_feats:
                closest = min(all_feats, key=lambda f: abs(f["raw"] - 90))
                state["zero_offset"] = closest["raw"]
                refresh()
        elif key == ord("s"):
            print_and_save(
                state["auto_features"], state["manual_features"],
                state["show_auto"], OUTPUT_TXT,
            )
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    run()
