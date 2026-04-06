import math

import pygame


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def vec_from_angle(angle_radians):
    return pygame.Vector2(math.cos(angle_radians), math.sin(angle_radians))


def dist_sq_xy(ax, ay, bx, by):
    dx = ax - bx
    dy = ay - by
    return (dx * dx) + (dy * dy)


def within_radius_sq(ax, ay, bx, by, radius):
    return dist_sq_xy(ax, ay, bx, by) <= (radius * radius)


def clamp_to_arena(pos, margin, arena_w, arena_h):
    return pygame.Vector2(
        clamp(pos[0], margin, arena_w - margin),
        clamp(pos[1], margin, arena_h - margin),
    )
