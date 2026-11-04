"""Narrow source equivalence, never a language interpreter or accent transliterator."""
import re
import unicodedata

PUNCTUATION=str.maketrans({'‘':"'",'’':"'",'“':'"','”':'"','–':'-','—':'-'})
ARROW=re.compile(r'→|⇒|➜|⟶|->')

def comparable(text):
    return ''.join(' ' if c.isspace() else c for c in text.translate(PUNCTUATION))

def verbatim(raw,phrase):
    if not phrase:return None
    pattern=r'\s+'.join(re.escape(p) for p in comparable(phrase).split())
    match=re.search(pattern,comparable(raw),re.I)
    return raw[match.start():match.end()] if match else None

def valid_input(text):
    if not text.strip():raise ValueError('Describe the stops you want to visit.')
    if any(unicodedata.category(c) in ('Cc','Cs') and c not in '\t\n\r' or c in '\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069' for c in text):
        raise ValueError('Remove hidden control characters from your request.')
    return text
