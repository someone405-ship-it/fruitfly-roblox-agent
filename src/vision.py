"""Vision encoder — Roblox window preferred, fixed N_SENSORY vector."""
from __future__ import annotations
import numpy as np
import cv2
from typing import Optional

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
        self.prefer_roblox = True

    def _find_roblox_region(self):
        if gw is None:
            return None
        try:
            wins = [w for w in gw.getAllWindows()
                    if w.title and "roblox" in w.title.lower() and getattr(w, "visible", True)]
            if not wins:
                return None
            w = max(wins, key=lambda x: max(0, x.width) * max(0, x.height))
            if w.width < 100 or w.height < 100:
                return None
            return {"left": int(w.left), "top": int(w.top), "width": int(w.width), "height": int(w.height)}
        except Exception:
            return None

    def capture(self, region=None) -> np.ndarray:
        if self.sct is None:
            frame = np.zeros((CAPTURE_H, CAPTURE_W, 3), dtype=np.uint8)
            self.last_frame = frame
            return frame
        if region is None and self.prefer_roblox:
            region = self._find_roblox_region()
        if region is None:
            mons = self.sct.monitors
            idx = min(self.monitor_index, len(mons) - 1)
            mon = mons[idx]
            region = {"left": mon["left"], "top": mon["top"], "width": mon["width"], "height": mon["height"]}
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
        feats.append(np.array([
            float(np.mean(np.abs(sx))), float(np.mean(np.abs(sy))),
            float(np.std(sx)), float(np.std(sy)),
        ], dtype=np.float32))
        if self.prev_gray is not None:
            diff = np.abs(gray - self.prev_gray)
            feats.append(np.array([float(np.mean(diff)), float(np.std(diff)), float(np.percentile(diff, 90))], dtype=np.float32))
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
        grid = []
        for r in range(0, CAPTURE_H, h4):
            for c in range(0, CAPTURE_W, w4):
                grid.append(float(gray[r:r + h4, c:c + w4].mean()))
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
        return vec

    def close(self) -> None:
        if self.sct is not None:
            try:
                self.sct.close()
            except Exception:
                pass
