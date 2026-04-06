import math
import random

import pygame

from .config import (
    ABILITY_COOLDOWN,
    ABILITY_DURATION_SLOW,
    BLINK_COOLDOWN,
    BLINK_IFRAME_DURATION,
    BULLET_SPEED,
    DASH_DURATION,
    DASH_SPEED,
    GRAVITY_PULL,
    HIT_GRACE_DURATION,
    INITIAL_DASH_COOLDOWN,
    MAX_BULLETS,
    MAX_SPAWN_CARRYOVER,
    MAX_WAVES_PER_FRAME,
    NEAR_MISS_MIN_AGE,
    PLAYER_SPEED_BASE,
    SAFE_ZONE_DURATION,
    SAFE_ZONE_RADIUS,
    SPAWN_RATE,
)
from .utils import clamp, clamp_to_arena, dist_sq_xy, vec_from_angle


class SafeZone:
    def __init__(self, pos, radius=SAFE_ZONE_RADIUS, duration=SAFE_ZONE_DURATION):
        self.pos = pygame.Vector2(pos)
        self.radius = radius
        self.time_left = duration

    def update(self, dt):
        self.time_left -= dt
        return self.time_left > 0.0

    def draw(self, surface):
        ratio = max(0.15, self.time_left / SAFE_ZONE_DURATION)
        color = (
            int(70 + (80 * ratio)),
            int(150 + (70 * ratio)),
            int(200 + (40 * ratio)),
        )
        pygame.draw.circle(
            surface,
            color,
            (int(self.pos.x), int(self.pos.y)),
            self.radius,
            width=3,
        )


