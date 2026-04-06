from dataclasses import dataclass
from functools import lru_cache

import pygame

from .config import COLOR_SWATCHES, SAFE_ZONE_RADIUS


@dataclass(frozen=True)
class Fonts:
    tiny: pygame.font.Font
    small: pygame.font.Font
    medium: pygame.font.Font
    large: pygame.font.Font
    title: pygame.font.Font


def create_fonts():
    return Fonts(
        tiny=pygame.font.SysFont(None, 18),
        small=pygame.font.SysFont(None, 20),
        medium=pygame.font.SysFont(None, 26),
        large=pygame.font.SysFont(None, 46),
        title=pygame.font.SysFont(None, 68),
    )


def build_ui_assets(fonts):
    title_text = fonts.title.render("PHOTON DESCENT", True, (180, 240, 255))
    title_glow_layers = []
    for index, alpha in enumerate((40, 24, 12)):
        layer = pygame.Surface((title_text.get_width() + 24, title_text.get_height() + 24), pygame.SRCALPHA)
        pygame.draw.rect(layer, (80, 200, 230, alpha), layer.get_rect(), border_radius=8)
        title_glow_layers.append((layer, index))

    slow_label = fonts.tiny.render("SLOW-MOTION ACTIVE", True, (240, 220, 80))
    teleport_marker = pygame.Surface((48, 48), pygame.SRCALPHA)
    pygame.draw.circle(teleport_marker, (120, 120, 120, 160), (24, 24), 18)

    return {
        "title_text": title_text,
        "title_glow_layers": title_glow_layers,
        "slow_label": slow_label,
        "teleport_marker": teleport_marker,
    }


@lru_cache(maxsize=64)
def _button_glow_surface(width, height, color, alpha):
    surface = pygame.Surface((width + 18, height + 18), pygame.SRCALPHA)
    pygame.draw.rect(surface, (*color, alpha), surface.get_rect(), border_radius=14)
    return surface


def draw_button(surface, rect, text, font, base_color, hover=False, glow=True):
    if glow:
        alpha = 140 if hover else 60
        glow_surface = _button_glow_surface(rect.width, rect.height, base_color, alpha)
        surface.blit(glow_surface, (rect.x - 9, rect.y - 9))
    pygame.draw.rect(surface, base_color, rect, border_radius=12)
    pygame.draw.rect(surface, (220, 220, 220), rect, 2, border_radius=12)
    rendered = font.render(text, True, (10, 10, 18))
    surface.blit(rendered, (rect.centerx - (rendered.get_width() / 2), rect.centery - (rendered.get_height() / 2)))


