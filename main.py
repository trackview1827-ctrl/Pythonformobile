# -*- coding: utf-8 -*-
"""
PyRunner AI - Ana uygulama.

Ekran düzeni:
  [ Araç çubuğu: Çalıştır / Durdur / Adım / Devam ]
  [ Araç çubuğu 2: Breakpoint / Pip / Ayarlar     ]
  [ Kod editörü (satır numaralı, temalı)          ]
  [ Durum satırı                                  ]
  [ Çıktı paneli (stdout + hata + AI analiz)      ]
  [ AI ile Analiz Et (sadece hata sonrası görünür) ]
"""
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.utils import escape_markup

from editor_widgets import CodeEditor
from executor import ExecutionController
from ai_helper import analyze_error_async
from pip_manager import install_package_async, is_pip_available
import config_manager
from themes import get_theme, theme_names, MIN_FONT_SIZE, MAX_FONT_SIZE

# Klavye açıldığında input alanını kapatmasın diye (Android)
Window.softinput_mode = "below_target"

DEFAULT_CODE = (
    "# Python kodunu buraya yaz ve Calistir'a bas\n"
    "print(\"Merhaba PyRunner!\")\n"
    "\n"
    "toplam = 0\n"
    "for i in range(5):\n"
    "    toplam += i\n"
    "print(\"Toplam:\", toplam)\n"
)


