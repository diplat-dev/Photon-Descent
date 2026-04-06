import math
import random
import sys

import pygame

from .audio import MusicManager
from .config import (
    ABILITY_SLOW_MULTIPLIER,
    BLINK_UNLOCK_ROUND,
    BUBBLE_RADIUS,
    COLOR_SWATCHES,
    FADE_DURATION,
    FPS,
    MIRROR_SPIN_BASE_DEG,
    MIRROR_SPIN_PER_ROUND,
    MIXER_BUFFER,
    MIXER_CHANNELS,
    MIXER_FREQ,
    MIXER_SIZE,
    NEAR_MISS_BUFFER,
    NOTIFICATION_DURATION,
    PHASES,
    SAFE_ZONE_CHANCE_PER_SECOND,
    SAFE_ZONE_DURATION,
    SAFE_ZONE_RADIUS,
)
from .display import DisplayManager
from .entities import (
    Player,
    SafeZone,
    Spawner,
    bullet_can_register_close_call,
    bullet_in_safe_zone,
    filter_bullets_outside_radius,
)
from .persistence import SaveStore
from .progression import ABILITIES, UPGRADE_POOL, get_phase_duration_for_round
from .ui import (
    build_ui_assets,
    create_fonts,
    draw_choice_screen,
    draw_game_over_screen,
    draw_hud,
    draw_mirror_phase_hint,
    draw_notifications,
    draw_phase_background,
    draw_safe_zone_hint,
    draw_title_screen,
)
from .utils import clamp, dist_sq_xy


def quit_game(music_manager):
    music_manager.stop_all()
    pygame.quit()
    sys.exit()


def add_notification(notifications, text, color=(200, 220, 240), duration=NOTIFICATION_DURATION):
    notifications.append({"text": text, "color": color, "time_left": duration})


def run_choice_screen(screen, display, clock, fonts, music_manager, title, subtitle, options, footer):
    while True:
        screen = display.get_render_surface(screen)
        dt = clock.tick(30) / 1000.0
        music_manager.update(dt)
        hovered_idx = None
        mouse_pos = display.get_mouse_pos()

        card_rects = draw_choice_screen(screen, fonts, title, subtitle, options, None, footer)
        for index, rect in enumerate(card_rects):
            if rect.collidepoint(mouse_pos):
                hovered_idx = index
                break

        draw_choice_screen(screen, fonts, title, subtitle, options, hovered_idx, footer)
        display.present(screen)

        for event in display.get_events():
            if event.type == pygame.QUIT:
                quit_game(music_manager)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    quit_game(music_manager)
                if pygame.K_1 <= event.key <= pygame.K_9:
                    chosen = event.key - pygame.K_1
                    if 0 <= chosen < len(options):
                        return chosen
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for index, rect in enumerate(card_rects):
                    if rect.collidepoint(event.pos):
                        return index


def spawn_safe_zone(player, arena_size):
    arena_w, arena_h = arena_size
    position = None
    for _ in range(8):
        candidate = pygame.Vector2(random.uniform(80, arena_w - 80), random.uniform(80, arena_h - 80))
        if candidate.distance_to(player.pos) > 140:
            position = candidate
            break
    if position is None:
        position = pygame.Vector2(arena_w / 2.0, arena_h / 2.0)
    return SafeZone(position, SAFE_ZONE_RADIUS, SAFE_ZONE_DURATION)


def apply_player_hit(player):
    if player.collision_immune:
        return False
    if player.absorb_hit_with_shield():
        return False
    player.hp -= 1
    return True


