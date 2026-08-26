# -*- coding: utf-8 -*-
"""
Kod editörü widget'ı: satır numaraları + Python söz dizimi renklendirme
(Pygments) + hata satırını kırmızı, duraklama satırını sarı vurgulama +
imlecin bulunduğu satıra breakpoint ekleyip kaldırma.

TASARIM NOTU (dürüstlük için): Bu widget'ı Android/masaüstü ekranında görsel
olarak test edemedim çünkü bu ortamda internet ve GUI görüntüleme yok.
Bu yüzden riskli/kırılgan olabilecek yöntemlerden kaçınıldı:
  - Hata/duraklama satırı vurgusu, TextInput'un KENDİ (Kivy tarafından test
    edilmiş) metin SEÇİMİ (selection) mekanizması kırmızı/sarı renkte
    kullanılarak yapılıyor; elle piksel/koordinat hesabı YAPILMIYOR.
  - Breakpoint eklemek için kenar boşluğuna (gutter) tıklamak yerine,
    "imlecin olduğu satıra breakpoint ekle/kaldır" butonu kullanılıyor
    (TextInput'un native ve güvenilir cursor_row özelliği ile).
Satır numarası sütunu, ana editörle aynı font/satır yüksekliğine sahip,
salt-okunur ikinci bir TextInput olup scroll_y'si ana editöre bağlanarak
kaydırma senkronize ediliyor.
"""
from kivy.uix.codeinput import CodeInput
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import NumericProperty, ListProperty
from pygments.lexers import PythonLexer


class LineNumberGutter(TextInput):
    """Salt okunur satır numarası sütunu. Kullanıcı buraya dokununca odak/imleç
    değişmesin diye dokunmalar yutuluyor (yansıtılmıyor)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("readonly", True)
        kwargs.setdefault("multiline", True)
        kwargs.setdefault("halign", "right")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("cursor_width", 0)
        kwargs.setdefault("focus", False)
        super().__init__(**kwargs)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            return True  # tıklamayı yut, üst widget'lara/ TextInput mantığına iletme
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            return True
        return super().on_touch_move(touch)


class CodeEditor(BoxLayout):
    """Satır numarası sütunu + kod editörünü bir arada tutan bileşik widget."""

    font_size_value = NumericProperty(16)
    error_line = NumericProperty(0)   # 1-indexli; 0 = vurgu yok
    debug_line = NumericProperty(0)   # 1-indexli; 0 = vurgu yok
    breakpoints = ListProperty([])    # 1-indexli satır numaraları listesi

    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", spacing=4, **kwargs)

        self.gutter = LineNumberGutter(
            size_hint_x=None,
            width="44dp",
            font_size=self.font_size_value,
        )
        self.code_input = CodeInput(
            lexer=PythonLexer(),
            font_size=self.font_size_value,
        )

        self.add_widget(self.gutter)
        self.add_widget(self.code_input)

        self.code_input.bind(text=self._on_text_changed)
        self.code_input.bind(scroll_y=self._sync_gutter_scroll)
        self.bind(error_line=self._refresh_highlight)
        self.bind(debug_line=self._refresh_highlight)
        self.bind(breakpoints=lambda *a: self._refresh_gutter_text())

        self._refresh_gutter_text()

    # ---------------- Genel erişim yardımcıları ----------------

    def get_text(self):
        return self.code_input.text

    def set_text(self, value):
        self.code_input.text = value
        self._refresh_gutter_text()

    def set_font_size(self, size):
        self.font_size_value = size
        self.code_input.font_size = size
        self.gutter.font_size = size

    def set_pygments_style(self, style_name):
        try:
            self.code_input.style_name = style_name
        except Exception as e:
            print(f"[CodeEditor] tema uygulanamadı ({style_name}): {e}")

    def set_colors(self, bg, fg):
        try:
            self.code_input.background_color = bg
            self.code_input.foreground_color = fg
            self.gutter.foreground_color = fg
        except Exception as e:
            print(f"[CodeEditor] renkler uygulanamadı: {e}")

    def current_cursor_line(self):
        """İmlecin bulunduğu satırı 1-indexli döner."""
        return self.code_input.cursor_row + 1

    def toggle_breakpoint_at_cursor(self):
        """İmlecin olduğu satırda breakpoint varsa kaldırır, yoksa ekler.
        (satir_no, artik_aktif_mi) döner."""
        line = self.current_cursor_line()
        bps = set(self.breakpoints)
        if line in bps:
            bps.discard(line)
            active = False
        else:
            bps.add(line)
            active = True
        self.breakpoints = sorted(bps)
        return line, active

    def clear_run_markers(self):
        """Yeni bir çalıştırma başlarken önceki hata/duraklama vurgusunu temizler."""
        self.error_line = 0
        self.debug_line = 0

    # ---------------- İç mekanizma ----------------

    def _on_text_changed(self, instance, value):
        self._refresh_gutter_text()

    def _sync_gutter_scroll(self, instance, value):
        # Gutter ve ana editör aynı font/padding ayarlarını paylaştığı için
        # scroll_y değerini doğrudan kopyalamak ikisini senkron tutar.
        self.gutter.scroll_y = value

    def _refresh_gutter_text(self, *args):
        line_count = max(1, self.code_input.text.count("\n") + 1)
        bps = set(self.breakpoints)
        rows = []
        for i in range(1, line_count + 1):
            marker = "●" if i in bps else " "
            rows.append(f"{marker}{i}")
        new_text = "\n".join(rows)
        if self.gutter.text != new_text:
            self.gutter.text = new_text

    def _refresh_highlight(self, *args):
        ci = self.code_input
        target_line = self.debug_line or self.error_line
        text_lines = ci.text.split("\n")

        if not target_line or target_line < 1 or target_line > len(text_lines):
            ci.cancel_selection()
            return

        idx = target_line - 1
        start = sum(len(l) + 1 for l in text_lines[:idx])  # +1 -> '\n' karakteri
        end = start + len(text_lines[idx])

        if self.debug_line:
            ci.selection_color = (1, 0.85, 0.2, 0.45)  # sarı: şu an duraklatıldığı satır
        else:
            ci.selection_color = (1, 0.15, 0.15, 0.45)  # kırmızı: hata satırı

        try:
            ci.select_text(start, end)
        except Exception as e:
            print(f"[CodeEditor] satır vurgulanamadı: {e}")
