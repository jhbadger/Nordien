#!/usr/bin/env python3
"""
Nordien <-> English translator.

Uses nordien_dict.txt for vocabulary and applies grammar rules:
  - Verb conjugation: root + -e (present), -te (past), -ende (progressive), -en (infinitive)
  - Noun plural: root + -ar
  - Genitive: root + -s
  - Articles: en (a/an), de (the)
  - Word order: same as English (no reordering applied)

Usage:
    python translate.py "some english text"       # English -> Nordien
    python translate.py -r "som nordien tekst"   # Nordien -> English
    python translate.py                          # interactive mode
    python translate.py -w dog                  # look up a word both ways
"""

import re
import sys
from pathlib import Path

DICT_FILE = Path(__file__).parent / "nordien_dict.txt"

# ─── Pronouns ────────────────────────────────────────────────────────────────

PRONOUNS_EN_NO: dict[str, str] = {
    # subject
    "i": "eg", "we": "vi", "you": "du", "he": "han", "she": "zi",
    "it": "het", "they": "dee", "one": "man",
    # object
    "me": "meg", "us": "os", "him": "han", "her": "zi", "them": "dem",
    # possessive
    "my": "min", "mine": "min", "our": "vor", "ours": "vor",
    "your": "din", "yours": "din", "his": "hans", "hers": "zir",
    "its": "hets", "their": "der", "theirs": "der",
}

# ─── Function words (articles, conjunctions, prepositions, adverbs…) ────────