def process_bullets(player, bullets, safe_zones, phase_name, round_index, phase_elapsed, game_dt, arena_size):
    arena_w, arena_h = arena_size
    cx, cy = arena_w / 2.0, arena_h / 2.0
    mirror_draw_data = []
    filtered_bullets = []
    run_failed = False

    safe_zone_data = [(zone.pos.x, zone.pos.y, zone.radius * zone.radius) for zone in safe_zones]

    if phase_name == "mirror":
        spin_speed_deg = MIRROR_SPIN_BASE_DEG + ((round_index - 1) * MIRROR_SPIN_PER_ROUND)
        rotate_angle = math.radians((phase_elapsed * spin_speed_deg) % 360.0)
        cos_angle = math.cos(rotate_angle)
        sin_angle = math.sin(rotate_angle)
        angular_velocity = -math.radians(spin_speed_deg)
    else:
        cos_angle = 1.0
        sin_angle = 0.0
        angular_velocity = 0.0

    for bullet in bullets:
        bullet.update(game_dt, phase_name, arena_size, player)

        if phase_name == "mirror":
            rel_x = bullet.pos.x - cx
            rel_y = bullet.pos.y - cy
            bullet.pos.x += (-rel_y * angular_velocity) * game_dt
            bullet.pos.y += (rel_x * angular_velocity) * game_dt

        lifetime = bullet.pattern.get("lifetime")
        if lifetime is not None and bullet.age >= lifetime:
            continue
        if bullet.offscreen(arena_size):
            continue
        if bullet_in_safe_zone(bullet, safe_zone_data):
            continue

        if phase_name == "mirror":
            dx = bullet.pos.x - cx
            dy = bullet.pos.y - cy
            rotated_x = cx + (dx * cos_angle) + (dy * sin_angle)
            rotated_y = cy - (dx * sin_angle) + (dy * cos_angle)
            mirror_x = arena_w - rotated_x
            mirror_y = rotated_y

            collision_radius = bullet.radius + player.radius
            collision_radius_sq = collision_radius * collision_radius
            near_radius = collision_radius + NEAR_MISS_BUFFER
            near_radius_sq = near_radius * near_radius

            primary_hit = dist_sq_xy(rotated_x, rotated_y, player.pos.x, player.pos.y) < collision_radius_sq
            mirror_hit = dist_sq_xy(mirror_x, mirror_y, player.pos.x, player.pos.y) < collision_radius_sq
            if primary_hit or mirror_hit:
                if apply_player_hit(player):
                    run_failed = True
                    break
            elif bullet_can_register_close_call(bullet):
                if (
                    dist_sq_xy(rotated_x, rotated_y, player.pos.x, player.pos.y) < near_radius_sq
                    or dist_sq_xy(mirror_x, mirror_y, player.pos.x, player.pos.y) < near_radius_sq
                ):
                    bullet.close_call_registered = True
                    player.close_calls += 1

            filtered_bullets.append(bullet)
            mirror_draw_data.append((bullet, (rotated_x, rotated_y), (mirror_x, mirror_y)))
            continue

        collision_radius = bullet.radius + player.radius
        collision_radius_sq = collision_radius * collision_radius
        bullet_dist_sq = dist_sq_xy(bullet.pos.x, bullet.pos.y, player.pos.x, player.pos.y)
        if bullet_dist_sq < collision_radius_sq:
            if apply_player_hit(player):
                run_failed = True
                break
        elif bullet_can_register_close_call(bullet):
            near_radius = collision_radius + NEAR_MISS_BUFFER
            if bullet_dist_sq < near_radius * near_radius:
                bullet.close_call_registered = True
                player.close_calls += 1

        filtered_bullets.append(bullet)

    return filtered_bullets, mirror_draw_data, run_failed


def handle_run_events(display, player, bullets, notifications, arena_size):
    arena_w, arena_h = arena_size
    for event in display.get_events():
        if event.type == pygame.QUIT:
            return "quit", bullets
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "quit", bullets
            if event.key == pygame.K_SPACE:
                player.try_dash()
            elif event.key == pygame.K_e:
                if player.special_ability == "slow" and player.can_use_ability():
                    player.use_slow()
                    add_notification(notifications, "Slow motion engaged", (240, 220, 80), 1.6)
            elif event.key == pygame.K_r:
                if player.special_ability == "bubble" and player.can_use_ability():
                    if player.use_bubble():
                        bullets = filter_bullets_outside_radius(bullets, player.pos, BUBBLE_RADIUS)
                        add_notification(notifications, "Bubble burst cleared nearby shots", (120, 220, 255), 1.5)
            elif event.key == pygame.K_j:
                player.invincible = not player.invincible
                status = "on" if player.invincible else "off"
                add_notification(notifications, f"Debug invincible {status}", (255, 160, 90), 1.2)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if player.try_blink(event.pos, arena_size):
                    add_notification(notifications, "Blink executed", (120, 220, 255), 1.1)
            elif event.button == 3:
                if player.use_teleport_ability(True):
                    player.pos = pygame.Vector2(clamp(event.pos[0], 20, arena_w - 20), clamp(event.pos[1], 20, arena_h - 20))
                    add_notification(notifications, "Teleport tether active", (200, 220, 255), 1.0)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            if player.teleport_tether_active:
                player.use_teleport_ability(False)
                add_notification(notifications, "Snapped back to tether origin", (200, 220, 255), 1.0)

    return "continue", bullets


