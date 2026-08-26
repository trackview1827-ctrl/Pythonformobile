# PyRunner AI

Telefonunda çalışan, Kivy tabanlı bir Python kod çalıştırma / debug uygulaması.
Kod yaz, çalıştır, hata olursa satırını kırmızıyla gör, breakpoint koyup adım
adım ilerle, Gemini AI'dan hatanın ne olduğunu Türkçe açıklamasını iste.

## Özellikler

- **Kod editörü:** satır numaraları, Python söz dizimi renklendirme (Pygments)
- **5 tema:** Koyu (Monokai), Dracula, Açık, Solarized Light, Terminal
- **Yazı tipi boyutu ayarı** (Ayarlar ekranından, kaydırıcı ile)
- **Hata satırı kırmızı vurgu**, breakpoint'te duraklama satırı sarı vurgu
- **Breakpoint + adım adım (step) debug:** imleci bir satıra koy, "Breakpoint"
  butonuna bas, çalıştır; o satırda duraklar, yerel değişkenleri görürsün,
  "Adım" ile satır satır ilerleyebilirsin
- **pip install** (uygulama içinden, saf Python paketleri için — aşağıya bak)
- **Gemini AI ile hata analizi:** hata olunca çıkan "AI ile Analiz Et"
  butonuna basınca, hatanın sebebini ve çözümünü Türkçe açıklar

## ÖNEMLİ: APK'yı neden ben (Claude) derleyemedim

Bu kodu yazdığım ortamın **interneti yok** ve **Android SDK/NDK kurulu değil**.
APK derlemek (Buildozer ile) hem birkaç GB indirme hem de gerçek bir Android
derleme zinciri gerektiriyor — bunlardan hiçbiri bu ortamda mevcut değil. Bu
yüzden sana **derlemeye hazır, tam kodu** hazırladım ve aşağıda 3 farklı
şekilde APK'ya çevirebileceğin adımları anlattım. **Yöntem 1 (GitHub
Actions)** hem en kolay hem de en garantili olanı; bilgisayarına hiçbir şey
kurmana gerek yok.

Ayrıca dürüst olmak gerekirse: editördeki kırmızı/sarı satır vurgusu gibi
görsel detayları, ekranı göremediğim için birebir test edemedim (kodun mantığı
sağlam ama ilk denemede küçük bir görsel ayar gerekebilir). Buna karşılık,
**çalıştırma/debug motorunun kendisini** (breakpoint, step, hata satırı
bulma, çıktı yakalama) bu ortamda gerçek testlerle doğruladım — hepsi geçti
(bkz. `test_executor.py`).

## Yöntem 1 (Önerilen): GitHub Actions ile derleme

Bilgisayarına hiçbir şey kurmadan, bulutta ücretsiz derlenir.

1. [github.com](https://github.com) üzerinde yeni bir repo oluştur (public
   olabilir, private de olur).
2. Bu klasördeki **tüm dosyaları** (bu README dahil, `.github` klasörü ile
   birlikte) o repoya yükle (GitHub'ın web arayüzünden "Add file → Upload
   files" ile sürükle-bırak yapabilirsin, ya da `git push`).
3. Repo sayfasında **Actions** sekmesine git. "APK Derle" iş akışının
   otomatik başladığını göreceksin (dosyaları push ettiğin an tetiklenir).
   Başlamadıysa "Run workflow" butonuna manuel basabilirsin.
4. Derleme bitince (ilk derleme 15-25 dakika sürebilir; SDK/NDK indirmesi
   yüzünden), o çalışmanın sayfasında en altta **Artifacts** bölümünden
   `pyrunner-apk` dosyasını indir. İçinden çıkan `.apk` dosyasını telefonuna
   atıp kurabilirsin (kaynağı bilinmeyen uygulamalara izin vermen gerekebilir).

## Yöntem 2: Kendi bilgisayarında (Linux / WSL2)

Buildozer sadece Linux/Mac'te çalışır. Windows'taysan önce WSL2 kur.

```bash
sudo apt update && sudo apt install -y python3-pip build-essential git \
    openjdk-17-jdk unzip zip
pip3 install --user buildozer cython
cd pyrunner_app
buildozer -v android debug
```

İlk derleme Android SDK/NDK'yı indireceği için uzun sürer (30dk-1 saat+,
internetine göre değişir). Bittiğinde `bin/` klasöründe `.apk` dosyasını
bulursun.

