[app]

title = PyRunner AI
package.name = pyrunnerai
package.domain = org.pyrunner

source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1

# python3 ve kivy zorunlu. pygments -> kod renklendirme (editorde). pip -> uygulama
# icinden "pip install" yapabilmek icin (sadece saf Python paketleri calisir).
# requests EKLENMEDI cunku ai_helper.py sadece stdlib (urllib) kullaniyor.
requirements = python3,kivy==2.3.0,pygments,pip

orientation = portrait
fullscreen = 0

# Internet: Gemini API cagrilari ve pip install icin gerekli.
android.permissions = INTERNET

android.api = 34
android.minapi = 21
# android.ndk kasten belirtilmedi: buildozer, kullandigi p4a/NDK surumuyle
# uyumlu güncel bir varsayilan secsin diye (sabit bir surum yazarsak ileride
# buildozer guncellenince uyumsuzluk/derleme hatasi riski olusabilir).
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True

# Klavye acildiginda inputu ekrandan itsin (asagi kaydirmasin)
android.softinput_mode = below_target

[buildozer]
log_level = 2
# Allow running as root in CI containers without interactive prompt
warn_on_root = 0
