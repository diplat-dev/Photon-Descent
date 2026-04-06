import pygame

from .config import SCREEN_H, SCREEN_W, WINDOW_MIN_H, WINDOW_MIN_W


class DisplayManager:
    def __init__(self):
        self.windowed_size = (SCREEN_W, SCREEN_H)
        self.fullscreen = False
        self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)

    def _set_windowed_mode(self, size):
        width = max(WINDOW_MIN_W, int(size[0]))
        height = max(WINDOW_MIN_H, int(size[1]))
        self.windowed_size = (width, height)
        self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self.fullscreen = False

    def toggle_fullscreen(self):
        if self.fullscreen:
            self._set_windowed_mode(self.windowed_size)
            return
        self.windowed_size = self.window.get_size()
        self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.fullscreen = True

    def _handle_system_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                self.toggle_fullscreen()
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and (event.mod & pygame.KMOD_ALT):
                self.toggle_fullscreen()
                return True
        if event.type == pygame.VIDEORESIZE and not self.fullscreen:
            self._set_windowed_mode((event.w, event.h))
            return True
        return False

    def get_events(self):
        events = []
        for event in pygame.event.get():
            if self._handle_system_event(event):
                continue
            events.append(event)
        return events

    def get_mouse_pos(self):
        return pygame.mouse.get_pos()

    def get_render_surface(self, current_surface=None):
        window_size = self.window.get_size()
        if current_surface is not None and current_surface.get_size() == window_size:
            return current_surface
        return pygame.Surface(window_size).convert()

    def present(self, render_surface):
        self.window.fill((0, 0, 0))
        if render_surface is self.window:
            pass
        elif render_surface.get_size() == self.window.get_size():
            self.window.blit(render_surface, (0, 0))
        else:
            scaled = pygame.transform.smoothscale(render_surface, self.window.get_size())
            self.window.blit(scaled, (0, 0))
        pygame.display.flip()