class Player:
    def __init__(self, pos):
        self.pos = pygame.Vector2(pos)
        self.radius = 10
        self.color = (180, 220, 255)
        self.speed_base = PLAYER_SPEED_BASE
        self.speed_multiplier = 1.0
        self.score_multiplier = 1.0
        self.time_scale = 1.0
        self.last_input_dir = pygame.Vector2(0, -1)
        self.dash_cooldown = INITIAL_DASH_COOLDOWN
        self.dash_timer = 0.0
        self.is_dashing = False
        self.dash_time_left = 0.0
        self.dash_velocity = pygame.Vector2(0, 0)
        self.fall_vel = 0.0
        self.damage_grace_timer = 0.0
        self.shield_enabled = False
        self.shield_charges = 0
        self.shield_max_charges = 0
        self.shield_recharge_time = 12.0
        self.shield_recharge_timer = 0.0
        self.teleport_unlocked = False
        self.teleport_cooldown = BLINK_COOLDOWN
        self.teleport_timer = 0.0
        self.rounds_completed = 0
        self.hp = 1
        self.score = 0.0
        self.close_calls = 0
        self.special_ability = None
        self.ability_on_cooldown = 0.0
        self.slow_active_timer = 0.0
        self.ability_available_for_round = False
        self.invincible = False
        self.teleport_tether_active = False
        self.teleport_tether_origin = None

    @property
    def speed(self):
        return self.speed_base * self.speed_multiplier

    @property
    def collision_immune(self):
        return self.invincible or self.is_dashing or self.damage_grace_timer > 0.0

    def unlock_blink(self):
        if self.teleport_unlocked:
            return False
        self.teleport_unlocked = True
        self.teleport_timer = 0.0
        return True

    def update(self, dt, keys, phase, arena_size):
        arena_w, arena_h = arena_size
        if not self.teleport_tether_active:
            move = pygame.Vector2(0, 0)
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                move.y -= 1
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                move.y += 1
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                move.x -= 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                move.x += 1
            if move.length_squared() > 0:
                move = move.normalize()
                self.last_input_dir = move

            speed_mod = 1.0
            if phase == "gravity":
                speed_mod = 0.75
            elif phase == "hyper":
                speed_mod = 1.15

            self.pos += move * self.speed * speed_mod * dt

            if phase == "gravity":
                self.fall_vel = GRAVITY_PULL
            else:
                self.fall_vel = 0.0

            self.pos.y += self.fall_vel * dt

            if self.is_dashing and self.dash_velocity.length_squared() > 0:
                self.pos += self.dash_velocity * dt

        self.pos = clamp_to_arena(self.pos, 20, arena_w, arena_h)

        self.dash_timer = max(0.0, self.dash_timer - dt)
        self.damage_grace_timer = max(0.0, self.damage_grace_timer - dt)
        if self.is_dashing:
            self.dash_time_left -= dt
            if self.dash_time_left <= 0.0:
                self.is_dashing = False
                self.dash_velocity.update(0.0, 0.0)

        self.teleport_timer = max(0.0, self.teleport_timer - dt)

        if self.shield_enabled and self.shield_charges < self.shield_max_charges:
            self.shield_recharge_timer += dt
            if self.shield_recharge_timer >= self.shield_recharge_time:
                self.shield_recharge_timer -= self.shield_recharge_time
                self.shield_charges = min(self.shield_max_charges, self.shield_charges + 1)

        self.ability_on_cooldown = max(0.0, self.ability_on_cooldown - dt)
        self.slow_active_timer = max(0.0, self.slow_active_timer - dt)

    def try_dash(self):
        if self.dash_timer > 0.0:
            return False
        direction = self.last_input_dir if self.last_input_dir.length_squared() > 0 else pygame.Vector2(0, -1)
        self.dash_velocity = direction.normalize() * DASH_SPEED
        self.is_dashing = True
        self.dash_time_left = DASH_DURATION
        self.dash_timer = self.dash_cooldown
        self.damage_grace_timer = max(self.damage_grace_timer, DASH_DURATION)
        return True

    def try_blink(self, target_pos, arena_size):
        arena_w, arena_h = arena_size
        if not self.teleport_unlocked or self.teleport_timer > 0.0 or self.teleport_tether_active:
            return False
        self.pos = clamp_to_arena(target_pos, 20, arena_w, arena_h)
        self.teleport_timer = self.teleport_cooldown
        self.is_dashing = True
        self.dash_time_left = BLINK_IFRAME_DURATION
        self.dash_velocity.update(0.0, 0.0)
        self.damage_grace_timer = max(self.damage_grace_timer, BLINK_IFRAME_DURATION)
        return True

    def absorb_hit_with_shield(self):
        if not self.shield_enabled or self.shield_charges <= 0:
            return False
        self.shield_charges -= 1
        self.shield_recharge_timer = 0.0
        self.damage_grace_timer = HIT_GRACE_DURATION
        return True

    def can_use_ability(self):
        return (
            self.ability_available_for_round
            and self.special_ability is not None
            and self.ability_on_cooldown <= 0.0
        )

    def use_slow(self):
        if not self.can_use_ability() or self.special_ability != "slow":
            return False
        self.slow_active_timer = ABILITY_DURATION_SLOW
        self.ability_on_cooldown = ABILITY_COOLDOWN
        return True

    def use_bubble(self):
        if not self.can_use_ability() or self.special_ability != "bubble":
            return False
        self.ability_on_cooldown = ABILITY_COOLDOWN
        self.damage_grace_timer = max(self.damage_grace_timer, 0.08)
        return True

    def use_teleport_ability(self, start_tether):
        if not self.ability_available_for_round or self.special_ability != "teleport":
            return False
        if start_tether:
            if self.ability_on_cooldown > 0.0 or self.teleport_tether_active:
                return False
            self.teleport_tether_origin = pygame.Vector2(self.pos)
            self.teleport_tether_active = True
            self.damage_grace_timer = max(self.damage_grace_timer, 0.08)
            return True
        if not self.teleport_tether_active:
            return False
        if self.teleport_tether_origin is not None:
            self.pos = pygame.Vector2(self.teleport_tether_origin)
        self.teleport_tether_origin = None
        self.teleport_tether_active = False
        self.ability_on_cooldown = ABILITY_COOLDOWN
        self.damage_grace_timer = max(self.damage_grace_timer, 0.12)
        return True

    def draw(self, surface):
        pos = (int(self.pos.x), int(self.pos.y))
        if self.shield_enabled:
            ring_color = (120, 220, 255) if self.shield_charges > 0 else (60, 80, 100)
            pygame.draw.circle(surface, ring_color, pos, int(self.radius * 2.4), 3)
        if self.is_dashing or self.damage_grace_timer > 0.0:
            pygame.draw.circle(surface, (255, 255, 200), pos, int(self.radius * 1.9))
        pygame.draw.circle(surface, self.color, pos, self.radius)
        pygame.draw.circle(surface, (50, 60, 90), pos, int(self.radius * 0.45))


