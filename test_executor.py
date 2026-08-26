# -*- coding: utf-8 -*-
"""executor.py için gerçek (mock olmayan) testler."""
import time
import threading
from executor import ExecutionController


def run_and_wait(code, breakpoints=None, timeout=5, on_paused_action=None):
    """Bir kodu çalıştırır, bitene kadar bekler, sonucu dict olarak döner.
    on_paused_action(controller, line_no, local_vars) verilirse her pause'da çağrılır
    (step/resume kararını test senaryosu verir)."""
    result = {
        "output": [],
        "errors": [],
        "finished": threading.Event(),
        "paused_lines": [],
        "line_changes": [],
    }

    def on_output(text):
        result["output"].append(text)

    def on_line_change(line_no):
        result["line_changes"].append(line_no)

    def on_paused(line_no, local_vars):
        result["paused_lines"].append((line_no, local_vars))
        if on_paused_action:
            on_paused_action(ctrl, line_no, local_vars)
        else:
            ctrl.resume()

    def on_finished():
        result["finished"].set()

    def on_error(line_no, short_msg, full_tb):
        result["errors"].append((line_no, short_msg, full_tb))
        result["finished"].set()  # main.py'de de: hata = oturumun bitmesi demektir

    ctrl = ExecutionController(on_output, on_line_change, on_paused, on_finished, on_error)
    if breakpoints:
        ctrl.set_breakpoints(breakpoints)
    ctrl.run(code)
    finished_in_time = result["finished"].wait(timeout)
    result["timed_out"] = not finished_in_time
    result["ctrl"] = ctrl
    return result


# ---------------- TEST 1: basit çalıştırma + stdout yakalama ----------------
def test_basic_output():
    code = "print('merhaba')\nprint(1 + 2)\n"
    r = run_and_wait(code)
    assert not r["timed_out"], "zaman aşımı"
    assert not r["errors"], f"hata bekleniyordu yok ama var: {r['errors']}"
    full_output = "".join(r["output"])
    assert "merhaba" in full_output
    assert "3" in full_output
    print("TEST 1 OK: temel çıktı yakalama çalışıyor ->", repr(full_output))


# ---------------- TEST 2: runtime hata - doğru satır numarası ----------------
def test_runtime_error_line_number():
    code = (
        "x = 1\n"          # satır 1
        "y = 2\n"          # satır 2
        "z = x / 0\n"      # satır 3 <- hata burada
        "print('buraya gelmemeli')\n"
    )
    r = run_and_wait(code)
    assert not r["timed_out"]
    assert len(r["errors"]) == 1, r["errors"]
    line_no, short_msg, tb = r["errors"][0]
    assert line_no == 3, f"beklenen satır 3, bulunan {line_no}"
    assert "ZeroDivisionError" in short_msg
    print("TEST 2 OK: runtime hata satır numarası doğru ->", line_no, short_msg)


# ---------------- TEST 3: syntax hata - doğru satır numarası ----------------
def test_syntax_error_line_number():
    code = (
        "x = 1\n"
        "if x == 1\n"   # satır 2 <- eksik ':'
        "    print(x)\n"
    )
    r = run_and_wait(code)
    assert not r["timed_out"]
    assert len(r["errors"]) == 1, r["errors"]
    line_no, short_msg, tb = r["errors"][0]
    assert line_no == 2, f"beklenen satır 2, bulunan {line_no}"
    assert "SyntaxError" in short_msg
    print("TEST 3 OK: syntax hata satır numarası doğru ->", line_no, short_msg)


# ---------------- TEST 4: iç içe fonksiyon çağrısında hata satırı ----------------
def test_error_inside_user_function():
    code = (
        "def bol(a, b):\n"     # satır 1
        "    return a / b\n"   # satır 2 <- gerçek hata burada (en içteki kullanıcı satırı)
        "\n"
        "print('basliyor')\n"  # satır 4
        "bol(10, 0)\n"         # satır 5 <- çağrı burada
    )
    r = run_and_wait(code)
    assert not r["timed_out"]
    assert len(r["errors"]) == 1, r["errors"]
    line_no, short_msg, tb = r["errors"][0]
    assert line_no == 2, f"beklenen satır 2 (fonksiyon içi), bulunan {line_no}"
    print("TEST 4 OK: iç içe fonksiyonda EN DERİN kullanıcı satırı bulundu ->", line_no)


# ---------------- TEST 5: kütüphane çağrısında hata -> çağrı satırına düşmeli ----------------
def test_error_inside_library_call():
    code = (
        "import json\n"                  # satır 1
        "print('basliyor')\n"             # satır 2
        "json.loads('{bozuk json')\n"     # satır 3 <- kütüphane içinde patlar ama çağrı burada
    )
    r = run_and_wait(code)
    assert not r["timed_out"]
    assert len(r["errors"]) == 1, r["errors"]
    line_no, short_msg, tb = r["errors"][0]
    assert line_no == 3, f"beklenen satır 3 (çağrı satırı), bulunan {line_no}"
    print("TEST 5 OK: kütüphane hatasında çağrı satırı doğru bulundu ->", line_no)


