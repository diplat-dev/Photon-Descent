import json
import os

from .config import COLOR_SWATCHES, SAVE_PATH
from .utils import clamp

DEFAULT_SAVE_DATA = {
    "high_score": 0,
    "volume": 0.85,
    "color_idx": 0,
}


class SaveStore:
    def __init__(self, path=SAVE_PATH):
        self.path = path
        self.data = dict(DEFAULT_SAVE_DATA)
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                merged = dict(DEFAULT_SAVE_DATA)
                merged.update(loaded)
                self.data = merged
        except FileNotFoundError:
            self.data = dict(DEFAULT_SAVE_DATA)
        except Exception:
            self.data = dict(DEFAULT_SAVE_DATA)

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2)

    @property
    def high_score(self):
        return int(max(0, int(self.data.get("high_score", 0))))

    @property
    def volume(self):
        return clamp(float(self.data.get("volume", 0.85)), 0.0, 1.0)

    @property
    def color_idx(self):
        raw = int(self.data.get("color_idx", 0))
        return max(0, min(len(COLOR_SWATCHES) - 1, raw))

    def set_volume(self, volume):
        volume = clamp(float(volume), 0.0, 1.0)
        if abs(volume - self.volume) < 0.001:
            return
        self.data["volume"] = volume
        self.save()

    def set_color_idx(self, color_idx):
        color_idx = max(0, min(len(COLOR_SWATCHES) - 1, int(color_idx)))
        if color_idx == self.color_idx:
            return
        self.data["color_idx"] = color_idx
        self.save()

    def update_high_score(self, score):
        score = max(0, int(score))
        if score <= self.high_score:
            return False
        self.data["high_score"] = score
        self.save()
        return True