FUNCTION_EN_NO: dict[str, str] = {
    # articles
    "a": "en", "an": "en", "the": "de",
    # to be
    "be": "eren", "is": "ere", "are": "ere", "am": "ere",
    "was": "erte", "were": "erte", "been": "erte",
    # to have (as auxiliary)
    "have": "have", "has": "have", "had": "havte",
    # do (as auxiliary in questions/negations — Nordien drops it; keep blank)
    # NOTE: Nordien questions use subject-verb inversion, not "do"-support.
    # We emit the bare infinitive so "do you speak?" → "spreken du?" approximately.
    "do": "",  # auxiliary "do" is silent in Nordien
    "does": "",
    "did": "",
    # compound / nautical / specialty vocabulary gaps in the dictionary
    "rowboat": "roebot", "rowboats": "roebotar",
    "stern": "bak",      # stern of a boat = back
    "oar": "roepad", "oars": "roepardar", "oar-locks": "roeklemar",
    "bunk": "slafskelf", "bunks": "slafskelfar",
    "quilt": "dek",      # cover/quilt = dek
    "lantern": "lantern", "lanterns": "lanternsar",
    "meadow": "grasfeld", "meadows": "grasfeldsar",
    "shanty": "stug", "shanties": "stugar",
    "logging": "holsveg",  # logging road = holsveg
    # words where the verb sense should win over the noun sense in the dictionary
    "die": "doden",      # die (v) not die (n, game piece = kastkub)
    "lie": "ligen",      # lie (v, recline) not lie (n, untruth)
    "run": "reenen",     # run (v)
    "light": "tilbrenen",  # light (v, kindle) — but as adj/n handled by dict
    "chill": "kulde",    # chill (n/v)  — gap in dictionary
    # modals / auxiliaries
    "will": "skal", "would": "skul", "shall": "skal",
    "can": "kane", "could": "kante",
    "may": "mage", "might": "magte",
    "must": "muste", "should": "skule",
    # conjunctions
    "and": "ent", "or": "oder", "but": "men",
    "although": "obvel", "because": "vel",
    "if": "als", "while": "teed", "as": "som",
    "than": "dan", "so": "so", "like": "lik",
    # negation
    "not": "neet", "no": "nej",
    # prepositions
    "in": "i", "on": "op", "at": "an", "to": "til",
    "from": "van", "of": "van", "with": "met",
    "by": "van", "for": "for", "about": "over",
    "after": "na", "before": "vor", "under": "unter",
    "over": "ovan", "above": "ovan", "through": "herdur",
    "into": "i til", "across": "herover", "along": "enlit",
    "toward": "mot", "towards": "mot", "between": "melan",
    "among": "melan", "near": "ner", "beside": "nest",
    "against": "agen", "around": "runt", "behind": "hind",
    # adverbs
    "up": "up", "down": "neder", "out": "ut", "back": "baka",
    "away": "fort", "here": "har", "there": "dar", "now": "nu",
    "then": "dan", "very": "veri", "quite": "veri", "too": "veri",
    "also": "og", "just": "just", "only": "nur", "still": "dok",
    "always": "altid", "never": "nitid", "sometimes": "imal",
    "often": "oft", "soon": "balda", "already": "red",
    "again": "nomals", "even": "even", "yet": "dok",
    "once": "enmal", "twice": "tvomal", "else": "ander",
    "ahead": "vorut", "further": "ferre", "further": "ferre",
    "inside": "inan", "outside": "utan",
    # question words
    "what": "va", "where": "var", "when": "ven",
    "why": "varfor", "how": "hur", "who": "ver", "whom": "ver",
    # determiners
    "this": "des", "that": "da", "these": "desar", "those": "dear",
    "all": "ala", "some": "fler", "any": "velka", "every": "vari",
    "each": "eek", "both": "boda", "many": "mika", "much": "mika",
    "more": "mer", "most": "merste", "less": "mindre", "least": "mindste",
    "few": "fler", "another": "en ander", "other": "ander",
    "same": "sam", "such": "so",
    # comparatives that aren't regular -er/-est
    "better": "gudre", "best": "gudste",
    "worse": "slegre", "worst": "slegste",
    "bigger": "grotre", "biggest": "grotste",
    "smaller": "kleenre", "smallest": "kleenste",
    "earlier": "frugre", "earliest": "frugste",
    "later": "latre", "latest": "latste",
    "nearer": "nerre", "nearest": "nerrste",
    # numbers
    "zero": "nul", "two": "tvo", "three": "tri", "four": "fir",
    "five": "fiv", "six": "seks", "seven": "siven", "eight": "akt",
    "nine": "neen", "ten": "ten", "hundred": "hundred",
    "thousand": "tusen", "million": "miljon",
    # greetings / social
    "yes": "ja", "please": "gudvil", "thanks": "dank",
    "thank": "danken", "hello": "hej", "goodbye": "adjo",
    "well": "gud", "okay": "alreet", "sorry": "bedure",
    "maybe": "velekt", "perhaps": "velekt",
    # contractions (expand before lookup in practice)
    "don't": "neet", "doesn't": "neet", "didn't": "neet",
    "isn't": "ere neet", "aren't": "ere neet",
    "wasn't": "erte neet", "weren't": "erte neet",
    "won't": "skal neet", "wouldn't": "skul neet",
    "can't": "kane neet", "couldn't": "kante neet",
    "shouldn't": "skule neet", "mustn't": "muste neet",
    "haven't": "have neet", "hasn't": "have neet", "hadn't": "havte neet",
    "i'm": "eg ere", "i've": "eg have", "i'll": "eg skal", "i'd": "eg skul",
    "you're": "du ere", "he's": "han ere", "she's": "zi ere",
    "it's": "het ere", "we're": "vi ere", "they're": "dee ere",
    "that's": "da ere", "there's": "dar ere", "here's": "har ere",
    "i'm": "eg ere",
}

# ─── English irregular verb → (Nordien infinitive, tense) ───────────────────

