"""Télécharge la base GeoLite2-Country (MaxMind) dans backend/data/.

Usage :
    export SDH_MAXMIND_LICENSE_KEY=VOTRE_CLE
    python3 scripts/download_geolite.py

La clé est gratuite : https://www.maxmind.com/en/accounts/current/license-key
("Generate new license key" — affichée une seule fois, notez-la).
"""
from __future__ import annotations

import os
import sys
import tarfile
import tempfile
from pathlib import Path

import httpx

BASE_URL = "https://download.maxmind.com/app/geoip_download"
EDITION = "GeoLite2-Country"
TARGET = Path(__file__).resolve().parent.parent / "data" / f"{EDITION}.mmdb"


def main() -> int:
    key = os.environ.get("SDH_MAXMIND_LICENSE_KEY", "").strip()
    if not key:
        print("Erreur : SDH_MAXMIND_LICENSE_KEY manquant dans l'environnement.")
        return 1
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tar_path = Path(tmp) / "geolite.tar.gz"
        with httpx.stream(
            "GET",
            BASE_URL,
            params={"edition_id": EDITION, "license_key": key, "suffix": "tar.gz"},
            timeout=60,
            follow_redirects=True,
        ) as resp:
            if resp.status_code != 200:
                print(f"Erreur HTTP {resp.status_code} : clé invalide ou compte non activé.")
                return 1
            with open(tar_path, "wb") as fh:
                for chunk in resp.iter_bytes(65536):
                    fh.write(chunk)
        with tarfile.open(tar_path) as tar:
            member = next(
                m for m in tar.getmembers() if m.name.endswith(f"{EDITION}.mmdb")
            )
            extracted = tar.extractfile(member)
            if extracted is None:
                print("Erreur : membre introuvable dans l'archive.")
                return 1
            TARGET.write_bytes(extracted.read())
    print(f"Base installée : {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
