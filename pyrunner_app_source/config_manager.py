# -*- coding: utf-8 -*-
"""
Kullanıcı ayarlarını (tema, font boyutu, Gemini API key/model) kalıcı olarak
saklar. Android'de uygulamanın kendi özel/güvenli veri klasörüne
(App.user_data_dir) yazar; bu klasör için ekstra izin gerekmez.

Bu dosya kasıtlı olarak Kivy'ye SIKI bağımlı değildir: Kivy kurulu değilken
(örn. masaüstünde test ederken) de import edilip test edilebilir.
"""
import json
import os

from themes import DEFAULT_THEME, DEFAULT_FONT_SIZE

CONFIG_FILENAME = "pyrunner_config.json"

DEFAULTS = {
    "theme": DEFAULT_THEME,
    "font_size": DEFAULT_FONT_SIZE,
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash",
}


def _get_base_dir():
    """Kivy çalışıyorsa uygulamanın özel veri klasörünü, yoksa mevcut dizini döner."""
    try:
        from kivy.app import App
        app = App.get_running_app()
        if app is not None:
            return app.user_data_dir
    except Exception:
        pass
    return "."


def _get_config_path(base_dir=None):
    base = base_dir if base_dir is not None else _get_base_dir()
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, CONFIG_FILENAME)


def load_config(base_dir=None):
    """Kayıtlı ayarları döner; dosya yoksa veya bozuksa varsayılanları döner.
    Bu fonksiyon ASLA exception fırlatmaz (uygulama açılışını asla bozmamalı)."""
    path = _get_config_path(base_dir)
    cfg = DEFAULTS.copy()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                cfg.update(saved)
        except Exception as e:
            print(f"[config_manager] ayarlar okunamadı, varsayılanlar kullanılıyor: {e}")
    return cfg


def save_config(cfg, base_dir=None):
    """Ayarları diske yazar. Başarılıysa True, değilse False döner."""
    path = _get_config_path(base_dir)
    try:
        # Sadece bilinen anahtarları kaydet (ileride yapı değişirse çöp birikmesin)
        clean = {k: cfg.get(k, v) for k, v in DEFAULTS.items()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[config_manager] ayarlar kaydedilemedi: {e}")
        return False