IRREGULAR_EN: dict[str, tuple[str, str]] = {
    # be
    "was": ("eren", "past"), "were": ("eren", "past"),
    "is": ("eren", "pres"), "are": ("eren", "pres"), "am": ("eren", "pres"),
    # have
    "had": ("haven", "past"), "has": ("haven", "pres"),
    # go
    "went": ("goen", "past"), "gone": ("goen", "past"),
    # come
    "came": ("komen", "past"),
    # see
    "saw": ("segen", "past"), "seen": ("segen", "past"),
    # say / tell
    "said": ("sagen", "past"), "told": ("sagen", "past"),
    # hear
    "heard": ("horen", "past"),
    # get
    "got": ("geten", "past"), "gotten": ("geten", "past"),
    # give
    "gave": ("given", "past"), "given": ("given", "past"),
    # take
    "took": ("tegen", "past"), "taken": ("tegen", "past"),
    # make
    "made": ("maken", "past"),
    # know
    "knew": ("veten", "past"), "known": ("veten", "past"),
    # think
    "thought": ("denken", "past"),
    # bring / carry
    "brought": ("bringen", "past"),
    # lie (recline)
    "lay": ("ligen", "past"), "lain": ("ligen", "past"),
    # lay (place)
    "laid": ("seten", "past"),
    # run
    "ran": ("reenen", "past"),
    # sit
    "sat": ("siten", "past"),
    # stand
    "stood": ("stejen", "past"),
    # hold
    "held": ("holden", "past"),
    # feel
    "felt": ("folen", "past"),
    # find
    "found": ("finden", "past"),
    # send
    "sent": ("senden", "past"),
    # cut
    "cut": ("sneden", "past"),
    # put
    "put": ("seten", "past"),
    # let
    "let": ("lasen", "past"),
    # begin
    "began": ("beginen", "past"), "begun": ("beginen", "past"),
    # blow
    "blew": ("blosen", "past"), "blown": ("blosen", "past"),
    # bite
    "bit": ("biten", "past"), "bitten": ("biten", "past"),
    # fall
    "fell": ("fallen", "past"), "fallen": ("fallen", "past"),
    # smelled / smelt
    "smelled": ("ruken", "past"), "smelt": ("ruken", "past"),
    # miscellaneous past forms that -ed rule would miss
    "pulled": ("dragen", "past"),
    "shoved": ("skoven", "past"),
    "rowed": ("roen", "past"),
    "walked": ("lopen", "past"),
    "rolled": ("drelen", "past"),
    "smiled": ("glimen", "past"),
    "laughed": ("laken", "past"),
    "tried": ("proven", "past"),
    "started": ("starten", "past"),
    "stopped": ("stopen", "past"),
    "moved": ("bevegen", "past"),
    "turned": ("drelen", "past"),
    "asked": ("fragen", "past"),
    "helped": ("helpen", "past"),
    "looked": ("sigen", "past"),
    "followed": ("folgen", "past"),
    "carried": ("bringen", "past"),
    "motioned": ("tegnden", "past"),
    "ordered": ("ordren", "past"),
    "poured": ("skuten", "past"),
    "wrapped": ("ipaken", "past"),
    "unwrapped": ("utpaken", "past"),
    "scrubbed": ("skruben", "past"),
    "washed": ("vasken", "past"),
    "operated": ("opereren", "past"),
    "picked": ("leften", "past"),    # picked up
    "slapped": ("slapten", "past"),
    "handed": ("overgiven", "past"),
    "watched": ("sigen", "past"),
    "finished": ("ferdigen", "past"),
    "bent": ("bugen", "past"),
    "pulled": ("dragen", "past"),
    "mounted": ("klimten", "past"),
    "rested": ("rasten", "past"),
    "sagged": ("sagen", "past"),
    "flowed": ("flusen", "past"),
    "drawn": ("dragen", "past"),
    "barked": ("lermen", "past"),
    "barking": ("lermen", "prog"),
    "born": ("beren", "past"),
    "tipped": ("tilten", "past"),
    "seated": ("siten", "past"),
    "trailed": ("slepen", "past"),
    "jumped": ("springen", "past"),
    "screamed": ("rupen", "past"),
    "screaming": ("rupen", "prog"),
    "died": ("doden", "past"),
    "dying": ("doden", "prog"),
    "killed": ("dodiren", "past"),
    "lying": ("ligen", "prog"),
    "sitting": ("siten", "prog"),
    "standing": ("stejen", "prog"),
    "going": ("goen", "prog"),
    "coming": ("komen", "prog"),
    "running": ("reenen", "prog"),
    "saying": ("sagen", "prog"),
    "telling": ("sagen", "prog"),
    "seeing": ("segen", "prog"),
    "looking": ("sigen", "prog"),
    "hearing": ("horen", "prog"),
    "holding": ("holden", "prog"),
    "working": ("arbeten", "prog"),
    "rowing": ("roen", "prog"),
    "smoking": ("ruken", "prog"),
}

