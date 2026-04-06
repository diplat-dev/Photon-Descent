import os

import pygame

from .config import (
    ASSET_DIR,
    FADE_DURATION,
    MIXER_BUFFER,
    MIXER_CHANNELS,
    MIXER_FREQ,
    MIXER_SIZE,
    PHASE_MUSIC_FILES,
)
from .utils import clamp


class MusicManager:
    def __init__(self, fade_duration=FADE_DURATION):
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(
                    frequency=MIXER_FREQ,
                    size=MIXER_SIZE,
                    channels=MIXER_CHANNELS,
                    buffer=MIXER_BUFFER,
                )
            self.available = True
        except Exception as exc:
            print("Warning: mixer init failed:", exc)
            self.available = False
            return

        self.fade_duration = fade_duration
        self.current_phase = None
        self.pending_phase = None
        self.transition_timer = 0.0
        self.master_volume = 0.85

    def _resolve_asset_path(self, phase):
        filename = PHASE_MUSIC_FILES.get(phase)
        if not filename:
            return None
        full_path = os.path.join(ASSET_DIR, filename)
        if not os.path.isfile(full_path):
            print(f"Warning: music file for phase '{phase}' not found at '{full_path}'")
            return None
        return full_path

    def _start_phase(self, phase, fade_in=True):
        path = self._resolve_asset_path(phase)
        if path is None:
            self.stop_all()
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.master_volume)
            pygame.mixer.music.play(
                loops=-1,
                fade_ms=int(self.fade_duration * 1000) if fade_in else 0,
            )
            self.current_phase = phase
        except Exception as exc:
            print("Warning: could not play music:", exc)

    def set_master_volume(self, volume):
        self.master_volume = clamp(volume, 0.0, 1.0)
        if not self.available:
            return
        try:
            pygame.mixer.music.set_volume(self.master_volume)
        except Exception:
            pass

    def set_phase(self, phase):
        if not self.available:
            return
        if phase == self.current_phase and self.pending_phase is None:
            return
        if phase == self.pending_phase:
            return

        path = self._resolve_asset_path(phase)
        if path is None:
            self.stop_all()
            return

        if self.current_phase is None or not pygame.mixer.music.get_busy():
            self.pending_phase = None
            self.transition_timer = 0.0
            self._start_phase(phase, fade_in=True)
            return

        self.pending_phase = phase
        self.transition_timer = self.fade_duration
        try:
            pygame.mixer.music.fadeout(int(self.fade_duration * 1000))
        except Exception:
            self.transition_timer = 0.0

    def update(self, dt):
        if not self.available or self.pending_phase is None:
            return
        self.transition_timer -= dt
        if self.transition_timer > 0.0:
            return
        next_phase = self.pending_phase
        self.pending_phase = None
        self._start_phase(next_phase, fade_in=True)

    def stop_all(self):
        if not self.available:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.current_phase = None
        self.pending_phase = None
        self.transition_timer = 0.0