def run_game(screen, display, clock, fonts, ui_assets, music_manager, save_store, selected_color_idx, high_score):
    screen = display.get_render_surface(screen)
    arena_w, arena_h = screen.get_size()
    player = Player((arena_w / 2, arena_h * 0.75))
    player.color = COLOR_SWATCHES[selected_color_idx]

    bullets = []
    spawner = Spawner()
    safe_zones = []
    notifications = []

    round_index = 1
    phase_idx = 0
    phase_elapsed = 0.0
    phase_duration = get_phase_duration_for_round(round_index)
    current_phase = PHASES[phase_idx]
    music_manager.set_phase(current_phase)

    safe_zone_acc = 0.0
    running = True

    while running:
        screen = display.get_render_surface(screen)
        arena_size = screen.get_size()
        arena_w, arena_h = arena_size
        dt_real = clock.tick(FPS) / 1000.0
        music_manager.update(dt_real)

        for item in notifications:
            item["time_left"] -= dt_real
        notifications[:] = [item for item in notifications if item["time_left"] > 0.0]

        global_time_scale = ABILITY_SLOW_MULTIPLIER if player.slow_active_timer > 0.0 else 1.0
        game_dt = dt_real * global_time_scale
        phase_dt = game_dt * player.time_scale
        phase_name = PHASES[phase_idx]

        event_result, bullets = handle_run_events(display, player, bullets, notifications, arena_size)
        if event_result == "quit":
            quit_game(music_manager)

        keys = pygame.key.get_pressed()
        if player.teleport_tether_active:
            mx, my = display.get_mouse_pos()
            player.pos.update(clamp(mx, 20, arena_w - 20), clamp(my, 20, arena_h - 20))

        player.update(game_dt, keys, phase_name, arena_size)
        spawner.update(game_dt, bullets, phase_name, phase_elapsed, phase_duration, round_index, player, arena_size)

        safe_zone_acc += dt_real
        if safe_zone_acc >= 0.2:
            if random.random() < SAFE_ZONE_CHANCE_PER_SECOND * safe_zone_acc:
                new_zone = spawn_safe_zone(player, arena_size)
                safe_zones.append(new_zone)
                bullets = filter_bullets_outside_radius(bullets, new_zone.pos, new_zone.radius)
                add_notification(notifications, "Safe zone stabilized", (80, 200, 240), 1.3)
            safe_zone_acc = 0.0

        remaining_zones = []
        for zone in safe_zones:
            if zone.update(dt_real):
                remaining_zones.append(zone)
        safe_zones = remaining_zones

        bullets, mirror_draw_data, run_failed = process_bullets(
            player,
            bullets,
            safe_zones,
            phase_name,
            round_index,
            phase_elapsed,
            game_dt,
            arena_size,
        )
        if run_failed:
            running = False

        player.score += dt_real * player.score_multiplier
        phase_elapsed += phase_dt

        display_high_score = max(high_score, int(player.score))

        draw_phase_background(screen, phase_name)
        for zone in safe_zones:
            zone.draw(screen)

        if phase_name == "mirror":
            for bullet, rotated_pos, mirrored_pos in mirror_draw_data:
                bullet.draw(screen, pos_override=rotated_pos)
                bullet.draw(screen, pos_override=mirrored_pos, ghost=True)
            draw_mirror_phase_hint(screen, fonts)
        else:
            for bullet in bullets:
                bullet.draw(screen)

        if safe_zones:
            draw_safe_zone_hint(screen, fonts)

        if player.teleport_tether_active and player.teleport_tether_origin is not None:
            marker = ui_assets["teleport_marker"]
            screen.blit(marker, (int(player.teleport_tether_origin.x - 24), int(player.teleport_tether_origin.y - 24)))

        player.draw(screen)
        draw_hud(screen, fonts, player, round_index, phase_name, phase_elapsed, phase_duration, display_high_score)

        if player.invincible:
            debug_text = fonts.small.render("DEBUG: INVINCIBLE (J to toggle)", True, (255, 140, 60))
            screen.blit(debug_text, (arena_w / 2 - debug_text.get_width() / 2, 126))

        if player.teleport_tether_active:
            tether_text = fonts.small.render("Teleport tether active: release right click to return.", True, (200, 220, 255))
            screen.blit(tether_text, (arena_w / 2 - tether_text.get_width() / 2, 150))

        if player.slow_active_timer > 0.0:
            slow_label = ui_assets["slow_label"]
            screen.blit(slow_label, (arena_w / 2 - slow_label.get_width() / 2, 174))

        draw_notifications(screen, fonts, notifications)
        display.present(screen)

        if phase_elapsed >= phase_duration and player.hp > 0:
            if player.teleport_tether_active:
                player.use_teleport_ability(False)

            upgrade_index = run_choice_screen(
                screen,
                display,
                clock,
                fonts,
                music_manager,
                f"Phase Complete - Round {round_index} - {phase_name.upper()}",
                "Choose one permanent upgrade:",
                UPGRADE_POOL,
                "Click or press 1-4 to continue.",
            )
            chosen_upgrade = UPGRADE_POOL[upgrade_index]
            chosen_upgrade["apply"](player)
            add_notification(notifications, f"Upgrade acquired: {chosen_upgrade['name']}", (140, 230, 255), 2.2)

            phase_idx += 1
            if phase_idx >= len(PHASES):
                phase_idx = 0
                ability_index = run_choice_screen(
                    screen,
                    display,
                    clock,
                    fonts,
                    music_manager,
                    f"Round Complete - Choose Ability for Round {round_index + 1}",
                    "Pick the ability you want for the next round.",
                    ABILITIES,
                    "Click or press 1-3 to lock it in.",
                )
                player.special_ability = ABILITIES[ability_index]["key"]
                player.ability_available_for_round = True
                player.ability_on_cooldown = 0.0
                player.slow_active_timer = 0.0
                round_index += 1
                player.rounds_completed += 1
                high_score = max(high_score, int(player.score))
                save_store.update_high_score(high_score)
                if round_index >= BLINK_UNLOCK_ROUND and player.unlock_blink():
                    add_notification(notifications, "Blink unlocked: left click to reposition.", (120, 220, 255), 3.0)

            phase_duration = get_phase_duration_for_round(round_index)
            phase_elapsed = 0.0
            bullets.clear()
            safe_zones.clear()
            current_phase = PHASES[phase_idx]
            music_manager.set_phase(current_phase)

        if player.hp <= 0:
            running = False

    high_score = max(high_score, int(player.score))
    save_store.update_high_score(high_score)

    while True:
        screen = display.get_render_surface(screen)
        dt = clock.tick(30) / 1000.0
        music_manager.update(dt)
        draw_game_over_screen(screen, fonts, player.score, high_score, player.close_calls)
        display.present(screen)

        for event in display.get_events():
            if event.type == pygame.QUIT:
                quit_game(music_manager)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return save_store.high_score
                if event.key == pygame.K_ESCAPE:
                    quit_game(music_manager)


