from .config import (
    PHASE_DURATION_INCREMENT_AFTER_LEVELS,
    PHASE_DURATION_LEVELS,
    PLAYER_SPEED_PER_UPGRADE,
    SHORTER_TIMER_SCORE_FLOOR,
    SHORTER_TIMER_SCORE_MULTIPLIER,
    SHORTER_TIMER_SPEED_MULTIPLIER,
)


def upgrade_movement_speed(player):
    player.speed_multiplier *= PLAYER_SPEED_PER_UPGRADE


def upgrade_reduce_dash_cd(player):
    player.dash_cooldown = max(0.15, player.dash_cooldown * 0.6)


def upgrade_shield_charge(player):
    player.shield_enabled = True
    player.shield_max_charges = max(1, player.shield_max_charges + 1)
    player.shield_charges = min(player.shield_charges + 1, player.shield_max_charges)
    player.shield_recharge_time = max(4.0, player.shield_recharge_time * 0.9)


def upgrade_shorter_timer(player):
    player.time_scale = min(player.time_scale * SHORTER_TIMER_SPEED_MULTIPLIER, 2.0)
    player.score_multiplier = max(
        SHORTER_TIMER_SCORE_FLOOR,
        player.score_multiplier * SHORTER_TIMER_SCORE_MULTIPLIER,
    )


UPGRADE_POOL = [
    {
        "name": "+ Movement Speed",
        "description": "Increase movement speed permanently.",
        "apply": upgrade_movement_speed,
    },
    {
        "name": "- Dash Cooldown",
        "description": "Reduce dash cooldown so you can dash more often.",
        "apply": upgrade_reduce_dash_cd,
    },
    {
        "name": "Shield Charge",
        "description": "Gain +1 max shield charge and one immediate charge.",
        "apply": upgrade_shield_charge,
    },
    {
        "name": "Shorter Timer",
        "description": "Phases move faster with a much lighter score penalty.",
        "apply": upgrade_shorter_timer,
    },
]

ABILITIES = [
    {
        "name": "Slow-Motion (E)",
        "description": "Slow the whole game for 2 seconds.",
        "key": "slow",
    },
    {
        "name": "Teleport Tether (Right Click)",
        "description": "Hold right click to move, then release to snap back.",
        "key": "teleport",
    },
    {
        "name": "Energy Bubble (R)",
        "description": "Clear bullets around you in a short radius burst.",
        "key": "bubble",
    },
]


def get_phase_duration_for_round(round_index):
    if round_index <= 0:
        return PHASE_DURATION_LEVELS[0]
    if round_index <= len(PHASE_DURATION_LEVELS):
        return PHASE_DURATION_LEVELS[round_index - 1]
    extra = round_index - len(PHASE_DURATION_LEVELS)
    return PHASE_DURATION_LEVELS[-1] + PHASE_DURATION_INCREMENT_AFTER_LEVELS * extra
