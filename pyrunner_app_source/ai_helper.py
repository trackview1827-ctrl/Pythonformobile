# -*- coding: utf-8 -*-
"""
Gemini API kullanarak hata (traceback) analizi yapan modül.

Not: Google zaman zaman model isimlerini değiştirip eskilerini emekliye
ayırabiliyor. Bu yüzden model adı sabit kodlanmadı; Ayarlar ekranından
değiştirilebilir. Güncel model listesi için:
https://ai.google.dev/gemini-api/docs/models

Bu dosya da (pip_manager/editor hariç) Kivy'ye bağımlı değildir; sadece
stdlib (urllib, json, threading) kullanır, böylece network olmadan bile
prompt üretimi ve hata-dallanma mantığı test edilebilir.
"""
import json
import threading
import urllib.request
import urllib.error

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-2.5-flash"
REQUEST_TIMEOUT_SECONDS = 30


def build_prompt(code, traceback_text):
    """Gemini'ye gönderilecek istemi (prompt) üretir. Test edilebilmesi için
    ağ çağrısından ayrı, saf bir fonksiyon olarak tutuldu."""
    return (
        "Aşağıda bir Python kodu ve çalıştırılınca aldığı hatanın (traceback) "
        "tam metni var. Görevin:\n"
        "1) Hatanın kök sebebini Türkçe, açık ve kısa şekilde anlat (en fazla 4-5 cümle).\n"
        "2) Nasıl düzeltileceğine dair kısa, maddeler halinde somut öneriler ver.\n"
        "Kodun tamamını tekrar yazma; sadece açıklama ve öneri yaz.\n\n"
        f"--- KOD ---\n{code}\n\n"
        f"--- HATA (traceback) ---\n{traceback_text}\n"
    )


def _parse_response_body(body):
    """Gemini yanıt JSON'undan düz metni çıkarır. Hata durumunda anlaşılır
    bir RuntimeError fırlatır (ham JSON'u kullanıcıya göstermek yerine)."""
    candidates = body.get("candidates", [])
    if not candidates:
        feedback = body.get("promptFeedback", {})
        block_reason = feedback.get("blockReason")
        if block_reason:
            raise RuntimeError(f"Gemini isteği reddetti (sebep: {block_reason}).")
        raise RuntimeError("Gemini boş yanıt döndürdü (candidates listesi boş).")

    try:
        parts = candidates[0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"Yanıt beklenmeyen formatta, ayrıştırılamadı: {e}")

    return text.strip() or "Gemini boş bir açıklama döndürdü."


def call_gemini_sync(code, traceback_text, api_key, model=DEFAULT_MODEL):
    """Gemini API'ye SENKRON (bloklayan) istek atar. UI thread'inden DEĞİL,
    her zaman bir arka plan thread'inden çağrılmalı (bkz. analyze_error_async)."""
    if not api_key:
        raise ValueError("Gemini API key girilmemiş. Ayarlar ekranından ekleyebilirsin.")
    if not model:
        model = DEFAULT_MODEL

    url = GEMINI_ENDPOINT.format(model=model)
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": build_prompt(code, traceback_text)}]}
        ]
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        if e.code == 404:
            raise RuntimeError(
                f"Model bulunamadı: '{model}'. Google model adını değiştirmiş "
                f"olabilir. Ayarlar'dan güncel bir model adı dene "
                f"(bkz. ai.google.dev/gemini-api/docs/models)."
            )
        elif e.code in (401, 403):
            raise RuntimeError(
                "API key reddedildi (401/403). Ayarlar'dan key'ini kontrol et."
            )
        elif e.code == 429:
            raise RuntimeError(
                "Ücretsiz kullanım kotası aşıldı (429). Biraz bekleyip tekrar dene."
            )
        else:
            raise RuntimeError(f"Gemini API hatası (kod {e.code}): {detail[:200]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"İnternet bağlantısı sorunu: {e.reason}")

    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError("Gemini yanıtı JSON olarak ayrıştırılamadı.")

    return _parse_response_body(body)


def analyze_error_async(code, traceback_text, api_key, model, on_result, on_error):
    """Arka planda thread açıp Gemini'ye sorar. Sonucu ana thread'e TAŞIMAZ;
    main.py bu callback'leri Clock.schedule_once ile sarmalıdır (Kivy widget'
    güncellemesi ana thread dışında yapılmamalı)."""

    def worker():
        try:
            text = call_gemini_sync(code, traceback_text, api_key, model)
            on_result(text)
        except Exception as e:
            on_error(str(e))

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t