## Yöntem 3: Termux (telefonun üzerinde) — deneysel

Bu, senin ilk aklına gelen yöntemdi ama dürüst olmak gerekirse buildozer
Termux üzerinde resmi olarak desteklenmiyor; NDK indirme/izin sorunları
yaşanabiliyor ve çok yavaş olabiliyor. Yine de denemek istersen:

```bash
pkg update && pkg install python git build-essential -y
pip install buildozer cython
cd pyrunner_app
buildozer -v android debug
```

Sorun yaşarsan Yöntem 1'e (GitHub Actions) geçmeni tavsiye ederim.

## Gemini API Key nasıl alınır

1. [aistudio.google.com/apikey](https://aistudio.google.com/apikey) adresine
   git, Google hesabınla giriş yap.
2. "Create API key" butonuna bas, key'i kopyala.
3. Uygulamada **Ayarlar** ekranına yapıştır, **Kaydet**'e bas.
4. Ücretsiz kullanım kotası var ama Google zaman zaman değiştirebiliyor;
   "model bulunamadı" hatası alırsan Ayarlar'daki "Gemini Model Adı" alanına
   güncel bir model adı yaz (bkz. ai.google.dev/gemini-api/docs/models).

## pip install hakkında dürüst bilgi

- **Çalışır:** saf Python paketleri — `requests`, `arrow`, `colorama`,
  `beautifulsoup4` gibi C derlemesi gerektirmeyenler.
- **Çalışmaz (telefonda):** `numpy`, `pandas`, `opencv-python`, `lxml` gibi
  C-uzantılı paketler — çünkü Android'de derleyici yok. Bunları kullanmak
  istersen `buildozer.spec` dosyasındaki `requirements` satırına ekleyip
  (örn. `requirements = python3,kivy,pygments,pip,numpy`) APK'yı yukarıdaki
  yöntemlerden biriyle **yeniden derlemen** gerekir — o zaman derleme
  makinesinde (GitHub Actions/bilgisayarın) derlenip APK'nın içine gömülür.

## Dosya yapısı

```
pyrunner_app/
├── main.py              # Kivy App, arayüz, buton bağlantıları
├── editor_widgets.py     # Satır numaralı/temalı kod editörü widget'ı
├── executor.py           # Çalıştırma + breakpoint/step + hata yakalama motoru
├── ai_helper.py          # Gemini API ile hata analizi
├── pip_manager.py        # Uygulama içi pip install
├── config_manager.py     # Ayarları diske kaydetme/okuma
├── themes.py             # Tema tanımları
├── test_executor.py       # executor.py için gerçek testler (9/9 geçiyor)
├── buildozer.spec         # APK derleme yapılandırması
├── .github/workflows/build.yml  # GitHub Actions ile otomatik derleme
└── README.md              # Bu dosya
```

## Kendi bilgisayarında motor testlerini çalıştırmak istersen

```bash
python3 test_executor.py
```

Kivy gerektirmez (sadece stdlib), her Python kurulu bilgisayarda çalışır.

## Bilinen sınırlamalar

- Editördeki kırmızı/sarı satır vurgusu ve breakpoint gutter'ı görsel olarak
  cihazda test edilmedi (yukarıda açıklandığı gibi); mantık doğru ama ince
  ayar gerekebilir.
- Breakpoint eklemek için kenar boşluğuna tıklamak yerine "imleci satıra
  koy + Breakpoint butonuna bas" yöntemi kullanılıyor (daha güvenilir).
- pip install, Android'de pip modülünün APK içine dahil edilmiş olmasına
  bağlıdır (buildozer.spec'te `pip` requirements'ta var, ama Android
  ortamında %100 her senaryoda çalışacağının garantisi yok — deneysel).
