"""Types de documents personnalises, appris via IA a partir d'un CR fictif.

Chaque type stocke les LIBELLES des champs identifiants (nom, n° patient, date
de naissance). L'extraction reelle reste 100% locale (voir extractors.py) :
ces libelles servent a localiser les valeurs, qui sont ensuite remplacees
partout par les regles generiques. Stocke dans custom_types.json (data_dir).

Format d'une entree :
  "custom_irm": {
    "label": "IRM cerebrale",
    "name_labels": ["Nom du patient", "Patient"],
    "id_labels": ["IPP", "No. patient"],
    "dob_labels": ["Date de naissance", "Ne(e) le"]
  }
"""
from __future__ import annotations

import json
import re
import unicodedata

from appconfig import CUSTOM_TYPES_FILE


def load() -> dict:
    try:
        data = json.loads(CUSTOM_TYPES_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    CUSTOM_TYPES_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def slugify(label: str) -> str:
    s = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return "custom_" + (s or "type")


def upsert(label: str, spec: dict, type_id: str | None = None) -> str:
    data = load()
    if not type_id:
        type_id = slugify(label)
        base, n = type_id, 2
        while type_id in data:  # unicite
            type_id = f"{base}_{n}"
            n += 1
    data[type_id] = {
        "label": label,
        "name_labels": list(spec.get("name_labels", [])),
        "name_before": list(spec.get("name_before", [])),
        "id_labels": list(spec.get("id_labels", [])),
        "dob_labels": list(spec.get("dob_labels", [])),
    }
    _save(data)
    return type_id


def delete(type_id: str) -> None:
    data = load()
    if data.pop(type_id, None) is not None:
        _save(data)


def labels() -> dict:
    """type_id -> libelle lisible."""
    return {k: v.get("label", k) for k, v in load().items()}
