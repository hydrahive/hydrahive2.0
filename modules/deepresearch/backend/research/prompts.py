"""Alle Prompt-Templates des Research-Loops an einem Ort.

Datum wird explizit eingespeist (today_str), damit lokale Modelle nicht auf ihr
Trainings-Cutoff-Jahr zurückfallen.
"""
from __future__ import annotations

import datetime


def today_str() -> str:
    return datetime.date.today().isoformat()


SYSTEM = (
    "Du bist ein gründlicher Recherche-Assistent. Heute ist {date}. "
    "Antworte ausschließlich auf Deutsch. Halte dich exakt an das geforderte Ausgabeformat."
)


def plan(question: str) -> str:
    return (
        f"Frage des Nutzers: {question}\n\n"
        "Zerlege die Frage in 3-5 fokussierte Teil-Fragen und bestimme die Kategorie.\n"
        "Kategorien: product | comparison | howto | factcheck | general\n\n"
        'Antworte NUR mit JSON: {"category": "...", "subquestions": ["...", "..."]}'
    )


def queries(question: str, subquestions: list[str], first_round: bool, known: list[str]) -> str:
    sub = "\n".join(f"- {s}" for s in subquestions) or "- (keine)"
    if first_round:
        ask = "Erzeuge 4 breite, gut gestreute Suchanfragen, die die Teil-Fragen abdecken."
    else:
        gaps = "\n".join(f"- {s}" for s in known[-12:]) or "- (noch keine)"
        ask = (
            "Bereits gesuchte Anfragen:\n" + gaps + "\n\n"
            "Erzeuge 3 NEUE, gezielte Suchanfragen, die offene Lücken schließen "
            "(keine Wiederholung der obigen)."
        )
    return (
        f"Frage: {question}\nTeil-Fragen:\n{sub}\n\n{ask}\n\n"
        'Antworte NUR mit JSON-Array von Strings: ["anfrage 1", "anfrage 2"]'
    )


def extract(question: str, title: str, url: str, content: str) -> str:
    return (
        f"Forschungsfrage: {question}\n"
        f"Quelle: {title} ({url})\n\n"
        "Seiteninhalt (gekürzt):\n"
        f"\"\"\"\n{content}\n\"\"\"\n\n"
        "Extrahiere NUR Information, die zur Forschungsfrage relevant ist. "
        "Wenn die Seite nichts Brauchbares enthält, setze relevant=false.\n\n"
        'Antworte NUR mit JSON: '
        '{"relevant": true/false, "summary": "2-4 Sätze Kernaussagen", '
        '"evidence": "konkrete Fakten/Zahlen/Zitate"}'
    )


def synthesize(question: str, current_report: str, new_findings: str) -> str:
    base = current_report.strip() or "(noch kein Bericht)"
    return (
        f"Forschungsfrage: {question}\n\n"
        f"Bisheriger Arbeitsbericht:\n{base}\n\n"
        f"Neue Funde (mit Quellen-URLs):\n{new_findings}\n\n"
        "Aktualisiere den Arbeitsbericht: arbeite die neuen Funde ein, behalte "
        "Inline-Zitate als [Quelle](url) direkt am jeweiligen Fakt. Markdown. "
        "Keine Erfindungen — nur was durch Funde gedeckt ist."
    )


def should_stop(question: str, report: str) -> str:
    return (
        f"Forschungsfrage: {question}\n\n"
        f"Aktueller Bericht:\n{report}\n\n"
        "Ist der Bericht umfassend genug, um die Frage fundiert zu beantworten? "
        "Antworte NUR mit YES oder NO."
    )


_CATEGORY_HINT = {
    "product": "Strukturiere als Produkt-/Kaufberatung: Optionen, Pro/Contra, Empfehlung.",
    "comparison": "Strukturiere als Vergleich: Kriterien-Tabelle, dann Fazit.",
    "howto": "Strukturiere als Schritt-für-Schritt-Anleitung mit Voraussetzungen.",
    "factcheck": "Strukturiere als Faktencheck: Behauptung, Belege, Einordnung.",
    "general": "Strukturiere als gut gegliederten Übersichtsartikel.",
}


def final_report(question: str, report: str, category: str) -> str:
    hint = _CATEGORY_HINT.get(category, _CATEGORY_HINT["general"])
    return (
        f"Forschungsfrage: {question}\n\n"
        f"Recherche-Material (mit Quellen):\n{report}\n\n"
        f"Schreibe den finalen Bericht. {hint}\n"
        "Anforderungen:\n"
        "- Magazin-Qualität, mind. 1200 Wörter, klare ##/###-Überschriften\n"
        "- Beginne mit einer aussagekräftigen H1-Überschrift (# Titel)\n"
        "- Executive Summary am Anfang, Fazit am Ende\n"
        "- Inline-Zitate [Quellenname](url) direkt am Fakt\n"
        "- Nur durch das Material gedeckte Aussagen; Lücken offen benennen\n"
        "Gib NUR den Markdown-Bericht aus, keine Vorrede."
    )
