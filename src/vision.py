"""Vision — Roblox; kill-feed + death; rail/portal (portal NEVER counted as danger)."""
from __future__ import annotations
import numpy as np
import cv2
from typing import Optional, Dict, Any

try:
    import mss
except ImportError:
    mss = None
try:
    import pygetwindow as gw
except ImportError:
    gw = None

from .config import CAPTURE_W, CAPTURE_H, N_SENSORY


class VisionEncoder:
    def __init__(self, monitor_index: int = 1) -> None:
        self.monitor_index = monitor_index
        self.sct = mss.mss() if mss is not None else None
        self.last_frame: Optional[np.ndarray] = None
        self.last_gray: Optional[np.ndarray] = None
        self.prev_gray: Optional[np.ndarray] = None
        self.last_region: Optional[dict] = None
        self.last_meta: Dict[str, Any] = {}
        self._last_title = ""
        self._prev_kill_score = 0.0
        self._prev_death_score = 0.0
        self._prev_portal = 0.0

    def find_roblox_window_info(self):
        if gw is None:
            return None
        try:
            best = None
            best_area = 0
            for w in gw.getAllWindows():
                title = w.title or ""
                tl = title.lower()
                if not tl or "fruitfly" in tl or "roblox" not in tl:
                    continue
                if w.width < 400 or w.height < 300:
                    continue
                area = max(0, w.width) * max(0, w.height)
                if area > best_area:
                    best_area = area
                    is_exp = "chrome" not in tl and "edge" not in tl and "firefox" not in tl
                    best = {
                        "left": int(w.left), "top": int(w.top),
                        "width": int(w.width), "height": int(w.height),
                        "title": title, "is_experience": is_exp,
                    }
            return best
        except Exception:
            return None

    def _find_roblox_region(self):
        info = self.find_roblox_window_info()
        if not info:
            return None
        self._last_title = info.get("title", "")
        return {k: info[k] for k in ("left", "top", "width", "height")}

    def capture(self, region=None) -> np.ndarray:
        if self.sct is None:
            frame = np.zeros((CAPTURE_H, CAPTURE_W, 3), dtype=np.uint8)
            self.last_frame = frame
            return frame
        if region is None:
            region = self._find_roblox_region()
        if region is None:
            frame = np.zeros((CAPTURE_H, CAPTURE_W, 3), dtype=np.uint8)
            cv2.putText(frame, "NO ROBLOX WINDOW", (40, CAPTURE_H // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 180, 255), 2)
            self.last_frame = frame
            self.last_meta = {"motion": 0, "food_score": 0, "loom_score": 0, "no_roblox": True,
                              "water_score": 0, "lobby_score": 0, "threat_score": 0,
                              "rail_score": 0, "portal_score": 0, "threat_cx": 0.5,
                              "kill_score": 0, "kill_event": False,
                              "death_score": 0, "death_event": False,
                              "portal_event": False, "arena_hint": 0.0}
            return frame
        self.last_region = region
        try:
            shot = self.sct.grab(region)
            frame = np.array(shot)[:, :, :3]
            frame = cv2.resize(frame, (CAPTURE_W, CAPTURE_H), interpolation=cv2.INTER_AREA)
        except Exception:
            frame = np.zeros((CAPTURE_H, CAPTURE_W, 3), dtype=np.uint8)
        self.last_frame = frame
        return frame

    def encode(self, frame: Optional[np.ndarray] = None) -> np.ndarray:
        if frame is None:
            frame = self.last_frame
        if frame is None:
            return np.zeros(N_SENSORY, dtype=np.float32)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        self.prev_gray = self.last_gray
        self.last_gray = gray
        feats = []
        hist = np.histogram(gray, bins=28, range=(0.0, 1.0))[0].astype(np.float32)
        hist = hist / (hist.sum() + 1e-6)
        feats.append(hist)
        sx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        feats.append(np.array([float(np.mean(np.abs(sx))), float(np.mean(np.abs(sy))),
                               float(np.std(sx)), float(np.std(sy))], dtype=np.float32))
        motion = 0.0
        if self.prev_gray is not None:
            diff = np.abs(gray - self.prev_gray)
            motion = float(np.mean(diff))
            feats.append(np.array([motion, float(np.std(diff)), float(np.percentile(diff, 90))], dtype=np.float32))
        else:
            feats.append(np.zeros(3, dtype=np.float32))
        bright = (gray > 0.65).astype(np.float32)
        if bright.sum() > 10:
            ys, xs = np.where(bright > 0)
            cx, cy = float(xs.mean()) / CAPTURE_W, float(ys.mean()) / CAPTURE_H
        else:
            cx, cy = 0.5, 0.5
        dark = (gray < 0.25).astype(np.float32)
        if dark.sum() > 10:
            ys, xs = np.where(dark > 0)
            dx, dy = float(xs.mean()) / CAPTURE_W, float(ys.mean()) / CAPTURE_H
        else:
            dx, dy = 0.5, 0.5
        feats.append(np.array([cx, cy, dx, dy, float(bright.mean()), float(dark.mean())], dtype=np.float32))
        means = frame.mean(axis=(0, 1)).astype(np.float32) / 255.0
        stds = frame.std(axis=(0, 1)).astype(np.float32) / 255.0
        feats.append(means)
        feats.append(stds)
        h2, w2 = max(1, CAPTURE_H // 2), max(1, CAPTURE_W // 2)
        q = [float(gray[r:r + h2, c:c + w2].mean()) for r in (0, h2) for c in (0, w2)]
        feats.append(np.array(q, dtype=np.float32))
        h4, w4 = max(1, CAPTURE_H // 4), max(1, CAPTURE_W // 4)
        grid = [float(gray[r:r + h4, c:c + w4].mean())
                for r in range(0, CAPTURE_H, h4) for c in range(0, CAPTURE_W, w4)]
        feats.append(np.array(grid[:16], dtype=np.float32))
        small = cv2.resize(gray, (12, 8), interpolation=cv2.INTER_AREA).ravel().astype(np.float32)
        feats.append(small)
        cy0, cx0 = CAPTURE_H // 2, CAPTURE_W // 2
        y0, y1 = max(0, cy0 - 30), min(CAPTURE_H, cy0 + 30)
        x0, x1 = max(0, cx0 - 40), min(CAPTURE_W, cx0 + 40)
        center = float(gray[y0:y1, x0:x1].mean()) if y1 > y0 and x1 > x0 else float(gray.mean())
        edge = float(np.mean(np.abs(sx)) + np.mean(np.abs(sy)))
        feats.append(np.array([center, edge], dtype=np.float32))
        vec = np.concatenate(feats).astype(np.float32)
        if vec.size < N_SENSORY:
            vec = np.pad(vec, (0, N_SENSORY - vec.size))
        else:
            vec = vec[:N_SENSORY]
        np.clip(vec, 0.0, 1.0, out=vec)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # --- PORTAL first (magenta / cyan / bright purple) — never threat ---
        hsv_mid = hsv[int(CAPTURE_H * 0.12):int(CAPTURE_H * 0.88), :, :]
        portal_m1 = cv2.inRange(hsv_mid, (125, 50, 90), (165, 255, 255))   # magenta/purple
        portal_m2 = cv2.inRange(hsv_mid, (80, 70, 110), (110, 255, 255))    # cyan/teal portals
        portal_m3 = cv2.inRange(hsv_mid, (140, 30, 160), (175, 180, 255))   # bright pink/white portal glow
        portal_mask = cv2.bitwise_or(portal_m1, cv2.bitwise_or(portal_m2, portal_m3))
        # dilate slightly for stable blob
        portal_mask = cv2.morphologyEx(portal_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        portal_ratio = float(np.count_nonzero(portal_mask)) / float(max(1, portal_mask.size))
        portal_score = 0.0
        portal_cx, portal_cy = 0.5, 0.5
        if 0.002 < portal_ratio < 0.30:
            portal_score = min(1.0, portal_ratio * 18.0)
            ys, xs = np.where(portal_mask > 0)
            if len(xs):
                portal_cx = float(xs.mean()) / CAPTURE_W
                portal_cy = float(np.clip(float(ys.mean()) / max(1, hsv_mid.shape[0]), 0.0, 1.0))
        prev_p = float(self._prev_portal)
        portal_event = portal_score > 0.35 and prev_p < 0.20
        # entered portal: score was high then collapsed with motion burst
        portal_passed = prev_p > 0.4 and portal_score < 0.12 and motion > 0.04
        self._prev_portal = 0.88 * prev_p + 0.12 * portal_score

        # food
        mask_y = cv2.inRange(hsv, (18, 80, 80), (40, 255, 255))
        mask_r1 = cv2.inRange(hsv, (0, 90, 70), (12, 255, 255))
        mask_r2 = cv2.inRange(hsv, (165, 90, 70), (180, 255, 255))
        mask_g = cv2.inRange(hsv, (35, 60, 60), (85, 255, 255))
        food_mask = cv2.bitwise_or(mask_y, cv2.bitwise_or(mask_r1, cv2.bitwise_or(mask_r2, mask_g)))
        # remove portal pixels from food
        if portal_mask is not None and portal_mask.shape[:2] == food_mask[int(CAPTURE_H * 0.12):int(CAPTURE_H * 0.88)].shape[:2]:
            fm = food_mask[int(CAPTURE_H * 0.12):int(CAPTURE_H * 0.88)].copy()
            fm[portal_mask > 0] = 0
            food_mask[int(CAPTURE_H * 0.12):int(CAPTURE_H * 0.88)] = fm
        food_ratio = float(np.count_nonzero(food_mask)) / float(food_mask.size)
        food_score = 0.0
        if 0.004 < food_ratio < 0.25:
            food_score = min(1.0, food_ratio * 12.0)

        y0c, y1c = max(0, cy0 - 40), min(CAPTURE_H, cy0 + 40)
        x0c, x1c = max(0, cx0 - 50), min(CAPTURE_W, cx0 + 50)
        center_patch = gray[y0c:y1c, x0c:x1c]
        if self.prev_gray is not None:
            center_motion = float(np.mean(np.abs(center_patch - self.prev_gray[y0c:y1c, x0c:x1c])))
        else:
            center_motion = 0.0
        center_dark = float(np.mean(center_patch < 0.35))
        loom_score = float(np.clip(center_motion * 4.0 + center_dark * 0.5, 0.0, 1.0))

        y_water0 = int(CAPTURE_H * 0.65)
        hsv_bottom = hsv[y_water0:, :, :]
        water_mask = cv2.inRange(hsv_bottom, (95, 100, 70), (125, 255, 220))
        water_ratio = float(np.count_nonzero(water_mask)) / float(max(1, water_mask.size))
        water_score = 0.0
        water_cx = 0.5
        if water_ratio > 0.22:
            water_score = min(1.0, (water_ratio - 0.18) * 4.0)
            ys, xs = np.where(water_mask > 0)
            if len(xs) > 0:
                water_cx = float(xs.mean()) / CAPTURE_W

        border = np.concatenate([
            gray[:12, :].ravel(), gray[-12:, :].ravel(),
            gray[:, :12].ravel(), gray[:, -12:].ravel(),
        ])
        border_bright = float(np.mean(border > 0.7))
        lobby_score = 0.0
        if motion < 0.03 and border_bright > 0.15 and float(gray.mean()) > 0.25:
            lobby_score = min(1.0, border_bright * 2.0 + (0.04 - motion) * 8.0)

        # THREAT = true enemy red, EXCLUDING portal mask regions
        red1 = cv2.inRange(hsv, (0, 110, 90), (10, 255, 255))
        red2 = cv2.inRange(hsv, (170, 110, 90), (180, 255, 255))
        red_mask = cv2.bitwise_or(red1, red2)
        # punch out portal area so purple portals never count as danger
        mid_y0, mid_y1 = int(CAPTURE_H * 0.12), int(CAPTURE_H * 0.88)
        if portal_score > 0.08:
            sub = red_mask[mid_y0:mid_y1]
            if sub.shape == portal_mask.shape:
                sub[portal_mask > 0] = 0
                red_mask[mid_y0:mid_y1] = sub
        red_ratio = float(np.count_nonzero(red_mask)) / float(frame.shape[0] * frame.shape[1])
        # when portal is dominant, force threat down
        threat_raw = float(np.clip(center_motion * 3.2 + red_ratio * 9.0 + loom_score * 0.4, 0.0, 1.0))
        if portal_score > 0.25:
            threat_raw *= 0.15  # portal scene is not combat danger
        elif portal_score > 0.12:
            threat_raw *= 0.45
        threat_score = threat_raw

        y0r, y1r = int(CAPTURE_H * 0.35), int(CAPTURE_H * 0.80)
        lower = gray[y0r:y1r, :]
        col = lower.mean(axis=0)
        ker = np.ones(11, dtype=np.float32) / 11.0
        col_s = np.convolve(col, ker, mode="same")
        rail_i = int(np.argmax(col_s))
        rail_cx = float(rail_i) / float(CAPTURE_W)
        peak = float(col_s.max())
        mean = float(col_s.mean()) + 1e-6
        rail_score = float(np.clip((peak - mean) / mean * 2.5, 0.0, 1.0))
        if peak < 0.25:
            rail_score *= 0.4

        threat_cx = 0.5
        if red_ratio > 0.008 and portal_score < 0.2:
            ys, xs = np.where(red_mask > 0)
            if len(xs):
                threat_cx = float(xs.mean()) / CAPTURE_W

        top = hsv[: max(1, int(CAPTURE_H * 0.22)), :, :]
        gold = cv2.inRange(top, (15, 80, 140), (40, 255, 255))
        white = cv2.inRange(top, (0, 0, 200), (180, 40, 255))
        kill_blob = cv2.bitwise_or(gold, white)
        kill_ratio = float(np.count_nonzero(kill_blob)) / float(max(1, kill_blob.size))
        top_red1 = cv2.inRange(top, (0, 120, 100), (12, 255, 255))
        top_red2 = cv2.inRange(top, (165, 120, 100), (180, 255, 255))
        top_red = float(np.count_nonzero(cv2.bitwise_or(top_red1, top_red2))) / float(max(1, top.shape[0] * top.shape[1]))
        kill_score = float(np.clip(kill_ratio * 14.0 + top_red * 6.0, 0.0, 1.0))
        prev_ks = float(self._prev_kill_score)
        kill_event = kill_score > 0.28 and prev_ks < 0.18
        self._prev_kill_score = 0.9 * prev_ks + 0.1 * kill_score

        mean_bgr = frame.mean(axis=(0, 1))
        red_bias = float(mean_bgr[2] - mean_bgr[1]) / 255.0
        center_mean = float(gray[y0c:y1c, x0c:x1c].mean()) if y1c > y0c else float(gray.mean())
        death_score = float(np.clip(
            max(0.0, red_bias) * 3.0 + max(0.0, 0.35 - center_mean) * 2.0 + (0.2 if float(gray.mean()) < 0.22 else 0.0),
            0.0, 1.0,
        ))
        prev_ds = float(self._prev_death_score)
        death_event = death_score > 0.42 and prev_ds < 0.25
        self._prev_death_score = 0.88 * prev_ds + 0.12 * death_score

        # arena hint: high motion + low lobby + not pure portal UI
        arena_hint = float(np.clip(
            (0.0 if lobby_score > 0.4 else 0.35)
            + (0.4 if motion > 0.04 else 0.0)
            + (0.35 if kill_score > 0.15 else 0.0)
            - (0.5 if portal_score > 0.3 else 0.0),
            0.0, 1.0,
        ))

        self.last_meta = {
            "motion": motion, "food_score": food_score, "brightness": float(gray.mean()),
            "edge": edge, "center_bright": center, "loom_score": loom_score,
            "no_roblox": False, "window_title": self._last_title,
            "water_score": water_score, "water_cx": water_cx,
            "lobby_score": lobby_score, "threat_score": threat_score,
            "rail_score": rail_score, "rail_cx": rail_cx,
            "portal_score": portal_score, "portal_cx": portal_cx, "portal_cy": portal_cy,
            "portal_event": bool(portal_event), "portal_passed": bool(portal_passed),
            "threat_cx": threat_cx,
            "kill_score": kill_score, "kill_event": bool(kill_event),
            "death_score": death_score, "death_event": bool(death_event),
            "arena_hint": arena_hint,
        }
        return vec

    def close(self) -> None:
        if self.sct is not None:
            try:
                self.sct.close()
            except Exception:
                pass
