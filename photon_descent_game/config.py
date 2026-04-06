import os
import sys

SCREEN_W, SCREEN_H = 800, 600
FPS = 60
SCREEN_CENTER = (SCREEN_W / 2.0, SCREEN_H / 2.0)
WINDOW_MIN_W, WINDOW_MIN_H = 640, 480

PHASE_DURATION_LEVELS = [30.0, 40.0, 60.0, 90.0]
PHASE_DURATION_INCREMENT_AFTER_LEVELS = 30.0

PLAYER_SPEED_BASE = 160
PLAYER_SPEED_PER_UPGRADE = 1.18

INITIAL_DASH_COOLDOWN = 1.2
DASH_DURATION = 0.12
DASH_SPEED = 520
HIT_GRACE_DURATION = 0.18

BLINK_UNLOCK_ROUND = 2
BLINK_COOLDOWN = 9.0
BLINK_IFRAME_DURATION = 0.16

BULLET_SPEED = 180
SPAWN_RATE = 1.0
MAX_BULLETS = 260
MAX_WAVES_PER_FRAME = 3
# Measured in spawn intervals, not raw seconds. This lets early rounds
# still accumulate enough time to emit a wave while preventing huge catch-up dumps.
MAX_SPAWN_CARRYOVER = 2.5

MIXER_FREQ = 44100
MIXER_SIZE = -16
MIXER_CHANNELS = 2
MIXER_BUFFER = 512
FADE_DURATION = 1.0

PHASE_MUSIC_FILES = {
    "title": "title_ambient.mp3",
    "light": "light_phase.mp3",
    "gravity": "gravity_phase.mp3",
    "hyper": "hyper_phase.mp3",
    "mirror": "mirror_phase.mp3",
}

SAFE_ZONE_CHANCE_PER_SECOND = 0.015
SAFE_ZONE_DURATION = 3.0
SAFE_ZONE_RADIUS = 90

ABILITY_DURATION_SLOW = 2.0
ABILITY_SLOW_MULTIPLIER = 0.4
ABILITY_COOLDOWN = 12.0
BUBBLE_RADIUS = 110

GRAVITY_PULL = 60.0

MIRROR_SPIN_BASE_DEG = 30.0
MIRROR_SPIN_PER_ROUND = 4.0

NEAR_MISS_BUFFER = 18
NEAR_MISS_MIN_AGE = 0.2

SHORTER_TIMER_SPEED_MULTIPLIER = 1.12
SHORTER_TIMER_SCORE_MULTIPLIER = 0.92
SHORTER_TIMER_SCORE_FLOOR = 0.72

NOTIFICATION_DURATION = 3.0
TITLE_VERSION = "v0.4 prototype"

PHASES = ["light", "gravity", "hyper", "mirror"]

COLOR_SWATCHES = [
    (180, 220, 255),
    (80, 255, 255),
    (200, 80, 255),
    (255, 120, 80),
    (120, 255, 120),
]

if getattr(sys, "frozen", False):
    ASSET_DIR = sys._MEIPASS
else:
    PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
    ASSET_DIR = os.path.dirname(PACKAGE_DIR)

LOCAL_APPDATA = os.environ.get("LOCALAPPDATA")
if LOCAL_APPDATA:
    SAVE_DIR = os.path.join(LOCAL_APPDATA, "PhotonDescent")
else:
    SAVE_DIR = os.path.join(os.path.expanduser("~"), ".photon_descent")
SAVE_PATH = os.path.join(SAVE_DIR, "save_data.json")
