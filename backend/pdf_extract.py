"""Extraction du texte d'un PDF, 100% en local (aucun envoi reseau).

On utilise pdfplumber qui lit la couche texte du PDF. Si le PDF est un scan
(image sans texte), l'extraction renverra peu ou pas de texte : on le signale
a l'appelant pour qu'il previenne l'utilisateur (OCR a ajouter plus tard).
"""
from __future__ import annotations

import io

import pdfplumber


def extract_text(pdf_bytes: bytes) -> str:
    """Renvoie le texte concatene de toutes les pages du PDF."""
    pages_text: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            pages_text.append(txt)
    return "\n\n".join(pages_text).strip()


def looks_like_scan(text: str) -> bool:
    """Heuristique : un PDF scanne renvoie un texte quasi vide."""
    return len(text.strip()) < 30