# ─── Nordien special forms → English ────────────────────────────────────────

NO_SPECIAL_EN: dict[str, str] = {
    # common nouns that get shadowed by rarer synonyms in the dict
    "fru": "woman", "jung": "young", "man": "man", "fater": "father",
    "mord": "murder", "blud": "blood", "keel": "throat", "og": "eye",
    "sko": "lake", "brink": "shore", "bot": "boat", "veg": "road",
    "pad": "path", "skog": "forest", "bak": "back", "huved": "head",
    "krop": "body", "gesik": "face", "oer": "ear", "rand": "edge",
    "vand": "wall", "flank": "side", "basen": "pool", "bek": "basin",
    "lerm": "noise", "morn": "morning", "nakt": "night",
    "sun": "sun", "strand": "beach", "gulf": "bay", "kamp": "camp",
    "hund": "dog", "ting": "thing", "tir": "animal", "fisk": "fish",
    "blud": "blood", "stit": "stitch", "sep": "soap", "ruk": "smoke",
    "lak": "laugh", "rup": "scream", "likt": "light", "durk": "dark",
    "varm": "warm", "kalt": "cold", "hard": "hard", "stil": "still",
    "ruig": "quiet", "veet": "wet", "glad": "happy", "sleg": "bad",
    # subject pronouns
    "eg": "I", "vi": "we", "du": "you", "han": "he",
    "zi": "she", "het": "it", "dee": "they", "man": "one",
    # object pronouns
    "meg": "me", "deg": "you", "os": "us", "ir": "you",
    "dem": "them",
    # possessive
    "min": "my", "vor": "our", "din": "your", "hans": "his",
    "zir": "her", "hets": "its", "jeer": "your", "der": "their",
    # articles
    "de": "the", "en": "a",
    # to be
    "eren": "to be", "ere": "is/are", "erte": "was/were",
    # to have
    "haven": "to have", "have": "has/have", "havte": "had",
    # auxiliaries
    "skal": "will", "skul": "would", "muste": "must",
    "kane": "can", "kante": "could", "skule": "should",
    "mage": "may", "magte": "might",
    # conjunctions
    "ent": "and", "men": "but", "oder": "or", "neet": "not",
    "obvel": "although", "vel": "because", "als": "if",
    "teed": "while", "som": "as", "lik": "like",
    # prepositions
    "i": "in", "op": "on", "an": "at", "til": "to", "van": "from/of",
    "met": "with", "for": "for", "over": "about", "na": "after",
    "vor": "before", "unter": "under", "ovan": "above/over",
    "herdur": "through", "herover": "across", "enlit": "along",
    "mot": "toward", "melan": "between", "ner": "near",
    "nest": "beside", "agen": "against", "runt": "around",
    "hind": "behind",
    # adverbs
    "up": "up", "neder": "down", "ut": "out", "baka": "back",
    "fort": "away", "har": "here", "dar": "there", "nu": "now",
    "dan": "then", "veri": "very", "og": "also", "just": "just",
    "nur": "only", "dok": "still", "altid": "always", "nitid": "never",
    "imal": "sometimes", "oft": "often", "balda": "soon", "red": "already",
    "nomals": "again", "even": "even", "enmal": "once", "tvomal": "twice",
    "vorut": "ahead", "ferre": "further", "inan": "inside", "utan": "outside",
    # question words
    "va": "what", "var": "where", "ven": "when",
    "varfor": "why", "hur": "how", "ver": "who",
    # determiners
    "des": "this", "da": "that", "desar": "these", "dear": "those",
    "ala": "all", "fler": "some", "velka": "any", "vari": "every",
    "eek": "each", "boda": "both", "mika": "many/much",
    "mer": "more", "merste": "most", "mindre": "less", "mindste": "least",
    "ander": "other", "sam": "same",
    # comparatives
    "gudre": "better", "gudste": "best",
    "slegre": "worse", "slegste": "worst",
    "grotre": "bigger", "grotste": "biggest",
    "kleenre": "smaller", "kleenste": "smallest",
    "ferre": "further", "ferrste": "furthest",
    # numbers
    "nul": "zero", "tvo": "two", "tri": "three", "fir": "four",
    "fiv": "five", "seks": "six", "siven": "seven", "akt": "eight",
    "neen": "nine", "ten": "ten", "hundred": "hundred",
    "tusen": "thousand", "miljon": "million",
    # greetings
    "ja": "yes", "nej": "no", "gudvil": "please", "dank": "thanks",
    "hej": "hello", "adjo": "goodbye", "alreet": "okay",
    "velekt": "maybe", "bedure": "sorry",
}