class Bullet:
    def __init__(self, pos, vel, color=(255, 100, 100), radius=4, pattern=None):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.radius = radius
        self.color = color
        self.pattern = pattern or {}
        self.age = 0.0
        self.close_call_registered = False
        self.teleport_warning_active = False
        interval = self.pattern.get("teleport_interval", (0.8, 2.0))
        self._teleport_cd = random.uniform(interval[0], interval[1])

    def update(self, dt, phase, arena_size, player=None):
        arena_w, arena_h = arena_size
        self.age += dt

        if self.pattern.get("homing") and player is not None:
            to_player = player.pos - self.pos
            if to_player.length_squared() > 0.01:
                desired = to_player.normalize() * max(self.vel.length(), 40.0)
                steer = (desired - self.vel) * self.pattern.get("homing_strength", 0.6) * dt
                self.vel += steer
                max_speed = self.pattern.get("max_speed", 300.0)
                if self.vel.length() > max_speed:
                    self.vel = self.vel.normalize() * max_speed

        if self.pattern.get("teleporting"):
            warning_time = self.pattern.get("teleport_warning", 0.22)
            self._teleport_cd -= dt
            self.teleport_warning_active = self._teleport_cd <= warning_time
            if self._teleport_cd <= 0.0:
                interval = self.pattern.get("teleport_interval", (0.9, 1.7))
                self._teleport_cd = random.uniform(interval[0], interval[1])
                jump = self.pattern.get("teleport_distance", 70.0)
                self.pos.x = clamp(self.pos.x + random.uniform(-jump, jump), self.radius, arena_w - self.radius)
                self.pos.y = clamp(self.pos.y + random.uniform(-jump, jump), self.radius, arena_h - self.radius)
                self.teleport_warning_active = False

        if self.pattern.get("curving"):
            angle = math.atan2(self.vel.y, self.vel.x)
            angle += self.pattern.get("curve_strength", 0.0) * dt
            speed = self.vel.length()
            self.vel = vec_from_angle(angle) * speed

        if phase == "gravity" and self.pattern.get("affected_by_gravity", False):
            self.vel.y += 200.0 * dt

        if self.pattern.get("bounce"):
            next_pos = self.pos + (self.vel * dt)
            bounced = False
            if next_pos.x < self.radius:
                self.vel.x = abs(self.vel.x)
                bounced = True
            if next_pos.x > arena_w - self.radius:
                self.vel.x = -abs(self.vel.x)
                bounced = True
            if next_pos.y < self.radius:
                self.vel.y = abs(self.vel.y)
                bounced = True
            if next_pos.y > arena_h - self.radius:
                self.vel.y = -abs(self.vel.y)
                bounced = True
            if bounced:
                next_pos = self.pos + (self.vel * dt)
            self.pos = next_pos
        else:
            self.pos += self.vel * dt

    def draw(self, surface, pos_override=None, ghost=False):
        px, py = pos_override if pos_override is not None else self.pos
        pos = (int(px), int(py))
        if ghost:
            pygame.draw.circle(surface, (70, 110, 145), pos, self.radius)
            pygame.draw.circle(surface, (215, 225, 255), pos, self.radius + 1, 1)
        else:
            pygame.draw.circle(surface, self.color, pos, self.radius)
        if self.pattern.get("teleporting") and self.teleport_warning_active:
            pygame.draw.circle(surface, (255, 245, 180), pos, self.radius + 5, 1)

    def offscreen(self, arena_size):
        arena_w, arena_h = arena_size
        return (
            self.pos.x < -80
            or self.pos.x > arena_w + 80
            or self.pos.y < -80
            or self.pos.y > arena_h + 80
        )