def run_title(screen, display, clock, fonts, ui_assets, music_manager, save_store, selected_color_idx):
    dragging_volume = False
    music_manager.set_phase("title")
    music_manager.set_master_volume(save_store.volume)

    while True:
        screen = display.get_render_surface(screen)
        dt_real = clock.tick(FPS) / 1000.0
        music_manager.update(dt_real)
        mouse_pos = display.get_mouse_pos()
        layout = draw_title_screen(
            screen,
            fonts,
            ui_assets,
            selected_color_idx,
            save_store.volume,
            save_store.high_score,
            mouse_pos,
        )
        display.present(screen)

        for event in display.get_events():
            if event.type == pygame.QUIT:
                quit_game(music_manager)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    quit_game(music_manager)
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return selected_color_idx
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if layout["start_rect"].collidepoint(event.pos):
                    return selected_color_idx
                for index, rect in enumerate(layout["swatch_rects"]):
                    if rect.collidepoint(event.pos):
                        selected_color_idx = index
                        save_store.set_color_idx(index)
                        break
                if layout["slider_rect"].collidepoint(event.pos):
                    dragging_volume = True
                    volume = clamp((event.pos[0] - layout["slider_rect"].x) / layout["slider_rect"].width, 0.0, 1.0)
                    music_manager.set_master_volume(volume)
                    save_store.set_volume(volume)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_volume = False
            if event.type == pygame.MOUSEMOTION and dragging_volume:
                volume = clamp((event.pos[0] - layout["slider_rect"].x) / layout["slider_rect"].width, 0.0, 1.0)
                music_manager.set_master_volume(volume)
                save_store.set_volume(volume)


def main():
    pygame.mixer.pre_init(
        frequency=MIXER_FREQ,
        size=MIXER_SIZE,
        channels=MIXER_CHANNELS,
        buffer=MIXER_BUFFER,
    )
    pygame.init()
    display = DisplayManager()
    screen = display.get_render_surface()
    pygame.display.set_caption("Photon Descent")
    clock = pygame.time.Clock()
    fonts = create_fonts()
    ui_assets = build_ui_assets(fonts)
    save_store = SaveStore()
    music_manager = MusicManager(fade_duration=FADE_DURATION)
    music_manager.set_master_volume(save_store.volume)

    selected_color_idx = save_store.color_idx
    while True:
        selected_color_idx = run_title(
            screen,
            display,
            clock,
            fonts,
            ui_assets,
            music_manager,
            save_store,
            selected_color_idx,
        )
        screen = display.get_render_surface(screen)
        save_store.set_color_idx(selected_color_idx)
        run_game(
            screen,
            display,
            clock,
            fonts,
            ui_assets,
            music_manager,
            save_store,
            selected_color_idx,
            save_store.high_score,
        )
        screen = display.get_render_surface(screen)
