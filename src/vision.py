"""Vision — Roblox only (no agent mirror), fruit HSV food, loom."""
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
            self.last_meta = {"motion": 0, "food_score": 0, "loom_score": 0, "no_roblox": True}
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
        hist = np.histogram(gray, bins=24, range=(0.0, 1.0))[0].astype(np.float32)
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
        small = cv2.resize(gray, (10, 6), interpolation=cv2.INTER_AREA).ravel().astype(np.float32)
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
        mask_y = cv2.inRange(hsv, (18, 80, 80), (40, 255, 255))
        mask_r1 = cv2.inRange(hsv, (0, 90, 70), (12, 255, 255))
        mask_r2 = cv2.inRange(hsv, (165, 90, 70), (180, 255, 255))
        mask_g = cv2.inRange(hsv, (35, 60, 60), (85, 255, 255))
        food_mask = cv2.bitwise_or(mask_y, cv2.bitwise_or(mask_r1, cv2.bitwise_or(mask_r2, mask_g)))
        food_ratio = float(np.count_nonzero(food_mask)) / float(food_mask.size)
        food_score = 0.0
        if 0.004 < food_ratio < 0.25:
            food_score = min(1.0, food_ratio * 12.0)
        y0, y1 = max(0, cy0 - 40), min(CAPTURE_H, cy0 + 40)
        x0, x1 = max(0, cx0 - 50), min(CAPTURE_W, cx0 + 50)
        center_patch = gray[y0:y1, x0:x1]
        if self.prev_gray is not None:
            center_motion = float(np.mean(np.abs(center_patch - self.prev_gray[y0:y1, x0:x1])))
        else:
            center_motion = 0.0
        center_dark = float(np.mean(center_patch < 0.35))
        loom_score = float(np.clip(center_motion * 4.0 + center_dark * 0.5, 0.0, 1.0))
        self.last_meta = {
            "motion": motion, "food_score": food_score, "brightness": float(gray.mean()),
            "edge": edge, "center_bright": center, "loom_score": loom_score,
            "no_roblox": False, "window_title": self._last_title,
        }
        return vec

    def close(self) -> None:
        if self.sct is not None:
            try:
                self.sct.close()
            except Exception:
                pass