class OutputPanel(ScrollView):
    """Program çıktısını / hatalarını gösteren, otomatik en alta kayan panel."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_scroll_x = False
        self.label = Label(
            text="",
            markup=True,
            size_hint_y=None,
            halign="left",
            valign="top",
            font_size=dp(13),
        )
        self.label.bind(texture_size=self._on_texture_size)
        self.bind(width=self._on_width_change)
        self.add_widget(self.label)

    def _on_width_change(self, instance, width):
        self.label.text_size = (max(width - dp(8), dp(10)), None)

    def _on_texture_size(self, instance, texture_size):
        self.label.height = texture_size[1]

    def append(self, text, color=None):
        safe = escape_markup(text)
        if color:
            safe = f"[color={color}]{safe}[/color]"
        self.label.text += safe
        Clock.schedule_once(lambda dt: setattr(self, "scroll_y", 0), 0.05)

    def clear(self):
        self.label.text = ""


class SettingsPopup(Popup):
    def __init__(self, app, **kwargs):
        self.app_ref = app
        super().__init__(title="Ayarlar", size_hint=(0.92, 0.85), **kwargs)

        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))

        root.add_widget(Label(text="Tema", size_hint_y=None, height=dp(24)))
        self.theme_spinner = Spinner(
            text=app.cfg["theme"], values=theme_names(),
            size_hint_y=None, height=dp(44),
        )
        root.add_widget(self.theme_spinner)

        root.add_widget(Label(text="Yazi Boyutu", size_hint_y=None, height=dp(24)))
        font_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.font_slider = Slider(
            min=MIN_FONT_SIZE, max=MAX_FONT_SIZE, value=app.cfg["font_size"], step=1
        )
        self.font_value_label = Label(text=str(int(app.cfg["font_size"])), size_hint_x=None, width=dp(36))
        self.font_slider.bind(
            value=lambda inst, v: setattr(self.font_value_label, "text", str(int(v)))
        )
        font_row.add_widget(self.font_slider)
        font_row.add_widget(self.font_value_label)
        root.add_widget(font_row)

        root.add_widget(Label(text="Gemini API Key", size_hint_y=None, height=dp(24)))
        self.api_key_input = TextInput(
            text=app.cfg.get("gemini_api_key", ""), multiline=False, password=True,
            size_hint_y=None, height=dp(44),
        )
        root.add_widget(self.api_key_input)

        root.add_widget(Label(text="Gemini Model Adi", size_hint_y=None, height=dp(24)))
        self.model_input = TextInput(
            text=app.cfg.get("gemini_model", "gemini-2.5-flash"), multiline=False,
            size_hint_y=None, height=dp(44),
        )
        root.add_widget(self.model_input)

        info = Label(
            text="[size=11][i]API key: aistudio.google.com/apikey[/i][/size]",
            markup=True, size_hint_y=None, height=dp(22),
        )
        root.add_widget(info)

        # Boşluk dolgusu (butonlar alta yapışmasın)
        root.add_widget(BoxLayout())

        btn_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        cancel_btn = Button(text="Iptal")
        save_btn = Button(text="Kaydet")
        cancel_btn.bind(on_release=lambda *a: self.dismiss())
        save_btn.bind(on_release=self._on_save)
        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(save_btn)
        root.add_widget(btn_row)

        self.content = root

    def _on_save(self, *args):
        self.app_ref.cfg["theme"] = self.theme_spinner.text
        self.app_ref.cfg["font_size"] = int(self.font_slider.value)
        self.app_ref.cfg["gemini_api_key"] = self.api_key_input.text.strip()
        self.app_ref.cfg["gemini_model"] = self.model_input.text.strip() or "gemini-2.5-flash"
        config_manager.save_config(self.app_ref.cfg)
        self.app_ref.apply_theme()
        self.dismiss()


class PipPopup(Popup):
    def __init__(self, app, **kwargs):
        self.app_ref = app
        super().__init__(title="Paket Kur (pip)", size_hint=(0.92, 0.85), **kwargs)

        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))

        warn_text = (
            "[size=11]Sadece SAF Python paketleri (ör. requests, arrow) telefonda "
            "kurulabilir. numpy/pandas/opencv gibi derleme gerektiren paketleri "
            "buildozer.spec 'requirements' satirina ekleyip APK'yi yeniden "
            "derlemen gerekir.[/size]"
        )
        if not is_pip_available():
            warn_text = (
                "[color=ff5555][size=12]Bu derlemede pip modulu dahil edilmemis. "
                "buildozer.spec 'requirements' satirina 'pip' ekleyip yeniden "
                "derlemen gerekiyor.[/size][/color]"
            )
        root.add_widget(Label(text=warn_text, markup=True, size_hint_y=None, height=dp(70)))

        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.pkg_input = TextInput(hint_text="paket-adi (or. requests)", multiline=False)
        install_btn = Button(text="Kur", size_hint_x=None, width=dp(72), disabled=not is_pip_available())
        install_btn.bind(on_release=self._on_install)
        row.add_widget(self.pkg_input)
        row.add_widget(install_btn)
        root.add_widget(row)

        self.log_panel = OutputPanel()
        root.add_widget(self.log_panel)

        close_btn = Button(text="Kapat", size_hint_y=None, height=dp(44))
        close_btn.bind(on_release=lambda *a: self.dismiss())
        root.add_widget(close_btn)

        self.content = root

    def _on_install(self, *args):
        pkg = self.pkg_input.text.strip()
        if not pkg:
            return
        self.log_panel.append(f"Kuruluyor: {pkg}...\n")

        def on_output(line):
            Clock.schedule_once(lambda dt: self.log_panel.append(line + "\n"), 0)

        def on_done(success, msg):
            def _upd(dt):
                color = "55ff55" if success else "ff5555"
                self.log_panel.append(f"{msg}\n", color=color)
            Clock.schedule_once(_upd, 0)

        install_package_async(pkg, on_output, on_done)


class PyRunnerApp(App):
    def build(self):
        self.title = "PyRunner AI"
        self.cfg = config_manager.load_config()
        self.last_error_context = None  # (kod, tam_traceback) - AI analiz icin

        root = BoxLayout(orientation="vertical")

        # ---- Araç çubuğu satır 1: çalıştırma kontrolleri ----
        toolbar1 = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(3), padding=(dp(3), dp(3)))
        self.run_btn = Button(text="Calistir", font_size=dp(13))
        self.stop_btn = Button(text="Durdur", font_size=dp(13), disabled=True)
        self.step_btn = Button(text="Adim", font_size=dp(13), disabled=True)
        self.continue_btn = Button(text="Devam", font_size=dp(13), disabled=True)
        for b in (self.run_btn, self.stop_btn, self.step_btn, self.continue_btn):
            toolbar1.add_widget(b)
        root.add_widget(toolbar1)

        # ---- Araç çubuğu satır 2: yardımcı araçlar ----
        toolbar2 = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(3), padding=(dp(3), dp(3)))
        self.bp_btn = Button(text="Breakpoint (imlec satiri)", font_size=dp(12))
        self.pip_btn = Button(text="Pip", font_size=dp(12), size_hint_x=0.3)
        self.settings_btn = Button(text="Ayarlar", font_size=dp(12), size_hint_x=0.3)
        toolbar2.add_widget(self.bp_btn)
        toolbar2.add_widget(self.pip_btn)
        toolbar2.add_widget(self.settings_btn)
        root.add_widget(toolbar2)

        self.run_btn.bind(on_release=self.on_run_pressed)
        self.stop_btn.bind(on_release=self.on_stop_pressed)
        self.step_btn.bind(on_release=self.on_step_pressed)
        self.continue_btn.bind(on_release=self.on_continue_pressed)
        self.bp_btn.bind(on_release=self.on_toggle_breakpoint)
        self.pip_btn.bind(on_release=self.on_open_pip)
        self.settings_btn.bind(on_release=self.on_open_settings)

        # ---- Kod editörü ----
        self.editor = CodeEditor(size_hint_y=0.5)
        self.editor.set_text(DEFAULT_CODE)
        root.add_widget(self.editor)

        # ---- Durum satırı ----
        self.status_label = Label(
            text="Hazir.", size_hint_y=None, height=dp(24), font_size=dp(12),
            halign="left", valign="middle",
        )
        self.status_label.bind(size=lambda i, s: setattr(i, "text_size", s))
        root.add_widget(self.status_label)

        # ---- Çıktı paneli ----
        self.output_panel = OutputPanel(size_hint_y=0.32)
        root.add_widget(self.output_panel)

        # ---- AI analiz butonu (başlangıçta gizli) ----
        self.ai_btn = Button(text="AI ile Analiz Et", size_hint_y=None, height=0, opacity=0, disabled=True)
        self.ai_btn.bind(on_release=self.on_ai_analyze_pressed)
        root.add_widget(self.ai_btn)

        self.controller = ExecutionController(
            on_output=self._cb_output,
            on_line_change=self._cb_line_change,
            on_paused=self._cb_paused,
            on_finished=self._cb_finished,
            on_error=self._cb_error,
        )

        self.apply_theme()
        return root

    # ---------------- Tema uygulama ----------------

    def apply_theme(self):
        theme = get_theme(self.cfg["theme"])
        self.editor.set_pygments_style(theme["pygments_style"])
        self.editor.set_colors(theme["editor_bg"], theme["editor_fg"])
        self.editor.set_font_size(self.cfg["font_size"])
        try:
            Window.clearcolor = theme["app_bg"]
        except Exception as e:
            print(f"[PyRunnerApp] pencere rengi ayarlanamadi: {e}")

    # ---------------- Buton olayları ----------------

    def on_run_pressed(self, *args):
        if self.controller.is_running():
            return
        self.output_panel.clear()
        self.editor.clear_run_markers()
        self._hide_ai_button()
        self.last_error_context = None

        self.controller.set_breakpoints(self.editor.breakpoints)
        self.controller.run(self.editor.get_text())

        self.run_btn.disabled = True
        self.stop_btn.disabled = False
        self.step_btn.disabled = True
        self.continue_btn.disabled = True
        self.status_label.text = "Calisiyor..."

    def on_stop_pressed(self, *args):
        self.controller.stop()
        self.status_label.text = "Durduruluyor..."

    def on_step_pressed(self, *args):
        self.controller.step()
        self.step_btn.disabled = True
        self.continue_btn.disabled = True

    def on_continue_pressed(self, *args):
        self.controller.resume()
        self.editor.debug_line = 0
        self.step_btn.disabled = True
        self.continue_btn.disabled = True

    def on_toggle_breakpoint(self, *args):
        line, active = self.editor.toggle_breakpoint_at_cursor()
        state = "eklendi" if active else "kaldirildi"
        self.status_label.text = f"Satir {line}: breakpoint {state}"

    def on_open_settings(self, *args):
        SettingsPopup(self).open()

    def on_open_pip(self, *args):
        PipPopup(self).open()

    def on_ai_analyze_pressed(self, *args):
        if not self.last_error_context:
            return
        code, tb = self.last_error_context
        api_key = self.cfg.get("gemini_api_key", "")
        model = self.cfg.get("gemini_model", "gemini-2.5-flash")

        if not api_key:
            self.output_panel.append(
                "\n[Gemini API key girilmemis. Ayarlar'dan ekleyebilirsin.]\n", color="ffaa00"
            )
            return

        self.status_label.text = "AI analiz ediyor..."
        self.ai_btn.disabled = True

        def on_result(text):
            def _upd(dt):
                self.output_panel.append("\n--- AI ANALIZ ---\n" + text + "\n", color="88c0ff")
                self.status_label.text = "Hazir."
                self.ai_btn.disabled = False
            Clock.schedule_once(_upd, 0)

        def on_error(msg):
            def _upd(dt):
                self.output_panel.append(f"\n[AI analiz hatasi: {msg}]\n", color="ff5555")
                self.status_label.text = "Hazir."
                self.ai_btn.disabled = False
            Clock.schedule_once(_upd, 0)

        analyze_error_async(code, tb, api_key, model, on_result, on_error)

    def _hide_ai_button(self):
        self.ai_btn.disabled = True
        self.ai_btn.opacity = 0
        self.ai_btn.height = 0

    def _show_ai_button(self):
        self.ai_btn.disabled = False
        self.ai_btn.opacity = 1
        self.ai_btn.height = dp(40)

    # ------------- Executor callback'leri (worker thread -> Clock ile ana thread) -------------

    def _cb_output(self, text):
        Clock.schedule_once(lambda dt: self.output_panel.append(text), 0)

    def _cb_line_change(self, line_no):
        pass  # su an icin sadece paused/error durumlarinda gorsel vurgu yapiliyor

    def _cb_paused(self, line_no, local_vars):
        def _upd(dt):
            self.editor.debug_line = line_no
            vars_text = ", ".join(f"{k}={v}" for k, v in local_vars.items()) or "(yok)"
            self.status_label.text = f"Satir {line_no}'da duraklatildi | {vars_text}"
            self.step_btn.disabled = False
            self.continue_btn.disabled = False
        Clock.schedule_once(_upd, 0)

    def _cb_finished(self):
        def _upd(dt):
            self.run_btn.disabled = False
            self.stop_btn.disabled = True
            self.step_btn.disabled = True
            self.continue_btn.disabled = True
            self.editor.debug_line = 0
            if self.status_label.text.startswith(("Calisiyor", "Durduruluyor")):
                self.status_label.text = "Tamamlandi."
        Clock.schedule_once(_upd, 0)

    def _cb_error(self, line_no, short_msg, full_tb):
        def _upd(dt):
            self.editor.error_line = line_no
            self.output_panel.append(f"\n{short_msg}\n", color="ff5555")
            self.status_label.text = f"Hata: satir {line_no}"
            self.last_error_context = (self.editor.get_text(), full_tb)
            self._show_ai_button()
            self.run_btn.disabled = False
            self.stop_btn.disabled = True
            self.step_btn.disabled = True
            self.continue_btn.disabled = True
        Clock.schedule_once(_upd, 0)


if __name__ == "__main__":
    PyRunnerApp().run()