def wrap_text(font, text, max_width):
    words = text.split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def get_title_layout(surface):
    screen_w = surface.get_width()
    screen_h = surface.get_height()
    button_width = min(280, max(220, screen_w // 3))
    button_height = 72
    start_rect = pygame.Rect(
        screen_w // 2 - button_width // 2,
        int(screen_h * 0.7),
        button_width,
        button_height,
    )
    slider_width = min(320, max(220, screen_w // 3))
    slider_rect = pygame.Rect(screen_w // 2 - slider_width // 2, int(screen_h * 0.58), slider_width, 16)
    swatch_start = screen_w // 2 - (len(COLOR_SWATCHES) * 42) // 2
    swatch_rects = [
        pygame.Rect(swatch_start + (index * 42), int(screen_h * 0.44), 36, 36)
        for index in range(len(COLOR_SWATCHES))
    ]
    return {
        "start_rect": start_rect,
        "slider_rect": slider_rect,
        "swatch_rects": swatch_rects,
    }


def draw_title_screen(screen, fonts, ui_assets, selected_color_idx, volume, high_score, mouse_pos):
    screen_w = screen.get_width()
    screen_h = screen.get_height()
    layout = get_title_layout(screen)
    screen.fill((6, 6, 12))

    for layer, offset in ui_assets["title_glow_layers"]:
        screen.blit(
            layer,
            (
                screen_w // 2 - ui_assets["title_text"].get_width() / 2 - 12 - offset,
                max(24, int(screen_h * 0.12)) - offset,
            ),
        )
    screen.blit(ui_assets["title_text"], (screen_w // 2 - ui_assets["title_text"].get_width() / 2, max(32, int(screen_h * 0.12) + 8)))

    hover = layout["start_rect"].collidepoint(mouse_pos)
    button_color = (100, 230, 255) if hover else (70, 200, 230)
    draw_button(screen, layout["start_rect"], "START RUN", fonts.large, button_color, hover=hover)

    color_label = fonts.medium.render("Color", True, (220, 230, 238))
    screen.blit(color_label, (screen_w // 2 - color_label.get_width() / 2, layout["swatch_rects"][0].y - 34))

    for index, color in enumerate(COLOR_SWATCHES):
        rect = layout["swatch_rects"][index]
        pygame.draw.rect(screen, color, rect, border_radius=6)
        pygame.draw.rect(screen, (220, 220, 220), rect, 2, border_radius=6)
        if index == selected_color_idx:
            pygame.draw.rect(screen, (255, 255, 255), rect.inflate(8, 8), 3, border_radius=10)

    slider_rect = layout["slider_rect"]
    pygame.draw.rect(screen, (36, 36, 42), slider_rect, border_radius=6)
    pygame.draw.rect(screen, (120, 120, 130), slider_rect, 2, border_radius=6)
    handle_x = slider_rect.x + int(volume * slider_rect.width)
    fill_rect = pygame.Rect(slider_rect.x, slider_rect.y, handle_x - slider_rect.x, slider_rect.height)
    pygame.draw.rect(screen, (70, 200, 230), fill_rect, border_radius=6)
    pygame.draw.circle(screen, (200, 200, 200), (handle_x, slider_rect.y + slider_rect.height // 2), 8)
    volume_text = fonts.medium.render(f"Volume {int(volume * 100)}%", True, (220, 230, 238))
    screen.blit(volume_text, (screen_w // 2 - volume_text.get_width() / 2, slider_rect.y - 34))

    return layout


def get_choice_card_rects(surface, option_count):
    screen_w = surface.get_width()
    card_width = (screen_w // option_count) - 48
    return [
        pygame.Rect((index * (screen_w // option_count)) + 24, 140, card_width, 250)
        for index in range(option_count)
    ]


def draw_choice_screen(screen, fonts, title, subtitle, options, hovered_idx, footer):
    screen_w = screen.get_width()
    screen_h = screen.get_height()
    screen.fill((16, 16, 26))
    title_text = fonts.large.render(title, True, (230, 230, 230))
    screen.blit(title_text, (screen_w / 2 - title_text.get_width() / 2, 34))
    subtitle_text = fonts.medium.render(subtitle, True, (200, 200, 200))
    screen.blit(subtitle_text, (screen_w / 2 - subtitle_text.get_width() / 2, 88))

    card_rects = get_choice_card_rects(screen, len(options))
    for index, option in enumerate(options):
        rect = card_rects[index]
        fill = (40, 40, 58) if hovered_idx == index else (28, 28, 40)
        border = (110, 210, 240) if hovered_idx == index else (70, 70, 100)
        pygame.draw.rect(screen, fill, rect, border_radius=10)
        pygame.draw.rect(screen, border, rect, 2, border_radius=10)
        name_text = fonts.medium.render(option["name"], True, (235, 235, 240))
        screen.blit(name_text, (rect.x + 18, rect.y + 18))

        y = rect.y + 56
        for line in wrap_text(fonts.small, option["description"], rect.width - 32):
            detail_text = fonts.small.render(line, True, (190, 195, 210))
            screen.blit(detail_text, (rect.x + 18, y))
            y += 22

        hotkey_text = fonts.small.render(f"Press {index + 1} or click", True, (150, 170, 180))
        screen.blit(hotkey_text, (rect.x + 18, rect.bottom - 34))

    footer_text = fonts.small.render(footer, True, (160, 160, 160))
    screen.blit(footer_text, (screen_w / 2 - footer_text.get_width() / 2, screen_h - 54))
    return card_rects


def draw_phase_background(screen, phase_name):
    screen_w = screen.get_width()
    screen_h = screen.get_height()
    screen.fill((8, 8, 14))
    if phase_name == "gravity":
        for x in range(0, screen_w, 64):
            pygame.draw.line(screen, (18, 24, 38), (x, 0), (x - 28, screen_h), 1)
    elif phase_name == "hyper":
        for y in range(90, screen_h, 48):
            pygame.draw.line(screen, (26, 14, 20), (0, y), (screen_w, y + 18), 1)
    elif phase_name == "mirror":
        half_width = screen_w // 2
        pygame.draw.rect(screen, (12, 12, 22), (0, 0, half_width, screen_h))
        pygame.draw.rect(screen, (18, 18, 30), (half_width, 0, half_width, screen_h))
        pygame.draw.line(screen, (150, 160, 190), (half_width, 0), (half_width, screen_h), 2)


def draw_notifications(screen, fonts, notifications):
    screen_w = screen.get_width()
    y = 78
    for item in notifications:
        text = fonts.small.render(item["text"], True, item["color"])
        screen.blit(text, (screen_w / 2 - text.get_width() / 2, y))
        y += 24


def draw_hud(screen, fonts, player, round_index, phase_name, phase_elapsed, phase_duration, high_score):
    screen_w = screen.get_width()
    screen_h = screen.get_height()
    pygame.draw.rect(screen, (18, 18, 26), (0, 0, screen_w, 72))
    header = fonts.large.render(f"Round {round_index}  Phase: {phase_name.upper()}", True, (220, 220, 220))
    screen.blit(header, (18, 6))

    phase_info = fonts.small.render(
        f"Phase Time: {int(phase_elapsed)} / {int(phase_duration)} s  (time scale x{player.time_scale:.2f})",
        True,
        (200, 200, 200),
    )
    screen.blit(phase_info, (18, 44))

    score_text = fonts.small.render(f"Score: {int(player.score)}  High: {int(high_score)}", True, (200, 200, 200))
    screen.blit(score_text, (screen_w - 260, 20))

    rounds_text = fonts.small.render(f"Rounds Completed: {player.rounds_completed}", True, (200, 200, 200))
    screen.blit(rounds_text, (screen_w - 260, 44))

    hud_x = 18
    hud_y = screen_h - 64
    if player.shield_enabled:
        shield_text = fonts.small.render(
            f"Shield: {player.shield_charges}/{player.shield_max_charges}",
            True,
            (180, 220, 240),
        )
        screen.blit(shield_text, (hud_x, hud_y))
        hud_x += 180

    dash_text = fonts.small.render(f"Dash CD: {player.dash_timer:.2f}s", True, (220, 200, 220))
    screen.blit(dash_text, (hud_x, hud_y))
    hud_x += 140

    if player.teleport_unlocked:
        blink_text = fonts.small.render(f"Blink CD: {player.teleport_timer:.2f}s", True, (170, 220, 255))
    else:
        blink_text = fonts.small.render("Blink unlocks after Round 1", True, (170, 220, 255))
    screen.blit(blink_text, (hud_x, hud_y))

    ability_name = player.special_ability if player.special_ability else "None"
    ability_text = fonts.small.render(
        f"Ability: {ability_name}  CD: {player.ability_on_cooldown:.1f}s",
        True,
        (200, 200, 200),
    )
    screen.blit(ability_text, (18, screen_h - 36))

    style_text = fonts.small.render(f"Close Calls: {player.close_calls}", True, (240, 220, 140))
    screen.blit(style_text, (screen_w - style_text.get_width() - 18, screen_h - 36))


def draw_game_over_screen(screen, fonts, score, high_score, close_calls):
    screen_w = screen.get_width()
    screen_h = screen.get_height()
    screen.fill((6, 6, 12))
    title = fonts.large.render("Run Over", True, (240, 200, 200))
    score_text = fonts.small.render(f"Score: {int(score)}  High: {int(high_score)}", True, (220, 220, 220))
    style_text = fonts.small.render(f"Close Calls: {close_calls}", True, (240, 220, 140))
    footer = fonts.small.render("Press R to restart, or Esc to quit.", True, (180, 180, 180))
    screen.blit(title, (screen_w / 2 - title.get_width() / 2, screen_h / 2 - 74))
    screen.blit(score_text, (screen_w / 2 - score_text.get_width() / 2, screen_h / 2 - 16))
    screen.blit(style_text, (screen_w / 2 - style_text.get_width() / 2, screen_h / 2 + 12))
    screen.blit(footer, (screen_w / 2 - footer.get_width() / 2, screen_h / 2 + 52))


def draw_mirror_phase_hint(screen, fonts):
    screen_w = screen.get_width()
    hint = fonts.small.render("Mirror phase: both the bright shot and its reflection can hit you.", True, (205, 215, 255))
    screen.blit(hint, (screen_w / 2 - hint.get_width() / 2, 102))


def draw_safe_zone_hint(screen, fonts):
    screen_w = screen.get_width()
    text = fonts.tiny.render(f"Safe zones delete shots inside a {SAFE_ZONE_RADIUS}px radius.", True, (120, 210, 240))
    screen.blit(text, (screen_w - text.get_width() - 18, 80))
