"""Screen capture + lightweight visual feature encoder for the fly brain."""

from __future__ import annotations

import numpy as np
import cv2
from typing import Optional, Tuple

try:
    import mss
except ImportError:
    mss = None

from .config import CAPTURE_W, CAPTURE_H, N_SENSORY


class VisionEncoder:
    """Captures a monitor region and produces a fixed-size sensory vector."""

    def __init__(self, monitor_index: int = 1) -> None:
        self.monitor_index = monitor_index
        self.sct = mss.mss() if mss is not None else None
        self.last_frame: Optional[np.ndarray] = None
        self.last_gray: Optional[np.ndarray] = None
        self.prev_gray: Optional[np.ndarray] = None

    def capture(self, region: Optional[dict] = None) -> np.ndarray:
        """
        Return BGR uint8 frame of shape (CAPTURE_H, CAPTURE_W, 3).
        If region is None, uses primary monitor.
        """
        if self.sct is None:
            # offline fallback: noise
            frame = np.random.randint(0, 40, (CAPTURE_H, CAPTURE_W, 3), dtype=np.uint8)
            self.last_frame = frame
            return frame

        if region is None:
            mon = self.sct.monitors[self.monitor_index]
            region = {
                "left": mon["left"],
                "top": mon["top"],
                "width": mon["width"],
                "height": mon["height"],
            }

        shot = self.sct.grab(region)
        frame = np.array(shot)[:, :, :3]  # BGRA → BGR
        frame = cv2.resize(frame, (CAPTURE_W, CAPTURE_H), interpolation=cv2.INTER_AREA)
        self.last_frame = frame
        return frame

    def encode(self, frame: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Map frame → (N_SENSORY,) float32 in [0, 1].

        Features:
        - luminance histogram (16 bins)
        - horizontal / vertical edge energy (Sobel)
        - optical-flow magnitude proxy (frame difference)
        - centre-of-mass of bright regions
        - simple colour channel means
        """
        if frame is None:
            frame = self.last_frame
        if frame is None:
            return np.zeros(N_SENSORY, dtype=np.float32)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        self.prev_gray = self.last_gray
        self.last_gray = gray

        feats = []

        # 1. luminance histogram
        hist = np.histogram(gray, bins=16, range=(0.0, 1.0))[0].astype(np.float32)
        hist /= hist.sum() + 1e-6
        feats.append(hist)

        # 2. edge energy
        sx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        edge_h = float(np.mean(np.abs(sx)))
        edge_v = float(np.mean(np.abs(sy)))
        feats.append(np.array([edge_h, edge_v], dtype=np.float32))

        # 3. motion proxy
        if self.prev_gray is not None:
            diff = np.abs(gray - self.prev_gray)
            motion = float(np.mean(diff))
            motion_std = float(np.std(diff))
        else:
            motion = 0.0
            motion_std = 0.0
        feats.append(np.array([motion, motion_std], dtype=np.float32))

        # 4. bright centre of mass
        bright = (gray > 0.7).astype(np.float32)
        if bright.sum() > 10:
            ys, xs = np.where(bright > 0)
            cx = float(xs.mean()) / CAPTURE_W
            cy = float(ys.mean()) / CAPTURE_H
        else:
            cx, cy = 0.5, 0.5
        feats.append(np.array([cx, cy], dtype=np.float32))

        # 5. colour means (BGR)
        means = frame.mean(axis=(0, 1)).astype(np.float32) / 255.0
        feats.append(means)

        # 6. quadrant brightness
        h2, w2 = CAPTURE_H // 2, CAPTURE_W // 2
        q = [
            gray[:h2, :w2].mean(),
            gray[:h2, w2:].mean(),
            gray[h2:, :w2].mean(),
            gray[h2:, w2:].mean(),
        ]
        feats.append(np.array(q, dtype=np.float32))

        # 7. fill remaining slots with spatial patches (downsample)
        small = cv2.resize(gray, (8, 4), interpolation=cv2.INTER_AREA).ravel()
        feats.append(small)

        vec = np.concatenate(feats).astype(np.float32)
        if vec.size < N_SENSORY:
            vec = np.pad(vec, (0, N_SENSORY - vec.size))
        else:
            vec = vec[:N_SENSORY]
        # clip
        np.clip(vec, 0.0, 1.0, out=vec)
        return vec

    def close(self) -> None:
        if self.sct is not None:
            self.sct.close()