# ---------------- TEST 6: breakpoint'te durma + devam etme + local değişkenler ----------------
def test_breakpoint_pause_and_resume():
    code = (
        "toplam = 0\n"          # 1
        "for i in range(3):\n"  # 2
        "    toplam += i\n"     # 3  <- breakpoint burada
        "print(toplam)\n"       # 4
    )
    captured_locals = []

    def on_pause_action(ctrl, line_no, local_vars):
        captured_locals.append(dict(local_vars))
        ctrl.resume()

    r = run_and_wait(code, breakpoints={3}, on_paused_action=on_pause_action)
    assert not r["timed_out"]
    assert not r["errors"], r["errors"]
    # range(3) -> 0,1,2 : satır 3'te 3 kere durmalı
    assert len(r["paused_lines"]) == 3, f"3 kere durması bekleniyordu: {r['paused_lines']}"
    assert all(ln == 3 for ln, _ in r["paused_lines"])
    # local değişkenler doğru yakalanmış mı (en az bir tanesinde i=1 falan olmalı)
    i_values = [lv.get("i") for lv in captured_locals]
    assert "0" in i_values and "1" in i_values and "2" in i_values, i_values
    full_output = "".join(r["output"])
    assert "3" in full_output  # toplam = 0+1+2 = 3
    print("TEST 6 OK: breakpoint 3 kez durdu, local değişkenler doğru ->", captured_locals)


# ---------------- TEST 7: step modu (tek tek ilerleme) ----------------
def test_step_mode():
    code = (
        "a = 1\n"  # 1
        "b = 2\n"  # 2
        "c = a + b\n"  # 3
    )
    lines_seen_while_stepping = []

    def on_pause_action(ctrl, line_no, local_vars):
        lines_seen_while_stepping.append(line_no)
        ctrl.step()  # her durakta bir sonraki satıra adım at

    # breakpoint olarak ilk satırı koyup step ile devam edeceğiz
    r = run_and_wait(code, breakpoints={1}, on_paused_action=on_pause_action)
    assert not r["timed_out"]
    assert not r["errors"], r["errors"]
    assert lines_seen_while_stepping == [1, 2, 3], lines_seen_while_stepping
    print("TEST 7 OK: step modu satır satır ilerledi ->", lines_seen_while_stepping)


# ---------------- TEST 8: durdurma (stop) ----------------
def test_stop_execution():
    code = (
        "toplam = 0\n"
        "for i in range(1000000):\n"
        "    toplam += i\n"
        "print('bitti', toplam)\n"
    )
    stopped_holder = {}

    def on_pause_action(ctrl, line_no, local_vars):
        # ilk durakta hemen durdur
        stopped_holder["ctrl"] = ctrl
        ctrl.stop()

    r = run_and_wait(code, breakpoints={3}, on_paused_action=on_pause_action, timeout=10)
    assert not r["timed_out"], "durdurma zaman aşımına uğradı, stop mekanizması çalışmıyor olabilir"
    full_output = "".join(r["output"])
    assert "bitti" not in full_output, "durdurulmasına rağmen kod sonuna kadar çalışmış"
    assert "durduruldu" in full_output.lower()
    print("TEST 8 OK: stop() çalışıyor, döngü yarıda kesildi ->", repr(full_output))


# ---------------- TEST 9: art arda iki çalıştırma (state sızıntısı olmamalı) ----------------
def test_sequential_runs_no_state_leak():
    r1 = run_and_wait("print('birinci')\n")
    assert not r1["errors"]
    r2 = run_and_wait("raise ValueError('ikinci')\n")
    assert len(r2["errors"]) == 1
    r3 = run_and_wait("print('ucuncu')\n")
    assert not r3["errors"]
    assert "ucuncu" in "".join(r3["output"])
    print("TEST 9 OK: ardışık çalıştırmalar birbirini etkilemiyor")


if __name__ == "__main__":
    tests = [
        test_basic_output,
        test_runtime_error_line_number,
        test_syntax_error_line_number,
        test_error_inside_user_function,
        test_error_inside_library_call,
        test_breakpoint_pause_and_resume,
        test_step_mode,
        test_stop_execution,
        test_sequential_runs_no_state_leak,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"BAŞARISIZ: {t.__name__} -> {e}")
        except Exception as e:
            failed += 1
            print(f"HATA (test kodu bile patladı): {t.__name__} -> {type(e).__name__}: {e}")
    print("\n" + "=" * 50)
    if failed == 0:
        print(f"HEPSİ BAŞARILI ({len(tests)}/{len(tests)})")
    else:
        print(f"{failed} test başarısız, {len(tests) - failed}/{len(tests)} başarılı")