class Spawner:
    def __init__(self):
        self.time_acc = 0.0
        self.spawn_rate = SPAWN_RATE

    def update(self, dt, bullets, phase, phase_elapsed, phase_duration, round_index, player, arena_size):
        progress = clamp(phase_elapsed / max(phase_duration, 1.0), 0.0, 1.0)
        round_scale = 1.0 + (0.12 * max(0, round_index - 1))
        phase_scale = 1.0 + (0.55 * progress) + (0.25 * progress * progress)
        rate = self.spawn_rate * round_scale * phase_scale
        if phase == "gravity":
            rate *= 1.05
        elif phase == "hyper":
            rate *= 1.28
        elif phase == "mirror":
            rate *= 0.68

        interval = 1.0 / max(rate, 0.05)
        self.time_acc += dt
        self.time_acc = min(self.time_acc, interval * MAX_SPAWN_CARRYOVER)

        spawned_waves = 0
        while (
            self.time_acc >= interval
            and spawned_waves < MAX_WAVES_PER_FRAME
            and len(bullets) < MAX_BULLETS
        ):
            self.time_acc -= interval
            self.spawn_wave(
                bullets,
                phase,
                round_index,
                player,
                arena_size,
                bullet_cap=MAX_BULLETS - len(bullets),
            )
            spawned_waves += 1

        if len(bullets) >= MAX_BULLETS:
            self.time_acc = 0.0

    def spawn_wave(self, bullets, phase, round_index, player, arena_size, bullet_cap):
        arena_w, arena_h = arena_size
        remaining_cap = bullet_cap
        t = random.random()
        prog = round_index

        def add_bullet(bullet):
            nonlocal remaining_cap
            if remaining_cap <= 0:
                return False
            bullets.append(bullet)
            remaining_cap -= 1
            return True

        if prog >= 4 and t < 0.18:
            side = random.choice(["top", "bottom", "left", "right"])
            if side == "top":
                origin = pygame.Vector2(random.uniform(60, arena_w - 60), -12)
                base_dir = pygame.Vector2(0, 1)
            elif side == "bottom":
                origin = pygame.Vector2(random.uniform(60, arena_w - 60), arena_h + 12)
                base_dir = pygame.Vector2(0, -1)
            elif side == "left":
                origin = pygame.Vector2(-12, random.uniform(60, arena_h - 60))
                base_dir = pygame.Vector2(1, 0)
            else:
                origin = pygame.Vector2(arena_w + 12, random.uniform(60, arena_h - 60))
                base_dir = pygame.Vector2(-1, 0)

            count = min(6 + prog, 10)
            for _ in range(count):
                spread = pygame.Vector2(random.uniform(-0.25, 0.25), random.uniform(-0.25, 0.25))
                direction = (base_dir + spread).normalize()
                speed = BULLET_SPEED * random.uniform(0.9, 1.2)
                bullet = Bullet(
                    origin,
                    direction * speed,
                    color=(120, 220, 255),
                    radius=4,
                    pattern={
                        "teleporting": True,
                        "teleport_interval": (1.0, 1.7),
                        "teleport_distance": 64.0,
                        "teleport_warning": 0.24,
                    },
                )
                if phase == "hyper":
                    bullet.pattern["bounce"] = True
                    bullet.pattern["lifetime"] = random.uniform(2.6, 4.4)
                if not add_bullet(bullet):
                    break
            return

        if prog >= 3 and t < 0.12:
            cx, cy = arena_w / 2.0, arena_h / 2.0
            count = 10 + min(12, prog * 3)
            for i in range(count):
                angle = (2.0 * math.pi) * (i / count) + random.uniform(-0.08, 0.08)
                direction = vec_from_angle(angle)
                speed = BULLET_SPEED * random.uniform(0.6, 1.5) * (1.0 + 0.05 * (prog - 1))
                bullet = Bullet((cx, cy), direction * speed, color=(100, 255, 180))
                if random.random() < 0.35:
                    bullet.pattern["homing"] = True
                    bullet.pattern["homing_strength"] = random.uniform(0.6, 1.6)
                    bullet.pattern["max_speed"] = speed * 1.3
                if phase == "hyper":
                    bullet.pattern["lifetime"] = random.uniform(3.0, 6.0)
                    bullet.pattern["bounce"] = True
                if not add_bullet(bullet):
                    break
            return

        if prog >= 2 and t < 0.30:
            side = random.choice(["left", "right", "top", "bottom"])
            if side == "left":
                origin = pygame.Vector2(-20, random.uniform(80, arena_h - 80))
            elif side == "right":
                origin = pygame.Vector2(arena_w + 20, random.uniform(80, arena_h - 80))
            elif side == "top":
                origin = pygame.Vector2(random.uniform(80, arena_w - 80), -20)
            else:
                origin = pygame.Vector2(random.uniform(80, arena_w - 80), arena_h + 20)

            if player is not None:
                to_player = player.pos - origin
                base_angle = math.atan2(to_player.y, to_player.x)
            else:
                base_angle = 0.0

            pellets = 6 + min(10, prog * 2)
            spread = 0.55 + (0.03 * prog)
            for _ in range(pellets):
                angle = base_angle + random.uniform(-spread, spread)
                direction = vec_from_angle(angle)
                speed = BULLET_SPEED * random.uniform(0.9, 1.2) * (1.0 + 0.04 * (prog - 1))
                bullet = Bullet(
                    origin + pygame.Vector2(random.uniform(-6, 6), random.uniform(-6, 6)),
                    direction * speed,
                    color=(200, 160, 255),
                    radius=3,
                )
                if random.random() < 0.28:
                    bullet.pattern["curving"] = True
                    bullet.pattern["curve_strength"] = random.uniform(-1.2, 0.9)
                if phase == "hyper":
                    bullet.pattern["lifetime"] = random.uniform(2.5, 5.0)
                    bullet.pattern["bounce"] = True
                if not add_bullet(bullet):
                    break
            return

        if prog >= 3 and t < 0.44:
            side = random.choice(["top", "bottom", "left", "right"])
            if side == "top":
                x = random.uniform(50, arena_w - 50)
                y = -10
                direction = pygame.Vector2(random.uniform(-0.12, 0.12), 1.0).normalize()
            elif side == "bottom":
                x = random.uniform(50, arena_w - 50)
                y = arena_h + 10
                direction = pygame.Vector2(random.uniform(-0.12, 0.12), -1.0).normalize()
            elif side == "left":
                x = -10
                y = random.uniform(50, arena_h - 50)
                direction = pygame.Vector2(1.0, random.uniform(-0.12, 0.12)).normalize()
            else:
                x = arena_w + 10
                y = random.uniform(50, arena_h - 50)
                direction = pygame.Vector2(-1.0, random.uniform(-0.12, 0.12)).normalize()
            speed = BULLET_SPEED * random.uniform(1.6, 2.2)
            bullet = Bullet((x, y), direction * speed, color=(255, 60, 60), radius=3)
            if phase == "hyper":
                bullet.pattern["lifetime"] = random.uniform(1.8, 3.4)
                bullet.pattern["bounce"] = True
            add_bullet(bullet)
            return

        if t < 0.5:
            side = random.choice(["top", "bottom", "left", "right"])
            if side == "top":
                x = random.uniform(50, arena_w - 50)
                y = -10
                direction = pygame.Vector2(random.uniform(-0.3, 0.3), 1.0).normalize()
            elif side == "bottom":
                x = random.uniform(50, arena_w - 50)
                y = arena_h + 10
                direction = pygame.Vector2(random.uniform(-0.3, 0.3), -1.0).normalize()
            elif side == "left":
                x = -10
                y = random.uniform(50, arena_h - 50)
                direction = pygame.Vector2(1.0, random.uniform(-0.3, 0.3)).normalize()
            else:
                x = arena_w + 10
                y = random.uniform(50, arena_h - 50)
                direction = pygame.Vector2(-1.0, random.uniform(-0.3, 0.3)).normalize()
            speed = random.uniform(BULLET_SPEED * 0.8, BULLET_SPEED * 1.1) * (1.0 + 0.05 * (prog - 1))
            bullet = Bullet((x, y), direction * speed, color=(255, 90, 80))
            if phase == "gravity" and random.random() < 0.35:
                bullet.pattern["affected_by_gravity"] = True
            if phase == "hyper":
                bullet.pattern["lifetime"] = random.uniform(2.5, 5.5)
                bullet.pattern["bounce"] = True
            add_bullet(bullet)
            return

        cx, cy = arena_w / 2.0, arena_h / 2.0
        for _ in range(6):
            angle = random.uniform(0.0, math.pi * 2.0)
            direction = vec_from_angle(angle)
            speed = BULLET_SPEED * random.uniform(0.6, 1.4)
            bullet = Bullet((cx, cy), direction * speed, color=(100, 255, 180))
            if phase == "hyper":
                bullet.pattern["lifetime"] = random.uniform(3.0, 6.0)
                bullet.pattern["bounce"] = True
            if not add_bullet(bullet):
                break


def filter_bullets_outside_radius(bullets, origin, radius):
    radius_sq = radius * radius
    ox, oy = origin
    kept = []
    for bullet in bullets:
        if dist_sq_xy(bullet.pos.x, bullet.pos.y, ox, oy) > radius_sq:
            kept.append(bullet)
    return kept


def bullet_in_safe_zone(bullet, safe_zone_data):
    for sx, sy, radius_sq in safe_zone_data:
        if dist_sq_xy(bullet.pos.x, bullet.pos.y, sx, sy) <= radius_sq:
            return True
    return False


def bullet_can_register_close_call(bullet):
    return bullet.age >= NEAR_MISS_MIN_AGE and not bullet.close_call_registered
