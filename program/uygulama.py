"""
Bidik Studyo masaustu uygulamasi.

Paneli kendi penceresinde acar (pywebview / Microsoft Edge WebView2).
pywebview kurulamadiysa Edge'i "uygulama modunda" (adres cubugu olmadan) acar;
bu modda pencere kapaninca program da kendiliginden kapanir.
"""
import os, sys, time, socket, threading, subprocess, urllib.request

PROGRAM = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(PROGRAM)
LOG = os.path.join(KOK, "bidik.log")

# pythonw ile acilinca konsol yok: ciktilari log dosyasina yaz
if sys.stdout is None or sys.stderr is None or "--log" in sys.argv:
    _log = open(LOG, "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = _log
    print(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} acildi ---")

sys.path.insert(0, PROGRAM)
import panel  # noqa: E402

URL = f"http://127.0.0.1:{panel.PORT}/"
ICO = os.path.join(PROGRAM, "bidik.ico")


def sunucu_cevap_veriyor():
    try:
        urllib.request.urlopen(URL + "api/durum", timeout=1.5)
        return True
    except Exception:
        return False


def port_bos():
    s = socket.socket()
    if not sys.platform.startswith("win"):
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", panel.PORT))
        return True
    except OSError:
        return False
    finally:
        s.close()


def mesaj_kutusu(metin):
    if sys.platform.startswith("win"):
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, metin, "Bıdık Stüdyo", 0x40)
    else:
        print(metin)


def sunucuyu_baslat():
    """Sunucu zaten calisiyorsa (ikinci kez acilis) onu kullanir."""
    if "--yeniden" in sys.argv:   # guncelleme sonrasi: eski surecin kapanmasini bekle
        for _ in range(40):
            if port_bos():
                break
            time.sleep(0.25)
    elif sunucu_cevap_veriyor():
        return False
    for deneme in range(20):
        try:
            sunucu = panel.sunucu_olustur()
            break
        except OSError:
            time.sleep(0.5)
    else:
        mesaj_kutusu("Bıdık Stüdyo başlatılamadı: 8765 portu kullanımda.\n"
                     "Bilgisayarı yeniden başlatıp tekrar dene.")
        sys.exit(1)
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    return True


def pywebview_ile(sahip):
    import webview
    if sys.platform.startswith("win"):
        try:  # gorev cubugunda Python yerine kendi simgemiz
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Bidik.Studyo")
        except Exception:
            pass
    from ortak import ayarlar
    arka = "#14151D" if ayarlar().get("tema", "koyu") == "koyu" else "#FAF4E6"
    pencere = webview.create_window("Bıdık Stüdyo", URL, width=1320, height=900,
                                    min_size=(900, 600), background_color=arka)
    panel.KAPAT["fonk"] = pencere.destroy

    def ikon():
        try:
            from System.Drawing import Icon
            from System import Action
            f = pencere.native
            f.Invoke(Action(lambda: setattr(f, "Icon", Icon(ICO))))
        except Exception as e:
            print("ikon ayarlanamadi:", e)
    pencere.events.shown += ikon
    try:
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    except Exception:
        pass
    webview.start(gui="edgechromium")   # WebView2 yoksa hata verir -> Edge moduna gecilir
    os._exit(0)   # pencere kapandi: arka plandaki sunucuyu da kapat


def edge_bul():
    adaylar = [os.path.join(os.environ.get(v, ""), r"Microsoft\Edge\Application\msedge.exe")
               for v in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
    return next((a for a in adaylar if os.path.exists(a)), None)


def edge_ile(sahip):
    edge = edge_bul()
    if "--yeniden" in sys.argv:
        pass   # acik Edge penceresi kendini yeniler, yeni pencere acma
    elif not edge:
        import webbrowser
        webbrowser.open(URL)
    else:
        profil = os.path.join(KOK, ".edge_profil")
        subprocess.Popen([edge, f"--app={URL}", f"--user-data-dir={profil}",
                          "--window-size=1320,900", "--no-first-run"])
    if not sahip:
        return
    # pencere kapaninca (nabiz kesilince) programi kapat
    baslangic = time.time()
    while True:
        time.sleep(3)
        son = panel.NABIZ["son"]
        if panel.IS["calisiyor"]:
            continue
        if son is None and time.time() - baslangic > 120:
            os._exit(0)
        if son is not None and time.time() - son > 15:
            os._exit(0)


def main():
    sahip = sunucuyu_baslat()
    try:
        import webview  # noqa: F401
        pywebview_ile(sahip)
    except ImportError:
        print("pywebview yok, Edge uygulama modu kullaniliyor")
        edge_ile(sahip)
    except Exception as e:
        print("pywebview acilamadi, Edge uygulama modu kullaniliyor:", e)
        edge_ile(sahip)


if __name__ == "__main__":
    main()
