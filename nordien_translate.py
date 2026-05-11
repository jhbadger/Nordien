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
    "then": "dan", "very": "veri", "quite": "veri",
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
    # teens
    "eleven": "teneen", "twelve": "tentvo", "thirteen": "tentri",
    "fourteen": "tenfir", "fifteen": "tenfiv", "sixteen": "tenseks",
    "seventeen": "tensiven", "eighteen": "tenakt", "nineteen": "tenneen",
    # tens
    "twenty": "tvoten", "thirty": "triten", "forty": "firten",
    "fifty": "fivten", "sixty": "seksten", "seventy": "siventen",
    "eighty": "akten", "ninety": "neenten",
    # greetings / social
    "yes": "ja", "please": "gudvil", "thanks": "dank",
    "thank": "danken", "hello": "hej", "goodbye": "adjo",
    "well": "gud", "okay": "alreet", "sorry": "bedure",
    "maybe": "velekt", "perhaps": "velekt",
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
    # eat / wear / speak / write
    "ate": ("eten", "past"), "eaten": ("eten", "past"),
    "eating": ("eten", "prog"),
    "wore": ("tragen", "past"), "worn": ("tragen", "past"),
    "wearing": ("tragen", "prog"),
    "spoke": ("spreken", "past"), "spoken": ("spreken", "past"),
    "speaking": ("spreken", "prog"),
    "wrote": ("skriben", "past"), "written": ("skriben", "past"),
    "writing": ("skriben", "prog"),
    # drink / sing / swim  (noun-before-verb in dict shadows -ing rule)
    "drank": ("trinken", "past"), "drunk": ("trinken", "past"),
    "drinking": ("trinken", "prog"),
    "sang": ("singen", "past"), "sung": ("singen", "past"),
    "singing": ("singen", "prog"),
    "swam": ("svimen", "past"), "swum": ("svimen", "past"),
    "swimming": ("svimen", "prog"),
    # fly / choose / drive / throw / grow  (fly: noun-before-verb)
    "flew": ("flugen", "past"), "flown": ("flugen", "past"),
    "flying": ("flugen", "prog"),
    "chose": ("veelen", "past"), "chosen": ("veelen", "past"),
    "choosing": ("veelen", "prog"),
    "drove": ("koren", "past"), "driven": ("koren", "past"),
    "driving": ("koren", "prog"),
    "threw": ("kasten", "past"), "thrown": ("kasten", "past"),
    "throwing": ("kasten", "prog"),
    "grew": ("groen", "past"), "grown": ("groen", "past"),
    "growing": ("groen", "prog"),
    # draw / break / freeze / wake  (break: noun-before-verb)
    "drew": ("dragen", "past"),
    "broke": ("breken", "past"), "broken": ("breken", "past"),
    "breaking": ("breken", "prog"),
    "froze": ("frosten", "past"), "frozen": ("frosten", "past"),
    "freezing": ("frosten", "prog"),
    "woke": ("veken", "past"), "woken": ("veken", "past"),
    "waking": ("veken", "prog"),
    # ride / tear / shake / strike / hide / swear
    "rode": ("riden", "past"), "ridden": ("riden", "past"),
    "riding": ("riden", "prog"),
    "tore": ("skiren", "past"), "torn": ("skiren", "past"),
    "tearing": ("skiren", "prog"),
    "shook": ("skutelen", "past"), "shaken": ("skutelen", "past"),
    "shaking": ("skutelen", "prog"),
    "struck": ("slagen", "past"), "stricken": ("slagen", "past"),
    "striking": ("slagen", "prog"),
    "hid": ("forsteken", "past"), "hidden": ("forsteken", "past"),
    "hiding": ("forsteken", "prog"),
    "swore": ("sveren", "past"), "sworn": ("sveren", "past"),
    "swearing": ("sveren", "prog"),
    # catch / teach / buy / fight / seek
    "caught": ("fangen", "past"), "catching": ("fangen", "prog"),
    "taught": ("leeren", "past"), "teaching": ("leeren", "prog"),
    "bought": ("kopen", "past"), "buying": ("kopen", "prog"),
    "fought": ("slakten", "past"), "fighting": ("slakten", "prog"),
    "sought": ("zuken", "past"), "seeking": ("zuken", "prog"),
    # mean / keep / sleep / weep / sweep / build / burn
    "meant": ("meenen", "past"), "meaning": ("meenen", "prog"),
    "kept": ("behaden", "past"), "keeping": ("behaden", "prog"),
    "slept": ("slafen", "past"), "sleeping": ("slafen", "prog"),
    "wept": ("veenen", "past"), "weeping": ("veenen", "prog"),
    "swept": ("fegen", "past"), "sweeping": ("fegen", "prog"),
    "built": ("bogen", "past"), "building": ("bogen", "prog"),
    "burnt": ("brenen", "past"), "burning": ("brenen", "prog"),
    # spell / lean / dream
    "spelt": ("bukstaben", "past"), "spelling": ("bukstaben", "prog"),
    "leant": ("klinen", "past"), "leaning": ("klinen", "prog"),
    "dreamt": ("dromen", "past"), "dreamed": ("dromen", "past"),
    "dreaming": ("dromen", "prog"),
}