# ─── Dictionary loader ───────────────────────────────────────────────────────

class NordienDict:
    def __init__(self, path: Path):
        self.en_no: dict[str, tuple[str, str]] = {}   # english  → (nordien, pos)
        self.no_en: dict[str, tuple[str, str]] = {}   # nordien  → (english, pos)
        self._load(path)

    def _load(self, path: Path):
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue
                m = re.match(r"^(.+?)(?:\s*\(([^)]+)\))?\s*:\s*(.+)$", line)
                if not m:
                    continue
                en = m.group(1).strip().lower()
                pos = (m.group(2) or "").lower()
                no_raw = m.group(3).strip()

                # Take primary form: first before semicolon or comma, strip parenthetical notes
                primary = no_raw.split(";")[0]
                primary = re.sub(r"\([^)]+\)", "", primary).strip().lower()
                primary = primary.split(",")[0].strip()  # first of comma alternatives
                if not primary:
                    continue

                self.en_no.setdefault(en, (primary, pos))
                self.no_en.setdefault(primary, (en, pos))

    def lookup_en(self, word: str) -> tuple[str, str] | None:
        return self.en_no.get(word.lower())

    def lookup_no(self, word: str) -> tuple[str, str] | None:
        return self.no_en.get(word.lower())


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _no_root(infinitive: str) -> str:
    """Strip -en from Nordien infinitive to get verb root."""
    return infinitive[:-2] if infinitive.endswith("en") else infinitive


def _no_conjugate(infinitive: str, tense: str) -> str:
    root = _no_root(infinitive)
    return {
        "past": root + "te",
        "pres": root + "e",
        "prog": root + "ende",
        "imp":  root,
    }.get(tense, infinitive)


def _cap(result: str, original: str) -> str:
    """Preserve capitalisation of the original token."""
    if result and original and original[0].isupper():
        return result[0].upper() + result[1:]
    return result


# ─── English → Nordien ───────────────────────────────────────────────────────

