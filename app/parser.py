"""
Module d'analyse de texte (parseur de phrases).
Fournit des fonctions simples pour extraire des métriques textuelles.
"""
import re
from typing import Dict, Any


def analyze_text(text: str) -> Dict[str, Any]:
    """
    Analyse une chaîne de caractères et renvoie des statistiques descriptives :
    - nombre de mots
    - nombre total de caractères
    - nombre de caractères hors espaces
    - nombre de voyelles et de consonnes
    - longueur moyenne des mots
    - mot le plus long
    """
    cleaned_text = text.strip()
    if not cleaned_text:
        return {
            "word_count": 0,
            "char_count": 0,
            "char_count_no_spaces": 0,
            "vowels_count": 0,
            "consonants_count": 0,
            "avg_word_length": 0.0,
            "longest_word": "",
        }

    # Extraction des mots (alphanumériques)
    words = re.findall(r"\b\w+\b", cleaned_text)
    word_count = len(words)

    char_count = len(cleaned_text)
    char_count_no_spaces = len(re.sub(r"\s+", "", cleaned_text))

    # Comptage des voyelles et consonnes (supporte les accents français courants)
    vowels = len(re.findall(r"[aeiouyàâäéèêëîïôöùûüÿAEIOUYÀÂÄÉÈÊËÎÏÔÖÙÛÜŸ]", cleaned_text))
    consonants = len(re.findall(r"[bcdfghjklmnpqrstvwxzBCDFGHJKLMNPQRSTVWXZçÇ]", cleaned_text))

    if word_count > 0:
        avg_word_length = round(sum(len(w) for w in words) / word_count, 2)
        longest_word = max(words, key=len)
    else:
        avg_word_length = 0.0
        longest_word = ""

    return {
        "word_count": word_count,
        "char_count": char_count,
        "char_count_no_spaces": char_count_no_spaces,
        "vowels_count": vowels,
        "consonants_count": consonants,
        "avg_word_length": avg_word_length,
        "longest_word": longest_word,
    }
