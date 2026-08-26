# -*- coding: utf-8 -*-
"""
Uygulama içinden "pip install" imkânı sağlar.

ÖNEMLİ VE DÜRÜST SINIRLAMA:
Android'de derleyici (C/C++ toolchain) YOKTUR. Bu yüzden:
  - Saf Python paketleri (requests, colorama, beautifulsoup4, arrow, vb.)
    telefonun üzerinde runtime'da kurulabilir. -> Bu modül bunun içindir.
  - C-uzantılı paketler (numpy, pandas, opencv-python, lxml, vb.) telefonda
    KURULAMAZ çünkü derlenmeleri gerekir. Bunlar buildozer.spec dosyasındaki
    'requirements' satırına eklenip APK YENİDEN DERLENEREK dahil edilebilir
    (python-for-android'in kendi tarifleri/recipe'leri ile, derleme
    BİLGİSAYARDA/CI'da yapılır, telefonda değil).

Bu modül pip'in "private" (resmî olarak dışa açık olmayan) iç API'sini
(pip._internal.cli.main) kullanır çünkü modern pip artık genel bir
`pip.main()` fonksiyonu sunmuyor. Bu yaklaşım yaygın kullanılıyor olsa da
pip sürümüne göre küçük değişiklikler gösterebilir; bu yüzden import
başarısız olursa kullanıcıya anlamlı bir mesaj veriyoruz, sessizce
çökmüyoruz.
"""
import sys
import os
import io
import threading

_pip_lock = threading.Lock()


def _get_install_dir():
    """Paketlerin kurulacağı, uygulamaya özel, izin gerektirmeyen klasör."""
    base = "."
    try:
        from kivy.app import App
        app = App.get_running_app()
        if app is not None:
            base = app.user_data_dir
    except Exception:
        pass
    install_dir = os.path.join(base, "installed_packages")
    os.makedirs(install_dir, exist_ok=True)
    if install_dir not in sys.path:
        sys.path.insert(0, install_dir)
    return install_dir


def is_pip_available():
    try:
        import pip._internal.cli.main  # noqa: F401
        return True
    except Exception:
        return False


def install_package_async(package_name, on_output, on_done):
    """
    on_output(line: str) -> pip çıktısından bir satır geldi
    on_done(success: bool, message: str) -> işlem bitti
    """
    package_name = (package_name or "").strip()

    def worker():
        if not package_name:
            on_done(False, "Paket adı boş olamaz.")
            return

        if not _pip_lock.acquire(blocking=False):
            on_done(False, "Şu anda başka bir pip işlemi sürüyor, bitmesini bekle.")
            return

        try:
            install_dir = _get_install_dir()
            try:
                from pip._internal.cli.main import main as pip_main
            except Exception:
                on_done(
                    False,
                    "pip bu APK içine dahil edilmemiş görünüyor. buildozer.spec "
                    "dosyasındaki 'requirements' satırına 'pip' eklenip APK "
                    "yeniden derlenmeli.",
                )
                return

            args = ["install", "--target", install_dir, "--no-cache-dir", "--disable-pip-version-check", package_name]

            class _Tee(io.TextIOBase):
                def writable(self_inner):
                    return True

                def write(self_inner, s):
                    if s:
                        for line in s.splitlines():
                            if line.strip():
                                on_output(line)
                    return len(s)

                def flush(self_inner):
                    pass

            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = _Tee()
            ret_code = 1
            try:
                ret_code = pip_main(args)
            except SystemExit as e:
                ret_code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
            finally:
                sys.stdout, sys.stderr = old_out, old_err

            if ret_code == 0:
                on_done(True, f"'{package_name}' kuruldu.")
            else:
                on_done(
                    False,
                    f"'{package_name}' kurulamadı (çıkış kodu {ret_code}). Bu paket "
                    f"muhtemelen derleme (C-extension) gerektiriyor; bu tür paketleri "
                    f"buildozer.spec 'requirements' satırına ekleyip APK'yı yeniden "
                    f"derlemen gerekir.",
                )
        except Exception as e:
            on_done(False, f"Beklenmeyen hata: {e}")
        finally:
            _pip_lock.release()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t