def en_word(word: str, dic: NordienDict) -> str:
    lower = word.lower()

    # 1. Pronouns
    if lower in PRONOUNS_EN_NO:
        return _cap(PRONOUNS_EN_NO[lower], word)

    # 2. Function words / contractions
    if lower in FUNCTION_EN_NO:
        return _cap(FUNCTION_EN_NO[lower], word)

    # 3. Irregular verbs
    if lower in IRREGULAR_EN:
        inf, tense = IRREGULAR_EN[lower]
        return _cap(_no_conjugate(inf, tense), word)

    # 4. Direct dictionary lookup
    hit = dic.lookup_en(lower)
    if hit:
        return _cap(hit[0], word)

    # 5. English -ing → Nordien -ende
    if lower.endswith("ing"):
        base = lower[:-3]
        for candidate in (base, base + "e"):
            h = dic.lookup_en(candidate)
            if h and "v" in h[1]:
                return _cap(_no_root(h[0]) + "ende", word)
        # doubled consonant: running → run
        if len(base) >= 2 and base[-1] == base[-2]:
            h = dic.lookup_en(base[:-1])
            if h and "v" in h[1]:
                return _cap(_no_root(h[0]) + "ende", word)

    # 6. English -ed → Nordien -te
    if lower.endswith("ed"):
        for candidate in (lower[:-2], lower[:-1], lower[:-2] + "e"):
            h = dic.lookup_en(candidate)
            if h and "v" in h[1]:
                return _cap(_no_root(h[0]) + "te", word)
        # doubled consonant
        if len(lower) >= 4 and lower[-3] == lower[-4]:
            h = dic.lookup_en(lower[:-3])
            if h and "v" in h[1]:
                return _cap(_no_root(h[0]) + "te", word)

    # 7. English -s  → Nordien -e (3sg verb) or -ar (plural noun)
    if lower.endswith("s") and not lower.endswith("ss"):
        base = lower[:-1]
        h = dic.lookup_en(base)
        if h:
            no, pos = h
            if "v" in pos:
                return _cap(_no_root(no) + "e", word)
            if "n" in pos:
                return _cap(no + "ar", word)

    # 8. Genitive 's
    if lower.endswith("'s"):
        h = dic.lookup_en(lower[:-2])
        if h:
            return _cap(h[0] + "s", word)

    # 9. English -ly adverb → strip to adjective (Nordien adj = adv)
    if lower.endswith("ly") and len(lower) > 4:
        for base in (lower[:-2], lower[:-3] + "y"):   # quickly→quick, happily→happy
            h = dic.lookup_en(base)
            if h:
                return _cap(h[0], word)

    # 10. English comparative -er / superlative -est → Nordien -re / -ste
    if lower.endswith("er") and len(lower) > 4:
        h = dic.lookup_en(lower[:-2])
        if h and "adj" in h[1]:
            return _cap(h[0] + "re", word)
    if lower.endswith("est") and len(lower) > 5:
        h = dic.lookup_en(lower[:-3])
        if h and "adj" in h[1]:
            return _cap(h[0] + "ste", word)

    # 11. Proper noun (capitalised, not in dict): keep as-is
    if word[0].isupper():
        return word

    return f"[{word}]"


# ─── Nordien → English ───────────────────────────────────────────────────────

def no_word(word: str, dic: NordienDict) -> str:
    lower = word.lower()

    # 1. Special hardcoded forms
    if lower in NO_SPECIAL_EN:
        return _cap(NO_SPECIAL_EN[lower], word)

    # 2. Direct lookup
    hit = dic.lookup_no(lower)
    if hit:
        return _cap(hit[0], word)

    # 3. Plural -ar
    if lower.endswith("ar"):
        hit = dic.lookup_no(lower[:-2])
        if hit:
            return _cap(hit[0] + "s", word)

    # 4. Progressive -ende → -ing
    if lower.endswith("ende"):
        root = lower[:-4]
        for inf in (root + "en", root + "e", root):
            hit = dic.lookup_no(inf)
            if hit:
                en = hit[0].rstrip("e")
                return _cap(en + "ing", word)

    # 5. Past -te → -ed / was/were/had
    if lower.endswith("te"):
        root = lower[:-2]
        for inf in (root + "en", root + "e", root):
            hit = dic.lookup_no(inf)
            if hit:
                en = hit[0]
                # avoid double-e endings
                if en.endswith("e"):
                    return _cap(en + "d", word)
                return _cap(en + "ed", word)

    # 6. Present -e  (Nordien same form all persons → return base)
    if lower.endswith("e") and not lower.endswith("ee"):
        root = lower[:-1]
        hit = dic.lookup_no(root + "en")
        if hit:
            return _cap(hit[0], word)

    # 7. Genitive/plural -s
    if lower.endswith("s"):
        hit = dic.lookup_no(lower[:-1])
        if hit:
            return _cap(hit[0] + "'s", word)

    # 8. Comparative -re
    if lower.endswith("re"):
        hit = dic.lookup_no(lower[:-2])
        if hit:
            return _cap(hit[0] + "er", word)

    # 9. Superlative -ste
    if lower.endswith("ste"):
        hit = dic.lookup_no(lower[:-3])
        if hit:
            return _cap(hit[0] + "est", word)

    # 10. Proper noun
    if word[0].isupper():
        return word

    return f"[{word}]"


