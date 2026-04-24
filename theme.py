"""theme.py — ThemeManager centralizado para DeepCore CRM Pro."""
import json, os
from typing import Callable

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

DEFAULTS = {
    "accent_color":       "#10B981",
    "font_family":        "Segoe UI",
    "start_with_windows": False,
    "minimize_to_tray":   True,
    "notifications":      True,
}


class ThemeManager:
    """Singleton. Gestiona paleta, configuración y notificaciones de cambio."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ready = False
        return cls._instance

    def __init__(self):
        if self._ready:
            return
        self._ready = True
        self._listeners: list[Callable] = []
        self.cfg = dict(DEFAULTS)
        self._load()
        self._build_palette()

    def _load(self):
        try:
            if os.path.exists(_CONFIG_PATH):
                with open(_CONFIG_PATH, encoding='utf-8') as f:
                    self.cfg.update(json.load(f))
        except Exception:
            pass

    def save(self):
        try:
            with open(_CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.cfg, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _build_palette(self):
        a = self.cfg['accent_color']
        self.C: dict[str, str] = {
            # Acento configurable
            'accent':    a,
            # Fondos OLED
            'base':      '#0c0c0e',
            'mantle':    '#080809',
            'sidebar':   '#090909',
            'surface0':  '#101014',
            'surface1':  '#141418',
            'surface2':  '#1a1a1f',
            # Bordes
            'border':    '#1a1a1f',
            'border2':   '#111115',
            # Estados interactivos
            'hover':     '#111115',
            'active':    '#161620',
            # Texto
            'overlay0':  '#2e2e38',
            'overlay1':  '#42424e',
            'overlay2':  '#52525b',
            'text':      '#e4e4e7',
            'text2':     '#a0a0b0',
            'heading':   '#f0f0f3',
            # Semánticos
            'green':     '#10B981',
            'green_bg':  '#0a1a10',
            'amber':     '#F59E0B',
            'amber_bg':  '#1a1408',
            'red':       '#EF4444',
            'red_bg':    '#1a0a0e',
            'blue':      '#60A5FA',
            'indigo':    '#818CF8',
            'teal':      '#2DD4BF',
            'sky':       '#38BDF8',
            # Alias compatibilidad
            'card':      '#101014',
            'card2':     '#141418',
            'texto':     '#e4e4e7',
            'subtexto':  '#a0a0b0',
            'borde':     '#1a1a1f',
            'verde':     '#10B981',
            'amarillo':  '#F59E0B',
            'rojo':      '#EF4444',
            # Extras usados por agent_panel y otros módulos
            'mauve':     '#C084FC',
            'crust':     '#080809',
            'yellow':    '#F59E0B',
            'lavender':  '#818CF8',
            'peach':     '#FB923C',
        }

    def set_accent(self, color: str):
        self.cfg['accent_color'] = color
        self._build_palette()
        self._notify()

    def add_listener(self, fn: Callable):
        if fn not in self._listeners:
            self._listeners.append(fn)

    def remove_listener(self, fn: Callable):
        if fn in self._listeners:
            self._listeners.remove(fn)

    def _notify(self):
        for fn in list(self._listeners):
            try:
                fn()
            except Exception:
                pass


theme = ThemeManager()
