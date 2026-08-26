# -*- coding: utf-8 -*-
"""
Kullanıcının Python kodunu ayrı bir thread'de çalıştıran, satır satır izleyen
(sys.settrace), breakpoint'lerde durabilen ve tam hata (traceback) bilgisini
kullanıcı kodundaki doğru satıra eşleyen motor.

ÖNEMLİ TASARIM NOTU: Bu dosya kasıtlı olarak Kivy'den tamamen bağımsızdır
(sadece stdlib kullanır). Böylece hem masaüstünde/CI'da gerçek testler
yazılabilir hem de ileride farklı bir arayüzle (örn. terminal) yeniden
kullanılabilir. Kivy tarafındaki main.py, buradaki callback'leri
Clock.schedule_once ile ana thread'e taşımakla yükümlüdür.
"""
import sys
import io
import threading
import traceback
import builtins

USER_CODE_FILENAME = "<kullanici_kodu>"


class _CallbackStream(io.TextIOBase):
    """print() / stdout çıktısını bir callback'e yönlendiren basit stream."""

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def writable(self):
        return True

    def write(self, s):
        if s:
            self._callback(s)
        return len(s)

    def flush(self):
        pass


class ExecutionController:
    """Tek seferde bir kod çalıştırma oturumunu yönetir."""

    def __init__(self, on_output, on_line_change, on_paused, on_finished, on_error):
        """
        on_output(text: str)                                -> çıktı parçası geldi
        on_line_change(line_no: int)                        -> şu an çalışan satır değişti
        on_paused(line_no: int, local_vars: dict[str, str])  -> breakpoint/step'te durdu
        on_finished()                                        -> normal/durduruldu bitiş
        on_error(line_no: int, short_msg: str, full_tb: str) -> yakalanmamış hata
        """
        self.on_output = on_output
        self.on_line_change = on_line_change
        self.on_paused = on_paused
        self.on_finished = on_finished
        self.on_error = on_error

        self.breakpoints = set()
        self._thread = None
        self._stop_requested = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._step_mode = False
        self._running = False
        self._last_line = None

    # ---------- Dışa açık kontrol API'si ----------

    def is_running(self):
        return self._running

    def set_breakpoints(self, line_numbers):
        self.breakpoints = set(line_numbers)

    def run(self, code_text):
        if self._running:
            return False
        self._stop_requested.clear()
        self._pause_event.set()
        self._step_mode = False
        self._running = True
        self._last_line = None
        self._thread = threading.Thread(
            target=self._run_worker, args=(code_text,), daemon=True
        )
        self._thread.start()
        return True

    def stop(self):
        """Çalışan kodu güvenli şekilde kesmeye çalışır (bir sonraki satıra
        geçildiğinde etkili olur; anlık/çok uzun tek satırlık işlemleri
        yarıda kesemez, bu CPython'un bir kısıtıdır)."""
        self._stop_requested.set()
        self._pause_event.set()

    def resume(self):
        self._step_mode = False
        self._pause_event.set()

    def step(self):
        self._step_mode = True
        self._pause_event.set()

    # ---------- İç mekanizma ----------

    def _trace(self, frame, event, arg):
        if self._stop_requested.is_set():
            raise KeyboardInterrupt("durduruldu")

        if frame.f_code.co_filename != USER_CODE_FILENAME:
            return None  # kütüphane/iç kod: adım adım izleme

        if event == "line":
            line_no = frame.f_lineno
            self._last_line = line_no
            self.on_line_change(line_no)

            if self._step_mode or line_no in self.breakpoints:
                local_vars = {}
                for k, v in frame.f_locals.items():
                    if k.startswith("__"):
                        continue
                    try:
                        local_vars[k] = repr(v)[:200]
                    except Exception:
                        local_vars[k] = "<repr alınamadı>"
                self._pause_event.clear()
                self.on_paused(line_no, local_vars)
                self._pause_event.wait()
                if self._stop_requested.is_set():
                    raise KeyboardInterrupt("durduruldu")

        return self._trace

    def _run_worker(self, code_text):
        out_stream = _CallbackStream(self.on_output)
        old_stdout, old_stderr = sys.stdout, sys.stderr
        old_trace = sys.gettrace()
        sys.stdout = out_stream
        sys.stderr = out_stream
        try:
            try:
                compiled = compile(code_text, USER_CODE_FILENAME, "exec")
            except SyntaxError as e:
                line_no = e.lineno or 0
                msg = f"Söz dizimi hatası (SyntaxError): {e.msg} (satır {line_no})"
                self.on_error(line_no, msg, traceback.format_exc())
                return

            exec_globals = {"__name__": "__main__", "__builtins__": builtins}
            sys.settrace(self._trace)
            try:
                exec(compiled, exec_globals)
            finally:
                sys.settrace(old_trace)

            if not self._stop_requested.is_set():
                self.on_finished()
            else:
                self.on_output("\n[Kullanıcı tarafından durduruldu]\n")
                self.on_finished()

        except KeyboardInterrupt:
            self.on_output("\n[Kullanıcı tarafından durduruldu]\n")
            self.on_finished()
        except Exception:
            tb_text = traceback.format_exc()
            line_no = self._extract_user_line(sys.exc_info()[2]) or self._last_line or 0
            short = self._short_error_message(tb_text)
            self.on_error(line_no, short, tb_text)
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
            self._running = False
            self._pause_event.set()

    @staticmethod
    def _short_error_message(tb_text):
        stripped = tb_text.strip().splitlines()
        return stripped[-1] if stripped else "Bilinmeyen hata"

    @staticmethod
    def _extract_user_line(tb):
        """Traceback zincirinde kullanıcı koduna ait EN İÇTEKİ (en derin) satırı bulur."""
        line_no = None
        while tb is not None:
            if tb.tb_frame.f_code.co_filename == USER_CODE_FILENAME:
                line_no = tb.tb_lineno
            tb = tb.tb_next
        return line_no
