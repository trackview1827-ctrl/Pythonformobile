# -*- coding: utf-8 -*-
"""
Uygulama genelinde kullanılan temalar.

Her tema hem uygulamanın genel arayüz renklerini hem de kod editöründeki
söz dizimi renklendirmesi (syntax highlighting) için kullanılacak Pygments
stilinin adını tanımlar. Pygments stil isimleri sabittir (pygments paketiyle
gelir), bu yüzden zaman içinde bozulma riski yoktur.
"""

THEMES = {
    "Koyu (Monokai)": {
        "pygments_style": "monokai",
        "app_bg": (0.11, 0.11, 0.13, 1),
        "panel_bg": (0.16, 0.16, 0.18, 1),
        "toolbar_bg": (0.09, 0.09, 0.10, 1),
        "fg": (0.92, 0.92, 0.92, 1),
        "accent": (0.30, 0.65, 1.0, 1),
        "editor_bg": (0.153, 0.157, 0.133, 1),
        "editor_fg": (0.97, 0.97, 0.95, 1),
    },
    "Dracula": {
        "pygments_style": "dracula",
        "app_bg": (0.16, 0.16, 0.21, 1),
        "panel_bg": (0.20, 0.20, 0.27, 1),
        "toolbar_bg": (0.14, 0.14, 0.19, 1),
        "fg": (0.94, 0.94, 0.96, 1),
        "accent": (0.74, 0.58, 0.98, 1),
        "editor_bg": (0.157, 0.165, 0.212, 1),
        "editor_fg": (0.97, 0.97, 0.98, 1),
    },
    "Açık (Light)": {
        "pygments_style": "default",
        "app_bg": (0.96, 0.96, 0.96, 1),
        "panel_bg": (1, 1, 1, 1),
        "toolbar_bg": (0.90, 0.90, 0.90, 1),
        "fg": (0.10, 0.10, 0.10, 1),
        "accent": (0.10, 0.45, 0.85, 1),
        "editor_bg": (1, 1, 1, 1),
        "editor_fg": (0.05, 0.05, 0.05, 1),
    },
    "Solarized Light": {
        "pygments_style": "solarized-light",
        "app_bg": (0.99, 0.96, 0.89, 1),
        "panel_bg": (0.99, 0.96, 0.89, 1),
        "toolbar_bg": (0.94, 0.91, 0.84, 1),
        "fg": (0.40, 0.48, 0.51, 1),
        "accent": (0.15, 0.55, 0.82, 1),
        "editor_bg": (0.99, 0.96, 0.89, 1),
        "editor_fg": (0.40, 0.48, 0.51, 1),
    },
    "Terminal (Native)": {
        "pygments_style": "native",
        "app_bg": (0.0, 0.0, 0.0, 1),
        "panel_bg": (0.08, 0.08, 0.08, 1),
        "toolbar_bg": (0.05, 0.05, 0.05, 1),
        "fg": (0.85, 0.85, 0.85, 1),
        "accent": (0.2, 0.9, 0.4, 1),
        "editor_bg": (0.0, 0.0, 0.0, 1),
        "editor_fg": (0.85, 0.85, 0.85, 1),
    },
}

DEFAULT_THEME = "Koyu (Monokai)"

# Yazı tipi boyutu sınırları (Ayarlar ekranındaki kaydırıcı için)
MIN_FONT_SIZE = 10
MAX_FONT_SIZE = 28
DEFAULT_FONT_SIZE = 16


def get_theme(name):
    """Var olmayan bir tema istenirse varsayılana düşer (uygulama asla çökmemeli)."""
    return THEMES.get(name, THEMES[DEFAULT_THEME])


def theme_names():
    return list(THEMES.keys())
