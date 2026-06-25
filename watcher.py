"""Surveillance de dossiers : anonymise automatiquement les PDF deposes.

Principe : on lit `config.json`, et pour chaque dossier active, on scanne
periodiquement les fichiers .pdf (dossiers ET sous-dossiers). Des qu'un nouveau
PDF apparait (qui ne commence pas deja par "ANOM_"), on cree une version
anonymisee "ANOM_<n>.pdf" dans le MEME dossier, mise en page conservee (PyMuPDF).

La redaction du CR (IA) n'est PAS faite ici : elle se fait a la demande, avec
l'interpretation du medecin, depuis l'onglet Workflow de l'interface.

Tout est 100% local. La config est relue a chaque cycle : tu peux modifier les
dossiers/types sans relancer le script.

Lancer :  python watcher.py    (ou le script Surveiller_dossiers.bat)
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import time
from pathlib import Path

# En developpement, rend les modules de backend/ importables. En .exe
# (PyInstaller) ils sont deja embarques comme modules de premier niveau.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from appconfig import (  # noqa: E402
    CONFIG_FILE,
    LOG_FILE,
    STATE_FILE,
    ensure_default_config,
)
from extractors import detect_type  # noqa: E402
from pdf_extract import extract_text, looks_like_scan  # noqa: E402
from pdf_redact import redact_pdf  # noqa: E402
import custom_types  # noqa: E402
from rules import TYPE_LABELS  # noqa: E402


def _all_labels() -> dict:
    """Types integres + types personnalises."""
    return {**TYPE_LABELS, **custom_types.labels()}

PREFIX = "ANOM_"

# Taille des fichiers vus au cycle precedent : on n'anonymise un PDF que
# lorsque sa taille est stable (= la copie/ecriture est terminee).
_sizes: dict[str, int] = {}

# Etat persistant (data_dir) :
#   next       : prochain numero de sortie (ANOM_0001.pdf...)
#   seen       : fichiers source deja vus (ignores au prochain passage). Contient
#                la "photo" initiale de chaque dossier + les fichiers traites.
#   baselined  : dossiers dont la photo initiale a deja ete prise.
# >>> Seuls les fichiers qui APPARAISSENT APRES la 1re surveillance d'un dossier
#     sont anonymises : on ne retraite jamais le backlog existant. <<<
STATE: dict = {"next": 1, "seen": set(), "baselined": set()}


def _load_state() -> None:
    global STATE
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        seen = set(data.get("seen", []))
        # Compat. ancien format (cle "done") : on considere ces fichiers comme vus.
        if isinstance(data.get("done"), dict):
            seen |= set(data["done"].keys())
        STATE = {
            "next": int(data.get("next", 1)),
            "seen": seen,
            "baselined": set(data.get("baselined", [])),
        }
    except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError):
        STATE = {"next": 1, "seen": set(), "baselined": set()}


def _save_state() -> None:
    try:
        STATE_FILE.write_text(
            json.dumps(
                {
                    "next": STATE["next"],
                    "seen": sorted(STATE["seen"]),
                    "baselined": sorted(STATE["baselined"]),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except OSError:
        pass


def log(msg: str) -> None:
    line = f"[{_dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        log(f"! config.json introuvable ({CONFIG_FILE}). Arret.")
        sys.exit(1)
    except json.JSONDecodeError as exc:
        log(f"! config.json invalide : {exc}")
        return {}


def resolve_type(raw: str, cr_type: str, pdf_name: str) -> str | None:
    """Type demande, ou detection automatique si cr_type == 'auto'."""
    if cr_type == "auto":
        detected = detect_type(raw)
        if detected is None:
            log(f"  ! Type indetermine (auto), ignore : {pdf_name}")
        return detected
    if cr_type not in _all_labels():
        log(f"  ! Type inconnu '{cr_type}', ignore : {pdf_name}")
        return None
    return cr_type


def process_file(pdf: Path, cr_type: str) -> bool:
    """Anonymise un fichier. Renvoie True si la decision est DEFINITIVE
    (traite, ou ignore pour de bon) -> a marquer comme "vu". False si l'on doit
    reessayer plus tard (fichier verrouille / lecture partielle)."""
    try:
        data = pdf.read_bytes()
    except (PermissionError, OSError):
        return False  # fichier verrouille / encore en cours d'ecriture

    try:
        raw = extract_text(data)
    except Exception as exc:  # PDF corrompu / partiel : on reessaiera
        log(f"  ! Lecture impossible, sera reessaye : {pdf.name} ({exc})")
        return False

    if looks_like_scan(raw):
        log(f"  ! PDF scanne (pas de texte), ignore : {pdf.name}")
        return True

    cr = resolve_type(raw, cr_type, pdf.name)
    if cr is None:
        return True  # type indetermine : on n'y revient pas

    try:
        redacted, masked = redact_pdf(data, cr)
    except Exception as exc:
        log(f"  ! Erreur anonymisation, ignore : {pdf.name} ({exc})")
        return True

    # Nom de sortie NEUTRE (compteur) : aucun nom patient dans le fichier.
    # Cree dans le meme dossier que la source.
    name = f"{PREFIX}{STATE['next']:04d}.pdf"
    out = pdf.parent / name
    while out.exists():  # anti-collision (numero deja pris)
        STATE["next"] += 1
        name = f"{PREFIX}{STATE['next']:04d}.pdf"
        out = pdf.parent / name

    # Ecriture atomique : fichier temporaire puis renommage.
    tmp = out.with_suffix(out.suffix + ".tmp")
    try:
        tmp.write_bytes(redacted)
        tmp.replace(out)
    except OSError as exc:
        log(f"  ! Ecriture impossible, sera reessaye : {out.name} ({exc})")
        tmp.unlink(missing_ok=True)
        return False

    STATE["next"] += 1
    log(f"  + {pdf.name} -> {out.name}  [{_all_labels().get(cr, cr)}, {len(masked)} elements masques]")
    return True


def candidates(directory: Path, recursive: bool) -> list[Path]:
    """PDF a traiter (hors fichiers ANOM_). Recursif = parcourt les sous-dossiers.

    Utile quand chaque CR arrive dans un sous-dossier cree automatiquement
    (ex. \\\\SERVEUR\\installation\\echophilips\\<patient>\\<fichier>.pdf).
    """
    out: list[Path] = []
    if recursive:
        for root, _dirs, files in os.walk(directory):
            for name in files:
                if name.lower().endswith(".pdf") and not name.startswith(PREFIX):
                    out.append(Path(root) / name)
    else:
        for p in directory.iterdir():
            if p.is_file() and p.suffix.lower() == ".pdf" and not p.name.startswith(PREFIX):
                out.append(p)
    return out


def scan(watch: list[dict]) -> None:
    seen = STATE["seen"]
    for entry in watch:
        if not entry.get("enabled", True):
            continue
        directory = Path(entry.get("directory", ""))
        cr_type = entry.get("cr_type", "auto")
        recursive = bool(entry.get("recursive", True))
        if not directory.is_dir():
            log(f"! Repertoire introuvable : {directory}")
            continue

        cands = candidates(directory, recursive)
        dirkey = str(directory)

        # 1re surveillance de ce dossier : on prend une PHOTO de l'existant et on
        # l'ignore. Seuls les fichiers qui arriveront ENSUITE seront anonymises.
        if dirkey not in STATE["baselined"]:
            for pdf in cands:
                seen.add(str(pdf))
            STATE["baselined"].add(dirkey)
            _save_state()
            log(
                f"  = Initialisation '{directory}' : {len(cands)} fichier(s) "
                f"existant(s) ignore(s). Seuls les nouveaux seront anonymises."
            )
            continue

        # Dossier deja initialise : ne traiter que les NOUVEAUX (hors photo).
        for pdf in sorted(cands):
            key = str(pdf)
            if key in seen:
                continue
            size = pdf.stat().st_size
            prev = _sizes.get(key)
            _sizes[key] = size
            # On attend un cycle de taille stable (>0) avant de traiter.
            if size == 0 or prev != size:
                continue
            if process_file(pdf, cr_type):
                seen.add(key)
                _save_state()


def run_forever(stop=None) -> None:
    """Boucle de surveillance. `stop` : callable optionnel renvoyant True pour
    demander l'arret (utilise quand la surveillance tourne dans un thread)."""
    ensure_default_config()
    _load_state()
    log("=== Surveillance demarree ===")
    cfg = load_config()
    for e in cfg.get("watch", []):
        state = "ON " if e.get("enabled", True) else "off"
        log(f"  [{state}] {e.get('cr_type')} <- {e.get('directory')}")
    while not (stop and stop()):
        cfg = load_config()  # relecture a chaud
        try:
            scan(cfg.get("watch", []))
        except Exception as exc:  # un cycle ne doit jamais tuer la boucle
            log(f"! Erreur de cycle : {exc}")
        time.sleep(int(cfg.get("poll_interval_seconds", 10)))


if __name__ == "__main__":
    try:
        run_forever()
    except KeyboardInterrupt:
        log("=== Surveillance arretee ===")
