"""
Telefondan erisim yardimcilari (Windows).

- Tailscale "serve": paneli internete ACMADAN, sadece Deniz'in Tailscale agindaki cihazlarina
  https://<bilgisayar>.<ag>.ts.net/ adresiyle sunar (sertifikayi Tailscale verir).
- Otomatik baslatma: Windows "Baslangic" klasorune arka plan kisayolu koyar/kaldirir.
- Uyku engelleme: uygulama calistigi surece bilgisayarin uykuya gecmesini engeller
  (sistem ayari degistirilmez; uygulama kapaninca kendiliginden biter).
"""
import json, os, re, shutil, subprocess, sys

from ortak import KOK, PROGRAM, PENCERESIZ

PORT = 8765
KISAYOL_ADI = "Bidik Studyo (arka plan).lnk"


# --- Tailscale -----------------------------------------------------------------
def tailscale_yolu():
    yol = shutil.which("tailscale")
    if yol:
        return yol
    for v in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        aday = os.path.join(os.environ.get(v, ""), "Tailscale", "tailscale.exe")
        if os.path.exists(aday):
            return aday
    return None


def _ts(args, sure=15):
    ts = tailscale_yolu()
    if not ts:
        raise RuntimeError("Tailscale kurulu degil")
    try:
        s = subprocess.run([ts] + args, capture_output=True, text=True, timeout=sure,
                           creationflags=PENCERESIZ, encoding="utf-8", errors="ignore")
        return s.returncode, (s.stdout or "") + (s.stderr or "")
    except subprocess.TimeoutExpired as e:
        cikti = e.stdout or b""
        cikti = cikti.decode("utf-8", "ignore") if isinstance(cikti, bytes) else cikti
        return -1, cikti


def tailscale_durum():
    """{"kurulu", "bagli", "ad", "url", "yayinda", "mesaj"}"""
    d = {"kurulu": bool(tailscale_yolu()), "bagli": False, "ad": "", "url": "", "yayinda": False, "mesaj": ""}
    if not d["kurulu"]:
        d["mesaj"] = "Tailscale bu bilgisayarda kurulu degil."
        return d
    kod, cikti = _ts(["status", "--json"], 10)
    try:
        st = json.loads(cikti[cikti.find("{"):])
    except ValueError:
        d["mesaj"] = "Tailscale durumu okunamadi: " + cikti.strip()[:160]
        return d
    d["bagli"] = st.get("BackendState") == "Running"
    ad = ((st.get("Self") or {}).get("DNSName") or "").rstrip(".")
    d["ad"] = ad
    if not d["bagli"]:
        d["mesaj"] = "Tailscale acik degil ya da giris yapilmadi (sag alttaki Tailscale simgesinden giris yap)."
        return d
    if ad:
        d["url"] = f"https://{ad}/"
    kod, cikti = _ts(["serve", "status", "--json"], 10)
    d["yayinda"] = str(PORT) in cikti
    return d


def tailscale_ac():
    """Paneli Tailscale agina HTTPS ile sunar. Onay gerekiyorsa onay baglantisini dondurur."""
    kod, cikti = _ts(["serve", "--bg", f"http://127.0.0.1:{PORT}"], 25)
    if kod != 0 and "login.tailscale.com" not in cikti and re.search(r"(?i)usage|invalid|unknown|flag", cikti):
        # eski Tailscale surumlerinin soz dizimi
        kod, cikti = _ts(["serve", "https", "/", f"http://127.0.0.1:{PORT}"], 25)
    onay = re.search(r"https://login\.tailscale\.com/\S+", cikti)
    d = tailscale_durum()
    if onay and not d["yayinda"]:
        d["onay_url"] = onay.group(0).rstrip(".,)")
        d["mesaj"] = ("Tailscale, aginda HTTPS'i bir kez onaylamani istiyor. Asagidaki baglantiyi ac, "
                      "'Enable' de, sonra bu dugmeye tekrar bas.")
    elif not d["yayinda"]:
        d["mesaj"] = "Acilamadi: " + (cikti.strip()[-300:] or "Tailscale cevap vermedi")
    return d


def tailscale_kapat():
    _ts(["serve", "reset"], 15)
    return tailscale_durum()


# --- otomatik baslatma ---------------------------------------------------------
def _baslangic_klasoru():
    return os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")


def _pythonw():
    py = sys.executable
    if py.lower().endswith("python.exe"):
        aday = py[:-len("python.exe")] + "pythonw.exe"
        if os.path.exists(aday):
            return aday
    return py


def otomatik_baslat_var():
    return os.path.exists(os.path.join(_baslangic_klasoru(), KISAYOL_ADI))


def otomatik_baslat(acik):
    if not sys.platform.startswith("win"):
        return False
    lnk = os.path.join(_baslangic_klasoru(), KISAYOL_ADI)
    if not acik:
        if os.path.exists(lnk):
            os.remove(lnk)
        return False
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:BIDIK_LNK);"
        "$s.TargetPath=$env:BIDIK_PY;$s.Arguments=$env:BIDIK_ARG;$s.WorkingDirectory=$env:BIDIK_KOK;"
        "$s.IconLocation=$env:BIDIK_ICO;$s.Description='Bidik Studyo arka plan';$s.Save()"
    )
    ortam = dict(os.environ, BIDIK_LNK=lnk, BIDIK_PY=_pythonw(),
                 BIDIK_ARG=f'"{os.path.join(PROGRAM, "uygulama.py")}" --arka', BIDIK_KOK=KOK,
                 BIDIK_ICO=os.path.join(PROGRAM, "bidik.ico"))
    s = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                       capture_output=True, text=True, env=ortam, creationflags=PENCERESIZ)
    if s.returncode != 0 or not os.path.exists(lnk):
        raise RuntimeError("Baslangic kisayolu olusturulamadi: " + (s.stderr or "")[-200:])
    return True


# --- uyku engelleme -------------------------------------------------------------
def uyku_engelle(acik=True):
    """Cagiran is parcacigi yasadigi surece gecerlidir (ana is parcacigindan cagir)."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if acik else 0))
    except Exception as e:
        print("uyku engellenemedi:", e)