# ─── Nordien special forms → English ────────────────────────────────────────

NO_SPECIAL_EN: dict[str, str] = {
    # common nouns that get shadowed by rarer synonyms in the dict
    "fru": "woman", "fruar": "women", "jung": "young", "man": "man", "fater": "father",
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
        self.en_no: dict[str, tuple[str, str]] = {}       # english  → (nordien, pos)  first entry wins
        self.en_no_verb: dict[str, tuple[str, str]] = {}  # english  → verb entry (last verb entry wins)
        self.no_en: dict[str, tuple[str, str]] = {}       # nordien  → (english, pos)
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
                if "v" in pos:
                    self.en_no_verb[en] = (primary, pos)
                self.no_en.setdefault(primary, (en, pos))

    def lookup_en(self, word: str) -> tuple[str, str] | None:
        return self.en_no.get(word.lower())

    def lookup_en_verb(self, word: str) -> tuple[str, str] | None:
        """Return the verb-specific entry, if any (bypasses noun-first collision)."""
        return self.en_no_verb.get(word.lower())

    def lookup_no(self, word: str) -> tuple[str, str] | None:
        return self.no_en.get(word.lower())


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_nordien_number(s: str) -> int | None:
    """Parse a compound Nordien number to its integer value.

    Nordien numbers are written as a single concatenated word, e.g.
    'tvotenfir' = 24, 'tvotusenakthundredtenfir' = 2814.
    Digits (en..neen) accumulate; multipliers (ten/hundred/tusen/miljon)
    multiply the running digit total and add it to the result.
    """
    _digits = {
        "nul": 0, "en": 1, "tvo": 2, "tri": 3, "fir": 4,
        "fiv": 5, "seks": 6, "siven": 7, "akt": 8, "neen": 9,
    }
    _mults = {"ten": 10, "hundred": 100, "tusen": 1_000, "miljon": 1_000_000}
    _all = {**_digits, **_mults}

    pos = 0
    result = 0
    current = 0  # digit(s) accumulating before the next multiplier
    while pos < len(s):
        matched = next(
            (w for w in sorted(_all, key=len, reverse=True) if s.startswith(w, pos)),
            None,
        )
        if matched is None:
            return None
        val = _all[matched]
        pos += len(matched)
        if matched in _mults:
            result += (current or 1) * val  # bare "hundred" = 1×100
            current = 0
        else:
            current += val
    result += current  # trailing units
    return result if result > 0 or s == "nul" else None


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


# ─── English irregular plurals ───────────────────────────────────────────────

_IRREG_PLURAL: dict[str, str] = {
    "man": "men", "woman": "women", "child": "children",
    "tooth": "teeth", "foot": "feet", "mouse": "mice",
    "goose": "geese", "louse": "lice", "ox": "oxen",
    "person": "people", "die": "dice",
    "knife": "knives", "life": "lives", "wife": "wives",
    "leaf": "leaves", "wolf": "wolves", "half": "halves",
    "calf": "calves", "loaf": "loaves", "shelf": "shelves",
    "elf": "elves", "thief": "thieves",
    "datum": "data", "criterion": "criteria", "phenomenon": "phenomena",
}
_IRREG_PLURAL_REV: dict[str, str] = {v: k for k, v in _IRREG_PLURAL.items()}


def _en_plural(singular: str) -> str:
    """Return the English plural, using irregular form where applicable."""
    return _IRREG_PLURAL.get(singular.lower(), singular + "s")


# ─── Number / affix lookup tables ────────────────────────────────────────────

_NUMBER_WORDS: dict[str, int] = {
    "en": 1, "tvo": 2, "tri": 3, "fir": 4, "fiv": 5,
    "seks": 6, "siven": 7, "akt": 8, "neen": 9, "ten": 10,
}
_ORDINALS: dict[str, str] = {
    "en": "first", "tvo": "second", "tri": "third", "fir": "fourth",
    "fiv": "fifth", "seks": "sixth", "siven": "seventh", "akt": "eighth",
    "neen": "ninth", "ten": "tenth",
}
_FRACTIONS: dict[str, str] = {
    "tvo": "half", "tri": "third", "fir": "quarter",
    "fiv": "fifth", "seks": "sixth", "siven": "seventh",
    "akt": "eighth", "neen": "ninth", "ten": "tenth",
}
_MULTIPLES: dict[str, str] = {
    "tvo": "double", "tri": "triple", "fir": "quadruple",
    "fiv": "quintuple", "seks": "sextuple",
}


# ─── English → Nordien ───────────────────────────────────────────────────────

def en_word(word: str, dic: NordienDict) -> str:
    lower = word.lower()

    # 1. Pronouns
    if lower in PRONOUNS_EN_NO:
        result = PRONOUNS_EN_NO[lower]
        # "I" is capitalised by English convention, not because it's a proper noun.
        return result if lower == "i" else _cap(result, word)

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
            hv = dic.lookup_en_verb(candidate)
            if hv:
                return _cap(_no_root(hv[0]) + "ende", word)
        # doubled consonant: running → run
        if len(base) >= 2 and base[-1] == base[-2]:
            h = dic.lookup_en(base[:-1])
            if h and "v" in h[1]:
                return _cap(_no_root(h[0]) + "ende", word)
            hv = dic.lookup_en_verb(base[:-1])
            if hv:
                return _cap(_no_root(hv[0]) + "ende", word)

    # 6. English -ed → Nordien -te
    if lower.endswith("ed"):
        for candidate in (lower[:-2], lower[:-1], lower[:-2] + "e"):
            h = dic.lookup_en(candidate)
            if h and "v" in h[1]:
                return _cap(_no_root(h[0]) + "te", word)
            hv = dic.lookup_en_verb(candidate)
            if hv:
                return _cap(_no_root(hv[0]) + "te", word)
        # doubled consonant
        if len(lower) >= 4 and lower[-3] == lower[-4]:
            h = dic.lookup_en(lower[:-3])
            if h and "v" in h[1]:
                return _cap(_no_root(h[0]) + "te", word)
            hv = dic.lookup_en_verb(lower[:-3])
            if hv:
                return _cap(_no_root(hv[0]) + "te", word)

    # 7. English -s  → Nordien -e (3sg verb) or -ar (plural noun)
    if lower.endswith("s") and not lower.endswith("ss"):
        base = lower[:-1]
        h = dic.lookup_en(base)
        if h:
            no, pos = h
            if "v" in pos:
                return _cap(_no_root(no) + "e", word)
            if "n" in pos:
                hv = dic.lookup_en_verb(base)
                if hv:
                    return _cap(_no_root(hv[0]) + "e", word)
                return _cap(no + "ar", word)

    # 7.5. English irregular plurals not caught above (men, mice, geese, knives…)
    if lower in _IRREG_PLURAL_REV:
        singular = _IRREG_PLURAL_REV[lower]
        h = dic.lookup_en(singular)
        if h:
            return _cap(h[0] + "ar", word)

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

    # 10. English -ness → Nordien -het  (darkness → durkhet, happiness → gladhet)
    if lower.endswith("ness") and len(lower) > 5:
        base = lower[:-4]
        candidates = [base]
        if base.endswith("i"):
            candidates.append(base[:-1] + "y")  # happi → happy
        for candidate in candidates:
            h = dic.lookup_en(candidate)
            if h:
                return _cap(h[0] + "het", word)

    # 11. English -ful → Nordien -sam  (painful → smartsam)
    if lower.endswith("ful") and len(lower) > 4:
        h = dic.lookup_en(lower[:-3])
        if h:
            return _cap(h[0] + "sam", word)

    # 12. English -some → Nordien -sam  (fearsome → angssam)
    if lower.endswith("some") and len(lower) > 5:
        h = dic.lookup_en(lower[:-4])
        if h:
            return _cap(h[0] + "sam", word)

    # 13. English -ic → Nordien -ig  (atomic → atomig)
    if lower.endswith("ic") and len(lower) > 3:
        for base in (lower[:-2], lower[:-2] + "e"):
            h = dic.lookup_en(base)
            if h:
                return _cap(h[0] + "ig", word)

    # 14. English comparative -er / superlative -est → Nordien -re / -ste
    if lower.endswith("er") and len(lower) > 4:
        h = dic.lookup_en(lower[:-2])
        if h and "adj" in h[1]:
            return _cap(h[0] + "re", word)
    if lower.endswith("est") and len(lower) > 5:
        h = dic.lookup_en(lower[:-3])
        if h and "adj" in h[1]:
            return _cap(h[0] + "ste", word)

    # 15. English -er (agent noun) → Nordien root + -er  (baker → bak+er)
    if lower.endswith("er") and len(lower) > 3:
        base = lower[:-2]
        for candidate in (base, base + "e"):
            h = dic.lookup_en(candidate)
            if h and "v" in h[1]:
                return _cap(_no_root(h[0]) + "er", word)
        if len(base) >= 2 and base[-1] == base[-2]:
            h = dic.lookup_en(base[:-1])
            if h and "v" in h[1]:
                return _cap(_no_root(h[0]) + "er", word)

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

    # 3. Causative -ir verb forms (checked before generic suffix stripping)
    if lower.endswith("irende") and len(lower) > 7:
        hit = dic.lookup_no(lower[:-6])
        if hit:
            return _cap("making " + hit[0], word)

    if lower.endswith("irte") and len(lower) > 5:
        hit = dic.lookup_no(lower[:-4])
        if hit:
            return _cap("made " + hit[0], word)

    if lower.endswith("iren") and len(lower) > 5:
        hit = dic.lookup_no(lower[:-4])
        if hit:
            return _cap("to make " + hit[0], word)

    if lower.endswith("ire") and len(lower) > 4:
        hit = dic.lookup_no(lower[:-3])
        if hit:
            return _cap("makes " + hit[0], word)

    # 4. Derivational affixes (longest first to reduce false matches)

    # -ling  offspring/young  (hundling → puppy, kikinling → chick)
    if lower.endswith("ling") and len(lower) > 5:
        hit = dic.lookup_no(lower[:-4])
        if hit:
            return _cap(hit[0] + " offspring", word)

    # -ning  noun from verb  (agerning → action, beslisning → decision)
    if lower.endswith("ning") and len(lower) > 5:
        root = lower[:-4]
        for inf in (root + "en", root + "iren", root):
            hit = dic.lookup_no(inf)
            if hit:
                en = hit[0]
                if en.endswith("e"):
                    return _cap(en[:-1] + "ing", word)
                return _cap(en + "ing", word)

    # -het  -ness  (gladhet → happiness, kanhet → ability)
    if lower.endswith("het") and len(lower) > 4:
        hit = dic.lookup_no(lower[:-3])
        if hit:
            en = hit[0]
            if en.endswith("y"):
                return _cap(en[:-1] + "iness", word)
            if en.endswith("le"):
                return _cap(en[:-2] + "ility", word)
            return _cap(en + "ness", word)

    # -sam  -ful / -some / -able  (kansam → able, smartsam → painful)
    if lower.endswith("sam") and len(lower) > 4:
        hit = dic.lookup_no(lower[:-3])
        if hit:
            en = hit[0]
            if en.endswith("e"):
                return _cap(en + "some", word)
            return _cap(en + "ful", word)

    # -ort  place  (grabort → graveyard, gerektort → courthouse)
    if lower.endswith("ort") and len(lower) > 4:
        hit = dic.lookup_no(lower[:-3])
        if hit:
            return _cap(hit[0] + " place", word)

    # -let  diminutive  (brodlet → roll, oranglet → clementine)
    if lower.endswith("let") and len(lower) > 4:
        hit = dic.lookup_no(lower[:-3])
        if hit:
            return _cap(hit[0] + "let", word)

    # -ien  person from a place  (Afrikien → African)
    if lower.endswith("ien") and len(lower) > 4:
        hit = dic.lookup_no(lower[:-3])
        if hit:
            en = hit[0]
            return _cap((en[:-1] if en[-1] in "aeiou" else en) + "an", word)

    # -ska  language / place adjective  (Afrikska → African)
    if lower.endswith("ska") and len(lower) > 4:
        hit = dic.lookup_no(lower[:-3])
        if hit:
            en = hit[0]
            return _cap((en[:-1] if en[-1] in "aeiou" else en) + "an", word)

    # -bel  multiple  (tvobel → double, tribel → triple)
    if lower.endswith("bel") and len(lower) > 4:
        num = lower[:-3]
        if num in _MULTIPLES:
            return _cap(_MULTIPLES[num], word)

    # -tel  fraction  (tvotel → half, tritel → third)
    if lower.endswith("tel") and len(lower) > 4:
        num = lower[:-3]
        if num in _FRACTIONS:
            return _cap(_FRACTIONS[num], word)

    # -mal  repetition  (trimal → three times)
    if lower.endswith("mal") and len(lower) > 4:
        num = lower[:-3]
        if num in _NUMBER_WORDS:
            n = _NUMBER_WORDS[num]
            if n == 1:
                return _cap("once", word)
            if n == 2:
                return _cap("twice", word)
            return _cap(f"{n} times", word)

    # -ig  adjective from noun/root  (basig → basic, abdomenig → abdominal)
    if lower.endswith("ig") and len(lower) > 3:
        hit = dic.lookup_no(lower[:-2])
        if hit:
            en = hit[0]
            if en.endswith("e"):
                return _cap(en[:-1] + "ic", word)
            return _cap(en + "ic", word)

    # -in  female form  (levenin → lioness)
    if lower.endswith("in") and len(lower) > 3:
        hit = dic.lookup_no(lower[:-2])
        if hit:
            en = hit[0]
            if en.endswith("e"):
                return _cap(en[:-1] + "ess", word)
            return _cap(en + "ess", word)

    # -er  agent / tool  (skoder → actor, reter → advisor)
    if lower.endswith("er") and len(lower) > 3:
        root = lower[:-2]
        for inf in (root + "en", root + "iren"):
            hit = dic.lookup_no(inf)
            if hit:
                en = hit[0]
                if en.endswith("e"):
                    return _cap(en[:-1] + "er", word)
                return _cap(en + "er", word)

    # -et  ordinal  (tvoet → second, firet → fourth)
    if lower.endswith("et") and len(lower) > 3:
        num = lower[:-2]
        if num in _ORDINALS:
            return _cap(_ORDINALS[num], word)

    # 5. Plural -ar
    if lower.endswith("ar"):
        hit = dic.lookup_no(lower[:-2])
        if hit:
            return _cap(_en_plural(hit[0]), word)

    # 6. Progressive -ende → -ing
    if lower.endswith("ende"):
        root = lower[:-4]
        for inf in (root + "en", root + "e", root):
            hit = dic.lookup_no(inf)
            if hit:
                en = hit[0].rstrip("e")
                return _cap(en + "ing", word)

    # 7. Past -te → -ed
    if lower.endswith("te"):
        root = lower[:-2]
        for inf in (root + "en", root + "e", root):
            hit = dic.lookup_no(inf)
            if hit:
                en = hit[0]
                if en.endswith("e"):
                    return _cap(en + "d", word)
                return _cap(en + "ed", word)

    # 8. Present -e  (Nordien same form all persons → return base)
    if lower.endswith("e") and not lower.endswith("ee"):
        root = lower[:-1]
        hit = dic.lookup_no(root + "en")
        if hit:
            return _cap(hit[0], word)

    # 9. Genitive/plural -s
    if lower.endswith("s"):
        hit = dic.lookup_no(lower[:-1])
        if hit:
            return _cap(hit[0] + "'s", word)

    # 10. Comparative -re
    if lower.endswith("re"):
        hit = dic.lookup_no(lower[:-2])
        if hit:
            return _cap(hit[0] + "er", word)

    # 11. Superlative -ste
    if lower.endswith("ste"):
        hit = dic.lookup_no(lower[:-3])
        if hit:
            return _cap(hit[0] + "est", word)

    # 12. Compound Nordien number (e.g. tvotenfir → 24, tenen → 11)
    n = _parse_nordien_number(lower)
    if n is not None:
        return str(n)

    # 13. Proper noun
    if word[0].isupper():
        return word

    return f"[{word}]"


# Auxiliaries that own their own "not" — neet stays put after these.
_EN_AUX = frozenset({
    "is", "are", "was", "were", "be", "been",
    "will", "would", "shall", "can", "could",
    "may", "might", "must", "should",
    "have", "has", "had", "do", "does", "did",
})

_DO_TENSE_MAP: dict[str, str] = {"do": "pres", "does": "pres", "did": "past"}
_WH_WORDS = frozenset({"what", "where", "when", "why", "how", "who", "whom"})

# Words that follow "one" when it is used as an impersonal pronoun (→ "man"),
# not as a numeral (→ "en").
_ONE_PRONOUN_SIGNALS = frozenset({
    "must", "should", "will", "would", "can", "could", "may", "might",
    "shall", "need", "dare", "ought", "never", "always", "often",
    "sometimes", "not", "knows", "thinks", "feels", "hopes", "tries",
    "has", "is", "was", "does",
})

# ─── Contraction expansion ────────────────────────────────────────────────────

_CONTRACTIONS: dict[str, str] = {
    # negative contractions
    "won't": "will not",    "shan't": "shall not",
    "can't": "can not",     "don't": "do not",
    "doesn't": "does not",  "didn't": "did not",
    "isn't": "is not",      "aren't": "are not",
    "wasn't": "was not",    "weren't": "were not",
    "wouldn't": "would not","couldn't": "could not",
    "shouldn't": "should not", "mustn't": "must not",
    "mightn't": "might not","needn't": "need not",
    "haven't": "have not",  "hasn't": "has not",  "hadn't": "had not",
    # subject + auxiliary
    "i'm": "i am",     "i've": "i have",  "i'll": "i will",  "i'd": "i would",
    "you're": "you are","you've": "you have","you'll": "you will","you'd": "you would",
    "he's": "he is",   "he'll": "he will", "he'd": "he would",
    "she's": "she is", "she'll": "she will","she'd": "she would",
    "it's": "it is",   "it'll": "it will", "it'd": "it would",
    "we're": "we are", "we've": "we have", "we'll": "we will", "we'd": "we would",
    "they're": "they are","they've": "they have","they'll": "they will","they'd": "they would",
    "that's": "that is","that'll": "that will","that'd": "that would",
    "there's": "there is","there'll": "there will",
    "here's": "here is",
    "what's": "what is","what'll": "what will",
    "who's": "who is",  "who'll": "who will",
    "where's": "where is","how's": "how is",
    "let's": "let us",
}

_CONTRACTION_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in sorted(_CONTRACTIONS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def _expand_contractions(text: str) -> str:
    """Expand English contractions to full words before translation."""
    def _repl(m: re.Match) -> str:
        word = m.group(0)
        expanded = _CONTRACTIONS[word.lower()]
        return expanded[0].upper() + expanded[1:] if word[0].isupper() else expanded
    return _CONTRACTION_RE.sub(_repl, text)


def _restructure_do_question(tokens: list[str]) -> tuple[list[str], int, str] | None:
    """
    Detect do/does/did questions and restructure tokens for Nordien V-S order.
    'do you speak nordien?' → tokens for 'speak you nordien?' with verb index.
    Returns (new_tokens, verb_idx_in_new_tokens, tense) or None.
    """
    word_idxs = [i for i, t in enumerate(tokens) if re.fullmatch(r"[A-Za-z'-]+", t)]
    if not word_idxs:
        return None
    wh_offset = 1 if tokens[word_idxs[0]].lower() in _WH_WORDS else 0
    if len(word_idxs) < wh_offset + 3:
        return None
    do_pos = word_idxs[wh_offset]
    tense = _DO_TENSE_MAP.get(tokens[do_pos].lower())
    if tense is None:
        return None
    subj_pos = word_idxs[wh_offset + 1]
    if tokens[subj_pos].lower() == "not":  # negative question: "do not you..." — skip
        return None
    verb_pos = word_idxs[wh_offset + 2]
    verb_tok = tokens[verb_pos]
    new_tokens: list[str] = []
    verb_new_idx = -1
    for i, t in enumerate(tokens):
        if i == do_pos:
            continue
        elif i == subj_pos:
            verb_new_idx = len(new_tokens)
            new_tokens.append(verb_tok)
            new_tokens.append(" ")
            new_tokens.append(t)
        elif i == verb_pos:
            continue
        else:
            new_tokens.append(t)
    return new_tokens, verb_new_idx, tense

# ─── Sentence translation ─────────────────────────────────────────────────────

def translate(text: str, direction: str, dic: NordienDict) -> str:
    """Translate a full string token-by-token.

    EN→NO negation: Nordien places neet *after* the verb it negates.  When
    "not/n't/don't/doesn't/didn't" follows a dropped do-auxiliary, neet is
    deferred and inserted after the next content word instead.

    NO→EN negation: "verb neet" is restructured to "do not verb" when the
    verb is not an auxiliary (past-tense restructuring is a known limitation).
    """
    _NEET = "\x00NEET\x00"
    text = text.replace('\u2018', "'").replace('\u2019', "'")  # normalise smart quotes
    if direction == "en":
        text = _expand_contractions(text)
    tokens = re.findall(r"[A-Za-z\x27-]+|[^A-Za-z\x27\x27\x27-]", text)
    out: list[str] = []
    prev_dropped = False   # last word token translated to "" (dropped auxiliary)

    # Question inversion: restructure do/does/did questions for Nordien V-S order
    question_verb_idx = -1
    question_verb_tense = ""
    if direction == "en" and text.rstrip().endswith("?"):
        q_result = _restructure_do_question(tokens)
        if q_result is not None:
            tokens, question_verb_idx, question_verb_tense = q_result

    # Imperative: if first word is a base verb (no subject precedes it), use root form.
    # Applies regardless of terminal punctuation — "Go!" and "Go." are both imperatives.
    imp_verb_idx = -1
    if direction == "en":
        word_toks = [(i, t) for i, t in enumerate(tokens) if re.fullmatch(r"[A-Za-z'-]+", t)]
        if word_toks:
            fi, fw = word_toks[0]
            fw_lower = fw.lower()
            hit = dic.lookup_en(fw_lower)
            if (hit and "v" in hit[1]) or fw_lower == "be":
                imp_verb_idx = fi

    perfect_participle_idx = -1  # next past-participle after have/has/had → use infinitive

    def _next_word_tok(idx: int) -> str:
        for j in range(idx + 1, len(tokens)):
            if re.fullmatch(r"[A-Za-z'-]+", tokens[j]):
                return tokens[j].lower()
        return ""

    for _i, tok in enumerate(tokens):
        if re.fullmatch(r"[A-Za-z'-]+", tok):
            lower_tok = tok.lower()

            # Track perfect auxiliary: mark the next past participle for infinitive form
            if direction == "en" and lower_tok in ("have", "has", "had"):
                for j in range(_i + 1, len(tokens)):
                    if re.fullmatch(r"[A-Za-z'-]+", tokens[j]):
                        if tokens[j].lower() in IRREGULAR_EN:
                            perfect_participle_idx = j
                        break

            if _i == question_verb_idx:
                raw = en_word(tok, dic)
                if raw and not raw.startswith("[") and raw.lower().endswith("en"):
                    translated = _cap(_no_conjugate(raw.lower(), question_verb_tense), tok)
                else:
                    translated = raw
            elif _i == imp_verb_idx and direction == "en":
                raw = en_word(tok, dic)
                if raw and not raw.startswith("[") and raw.lower().endswith("en"):
                    translated = _cap(_no_root(raw.lower()), tok)
                else:
                    translated = raw
            elif _i == perfect_participle_idx and direction == "en":
                inf, _ = IRREGULAR_EN[lower_tok]
                translated = _cap(inf, tok)
            elif direction == "en" and lower_tok == "one":
                translated = "man" if _next_word_tok(_i) in _ONE_PRONOUN_SIGNALS else "en"
            elif direction == "en" and lower_tok == "to":
                nw = _next_word_tok(_i)
                nw_hit = dic.lookup_en(nw) if nw else None
                nw_fn = FUNCTION_EN_NO.get(nw, "")
                if (nw_hit and "v" in nw_hit[1]) or nw == "be" or (nw_fn and nw_fn.endswith("en")):
                    translated = ""  # infinitive marker — not needed in Nordien
                else:
                    translated = en_word(tok, dic)
            elif direction == "en" and lower_tok == "too":
                nw = _next_word_tok(_i)
                nw_hit = dic.lookup_en(nw) if nw else None
                # "too" before adj/adv = excessive (tu); elsewhere = also (og)
                _too_excessive_fn = frozenset({
                    "many", "much", "few", "little", "often", "soon", "far",
                    "long", "fast", "slow", "early", "late", "well", "hard",
                })
                if (nw_hit and ("adj" in nw_hit[1] or "adv" in nw_hit[1])) \
                        or nw in _too_excessive_fn:
                    translated = "tu"
                else:
                    translated = "og"
            else:
                translated = en_word(tok, dic) if direction == "en" else no_word(tok, dic)

            # Defer neet when it comes from "not" after a dropped auxiliary,
            # or directly from a do-contraction (don't / doesn't / didn't).
            if direction == "en" and translated == "neet" and (
                prev_dropped or tok.lower() in ("don't", "doesn't", "didn't")
            ):
                out.append(_NEET)
            else:
                out.append(translated)
            prev_dropped = direction == "en" and translated == ""
        else:
            out.append(tok)
            if tok.strip():          # non-whitespace punctuation resets the flag
                prev_dropped = False

    if direction == "en":
        # Resolve each deferred neet: place it after the immediately following word.
        i = 0
        while i < len(out):
            if out[i] == _NEET:
                j = i + 1
                while j < len(out) and not re.fullmatch(r"[A-Za-z'-]+", out[j]):
                    j += 1
                if j < len(out):
                    word, gap = out[j], out[i + 1 : j]
                    out[i : j + 1] = [word] + gap + ["neet"]
                else:
                    out[i] = "neet"   # end of sentence — leave as-is
            i += 1

    result = "".join(out)
    result = re.sub(r" {2,}", " ", result).strip()
    result = re.sub(r" +([?!.,;:])", r"\1", result)  # no space before punctuation

    if direction == "no":
        # "verb not" → "do not verb" when verb is not an auxiliary.
        result = re.sub(
            r"\b(\w+) not\b",
            lambda m: m.group(0) if m.group(1).lower() in _EN_AUX
                      else f"do not {m.group(1)}",
            result,
        )

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
    try:
        import readline  # noqa: F401 — enables arrow-key editing and history in input()
    except ImportError:
        pass
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