# ─── Sentence translation ─────────────────────────────────────────────────────

def translate(text: str, direction: str, dic: NordienDict) -> str:
    """Translate a full string token-by-token.

    Note: Nordien uses the same SVO word order as English, so word-by-word
    translation works reasonably well.  Two limitations apply:
      1. Nordien questions use subject-verb inversion (not English "do"-support),
         so the English auxiliary "do/does/did" is dropped silently.
      2. Nordien negation (neet) follows the verb; this script places it where the
         English "not/n't" appears, which may precede the verb.
    """
    tokens = re.findall(r"[A-Za-z''’-]+|[^A-Za-z''’-]", text)
    out = []
    for tok in tokens:
        if re.fullmatch(r"[A-Za-z''’-]+", tok):
            result = en_word(tok, dic) if direction == "en" else no_word(tok, dic)
            out.append(result)
        else:
            out.append(tok)
    result = "".join(out)
    # Clean up multiple spaces left by dropped auxiliary "do/does/did"
    result = re.sub(r" {2,}", " ", result).strip()
    # Ensure sentence starts with a capital letter
    if result and result[0].islower():
        result = result[0].upper() + result[1:]
    return result


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Nordien ↔ English translator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("text", nargs="?", help="Text to translate")
    parser.add_argument("-r", "--reverse", action="store_true",
                        help="Nordien → English (default: English → Nordien)")
    parser.add_argument("-w", "--word", metavar="WORD",
                        help="Look up a word in both directions")
    parser.add_argument("-d", "--dict", default=str(DICT_FILE),
                        help="Path to nordien_dict.txt")
    args = parser.parse_args()

    dic = NordienDict(Path(args.dict))

    # ── Single word lookup ───────────────────────────────────────────────────
    if args.word:
        w = args.word.lower()
        hit_en = dic.lookup_en(w)
        hit_no = dic.lookup_no(w)
        if hit_en:
            no, pos = hit_en
            print(f"  EN→NO  {w!r:20s} ({pos})  →  {no}")
        if hit_no:
            en, pos = hit_no
            print(f"  NO→EN  {w!r:20s} ({pos})  →  {en}")
        if not hit_en and not hit_no:
            print(f"  '{w}' not found in dictionary.")
        return

    direction = "no" if args.reverse else "en"
    label = lambda d: "NO→EN" if d == "no" else "EN→NO"

    # ── Single-shot from argument ────────────────────────────────────────────
    if args.text:
        print(translate(args.text, direction, dic))
        return

    # ── Interactive mode ─────────────────────────────────────────────────────
    print("Nordien ↔ English Translator")
    print(f"Mode: {label(direction)}  |  type 'en'/'no' to switch, 'q' to quit\n")
    while True:
        try:
            line = input(f"[{label(direction)}] ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        cmd = line.lower()
        if cmd == "q":
            break
        if cmd in ("en", "no"):
            direction = cmd
            print(f"  ↳ Switched to {label(direction)}\n")
            continue
        print(translate(line, direction, dic))


if __name__ == "__main__":
    main()
