"""
Depodaki program/ (ve varsa kok/) dosyalarindan surum.json uretir.
Kullanim:  python araclar/manifest_yap.py 1.5.2 "not 1" "not 2"
Uygulama (program/github_kanal.py) bu dosyayi okur; sadece parmak izi degisen dosyalari indirir.
"""
import datetime, hashlib, json, os, sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATLA = {"program/surum.txt"}


def main():
    if len(sys.argv) < 2:
        sys.exit("Kullanim: manifest_yap.py SURUM [notlar...]")
    dosyalar = {}
    for alan in ("program", "kok"):
        for kok, klasorler, adlar in os.walk(os.path.join(KOK, alan)):
            klasorler[:] = [k for k in klasorler if k != "__pycache__"]
            for ad in adlar:
                tam = os.path.join(kok, ad)
                goreli = os.path.relpath(tam, KOK).replace(os.sep, "/")
                if goreli in ATLA or ad.endswith(".pyc"):
                    continue
                with open(tam, "rb") as f:
                    dosyalar[goreli] = hashlib.sha256(f.read()).hexdigest()
    man = {"surum": sys.argv[1], "tarih": datetime.date.today().isoformat(),
           "notlar": sys.argv[2:], "dosyalar": dict(sorted(dosyalar.items()))}
    with open(os.path.join(KOK, "surum.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
    print(f"surum.json yazildi: v{man['surum']}, {len(dosyalar)} dosya")


if __name__ == "__main__":
    main()
