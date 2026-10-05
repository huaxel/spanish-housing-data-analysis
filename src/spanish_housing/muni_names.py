"""Canonical keys for Spanish municipal names across publishers.

MIVAU/DIBA write articles prefixed ("El Bruc", "L'Ametlla"), INE appends
them ("Bruc, El", "Rozas de Madrid, Las"); both tag aggregates with
parentheticals ("Barcelona (provincia)", "Madrid (ciudad)").
muni_key() collapses all three differences. Fails safe: collisions after
canonicalization must be resolved explicitly, never silently merged.
"""

from __future__ import annotations

import re
import unicodedata

_ARTICLES = {"EL", "LA", "LOS", "LAS", "ELS", "LES", "ES", "SA", "SES", "NA", "EN", "L"}
_QUALIFIERS = {"(CIUDAD)", "(PROVINCIA)"}


def _strip_accents(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()


def muni_key(name: str) -> str:
    """Canonical municipal key: upper, no accents/punctuation, no articles."""
    s = _strip_accents(name).upper()
    for q in _QUALIFIERS:
        s = s.replace(q, "")
    s = re.sub(r"[^A-Z ]", " ", s)
    toks = s.split()
    # Leading article: EL BRUC, L AMETLLA, ELS HOSTALETS, SES SALINES...
    if toks and (toks[0] in _ARTICLES or toks[0] == "L"):
        toks = toks[1:]
    # Trailing article: BRUC EL, ROZAS DE MADRID LAS, PALMA LA...
    if len(toks) > 1 and toks[-1] in _ARTICLES:
        toks = toks[:-1]
    return " ".join(toks)
