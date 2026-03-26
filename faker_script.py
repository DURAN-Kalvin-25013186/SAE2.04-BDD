"""
Faker MLD v3 — Générateur de données propres (aucun fix nécessaire)
===================================================================
Toutes les corrections des scripts fix_* sont intégrées directement :

  - grade, Titre, Dignite, rang : exactement 10 valeurs nommées, jamais plus
  - composant : type_aliment cohérent avec le nom (Agneau rôti → Viande, etc.)
  - organisation : type_orga limité aux 8 types officiels
  - Membre : CodeMembre entier auto-incrémenté (1, 2, 3...)
  - Legume : noms cohérents tirés d'une liste fixe

Usage:
    python faker_mld_v3.py                          # 1 000 tuples
    python faker_mld_v3.py --rows 1000000           # 1 million
    python faker_mld_v3.py --output sql             # INSERT SQL
    python faker_mld_v3.py --output json            # JSON
    python faker_mld_v3.py --out-dir ./data         # dossier personnalisé
    python faker_mld_v3.py --seed 42                # reproductible
"""

import argparse
import csv
import json
import random
import string
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Faker optionnel
# ---------------------------------------------------------------------------
try:
    from faker import Faker as _FakerLib
    _FAKER = _FakerLib("fr_FR")
except ImportError:
    _FAKER = None

_RNG = random.Random()

# ---------------------------------------------------------------------------
# Tables de référence fixes — exactement les valeurs nommées, jamais plus
# ---------------------------------------------------------------------------

# 10 grades nommés — CodeMembre sera limité à 1..10
GRADES = [
    (1,  "Apprenti"),
    (2,  "Compagnon"),
    (3,  "Maître"),
    (4,  "Grand Maître"),
    (5,  "Archonte"),
    (6,  "Sénéchal"),
    (7,  "Connétable"),
    (8,  "Maréchal"),
    (9,  "Chambellan"),
    (10, "Chancelier"),
]

TITRES = [
    (1,  "Chevalier"),
    (2,  "Dame"),
    (3,  "Ecuyer"),
    (4,  "Damoiselle"),
    (5,  "Banneret"),
    (6,  "Bachelier"),
    (7,  "Paladin"),
    (8,  "Preux"),
    (9,  "Prude Femme"),
    (10, "Vassal"),
]

DIGNITES = [
    (1,  "Noble"),
    (2,  "Roturier"),
    (3,  "Bourgeois"),
    (4,  "Anobli"),
    (5,  "Vassal"),
    (6,  "Suzerain"),
    (7,  "Seigneur"),
    (8,  "Baron"),
    (9,  "Vicomte"),
    (10, "Comte"),
]

RANGS = [
    (1,  "Premier rang"),
    (2,  "Deuxième rang"),
    (3,  "Troisième rang"),
    (4,  "Rang d'honneur"),
    (5,  "Rang de table"),
    (6,  "Rang de cérémonie"),
    (7,  "Rang militaire"),
    (8,  "Rang civil"),
    (9,  "Rang épiscopal"),
    (10, "Rang royal"),
]

# 8 types d'organisation — distribution réaliste (clubs et associations majoritaires)
TYPES_ORGA   = ["Club", "Association", "Guilde", "Loge",
                 "Cercle", "Confrérie", "Ordre", "Fraternité"]
POIDS_ORGA   = [0.30,   0.25,          0.15,    0.12,
                 0.08,   0.05,          0.03,    0.02]

# Grades — distribution pyramidale (30% Apprenti → 1% Chancelier)
# Correspond à IdGr 1..10 dans l'ordre des GRADES
POIDS_GRADES = [0.30, 0.20, 0.15, 0.10, 0.08, 0.06, 0.04, 0.03, 0.02, 0.01]

# Types d'aliment — distribution réaliste (épices et herbes majoritaires)
POIDS_CATALOGUE = {
    "Épice":           0.20,
    "Herbe":           0.15,
    "Légume":          0.05,
    "Légumineuse":     0.12,
    "Viande":          0.10,
    "Céréale":         0.5,
    "Fruit":           0.08,
    "Champignon":      0.05,
    "Poisson":         0.03,
    "Produit laitier": 0.17,
}

# Mapping sémantique nom_base → type_aliment
# Chaque composant aura un type cohérent avec son nom dès la génération
COMPOSANTS_CATALOGUE = [
    ("Agneau rôti",       "Viande"),
    ("Canard fumé",       "Viande"),
    ("Venaison",          "Viande"),
    ("Mouton braisé",     "Viande"),
    ("Carpe dorée",       "Poisson"),
    ("Brochet en gelée",  "Poisson"),
    ("Navet confit",      "Légume"),
    ("Chou frisé",        "Légume"),
    ("Pomme sauvage",     "Fruit"),
    ("Verjus",            "Fruit"),
    ("Épeautre",          "Céréale"),
    ("Fromage affiné",    "Produit laitier"),
    ("Safran",            "Épice"),
    ("Poivre long",       "Épice"),
    ("Épices orientales", "Épice"),
    ("Lentilles du Puy",  "Légumineuse"),
    ("Truffe noire",      "Champignon"),
    ("Romarin",           "Herbe"),
    ("Thym sauvage",      "Herbe"),
]

# Légumes cohérents
LEGUMES = ["Carotte", "Navet", "Panais", "Poireau", "Chou", "Betterave",
           "Raifort", "Salsifis", "Artichaut", "Topinambour", "Ail", "Oignon"]

# ---------------------------------------------------------------------------
# Générateurs de valeurs primitives
# ---------------------------------------------------------------------------

def _rand_date(start_year=2000, end_year=2024) -> str:
    start = date(start_year, 1, 1)
    delta = (date(end_year, 12, 31) - start).days
    return (start + timedelta(days=_RNG.randint(0, delta))).strftime("%Y-%m-%d")

def _rand_date_repas(start_year=2000, end_year=2024) -> str:
    """
    Date de repas concentrée au printemps (mars-avril) et automne (oct-nov),
    avec une tendance croissante : les années récentes ont plus de repas.
    """
    # Tendance croissante : on tire l'année avec un biais vers les années récentes
    annees = list(range(start_year, end_year + 1))
    poids  = [i ** 1.5 for i in range(1, len(annees) + 1)]
    total  = sum(poids)
    poids  = [p / total for p in poids]
    annee  = _RNG.choices(annees, weights=poids, k=1)[0]

    # Saisons : 60% printemps/automne, 40% reste de l'année
    if _RNG.random() < 0.60:
        # Printemps (mars-avril) ou automne (oct-nov)
        if _RNG.random() < 0.50:
            mois = _RNG.choice([3, 4])
        else:
            mois = _RNG.choice([10, 11])
    else:
        mois = _RNG.randint(1, 12)

    # Jour valide pour le mois
    import calendar
    max_jour = calendar.monthrange(annee, mois)[1]
    jour = _RNG.randint(1, max_jour)
    return date(annee, mois, jour).strftime("%Y-%m-%d")

def _date_apres_repas(date_repas_str: str) -> str:
    """
    Date d'entretien = date du repas + 0 à 30 jours.
    Les machines ayant servi pour un repas sont entretenues juste après.
    """
    d = date.fromisoformat(date_repas_str)
    d_entretien = d + timedelta(days=_RNG.randint(0, 30))
    return d_entretien.strftime("%Y-%m-%d")

def _siret() -> int:
    return _RNG.randint(1_000_000_000, 9_999_999_999)

def _raison_sociale() -> str:
    if _FAKER:
        return _FAKER.company()[:50]
    adj  = ["Global", "Alliance", "Prestige", "Horizon", "Elite", "Royal"]
    noun = ["Services", "Consulting", "Group", "Industries", "Solutions", "Partners"]
    return f"{_RNG.choice(adj)} {_RNG.choice(noun)}"[:50]

def _nom_territoire() -> str:
    if _FAKER:
        return _FAKER.city()[:50]
    regions = ["Normandie", "Bretagne", "Provence", "Alsace", "Bourgogne",
               "Auvergne", "Limousin", "Picardie", "Lorraine", "Champagne"]
    return (_RNG.choice(regions) + f"-{_RNG.randint(1,99):02d}")[:50]

def _nom_repas() -> str:
    plats = ["Banquet royal", "Festin des chevaliers", "Dîner de gala",
             "Souper d'apparat", "Déjeuner des preux", "Agapes fraternelles"]
    return (_RNG.choice(plats) + f" #{_RNG.randint(1,9999)}")[:50]

def _adresse() -> str:
    if _FAKER:
        return _FAKER.address().replace("\n", ", ")[:50]
    streets = ["Rue de la Paix", "Avenue des Chevaliers", "Boulevard du Roi",
               "Allée des Preux", "Chemin des Dames", "Place d'Armes"]
    return f"{_RNG.randint(1,200)} {_RNG.choice(streets)}"[:50]

def _nom_chevalier() -> str:
    if _FAKER:
        return _FAKER.name()[:50]
    prenoms = ["Arthur", "Lancelot", "Perceval", "Gauvain", "Tristan",
               "Iseult", "Guenièvre", "Morgane", "Viviane", "Élaine"]
    noms    = ["de Gaule", "du Lac", "de Galles", "d'Orkney", "de Bretagne",
               "Pendragon", "Le Fay", "de Cornouailles", "des Îles", "de Lyonesse"]
    return f"{_RNG.choice(prenoms)} {_RNG.choice(noms)}"[:50]

def _allergene(type_aliment: str) -> str:
    """Retourne des allergènes cohérents avec le type d'aliment du composant."""
    _ALLERGENES_PAR_TYPE = {
        "Viande":          ["Céleri", "Sulfites", "Moutarde", "Gluten", "Oeufs"],
        "Poisson":         ["Poisson", "Gluten", "Sulfites", "Céleri", "Moutarde"],
        "Légume":          ["Céleri", "Gluten", "Sulfites", "Soja", "Lupin", "Moutarde"],
        "Fruit":           ["Fruits à coque", "Sulfites", "Arachides", "Soja"],
        "Céréale":         ["Gluten", "Soja", "Fruits à coque", "Arachides", "Lupin"],
        "Produit laitier": ["Lactose", "Gluten", "Oeufs"],
        "Épice":           ["Moutarde", "Sésame", "Sulfites", "Céleri", "Gluten"],
        "Légumineuse":     ["Arachides", "Soja", "Lupin", "Gluten", "Sulfites", "Céleri"],
        "Champignon":      ["Sulfites", "Céleri", "Gluten"],
        "Herbe":           ["Céleri", "Sulfites", "Gluten"],
    }
    candidats = _ALLERGENES_PAR_TYPE.get(type_aliment, ["Gluten", "Sulfites", "Céleri"])
    k = _RNG.randint(0, min(3, len(candidats)))
    return (", ".join(_RNG.sample(candidats, k)) if k else "Aucun")[:50]

def _nom_machine() -> str:
    types = ["Presse", "Tour", "Fraiseuse", "Perceuse", "Robot", "Convoyeur",
             "Étuve", "Malaxeur", "Broyeur", "Centrifugeuse"]
    return f"{_RNG.choice(types)}-{_RNG.randint(100,999)}"[:50]

def _nom_modele() -> str:
    return f"MOD-{_RNG.choice(string.ascii_uppercase)}{_RNG.randint(1000,9999)}"[:50]

def _nom_membre() -> str:
    if _FAKER:
        return _FAKER.name()[:100]
    return _nom_chevalier()[:100]

def _courriel() -> str:
    if _FAKER:
        return _FAKER.email()[:50]
    domains = ["chevalerie.fr", "ordre.eu", "table-ronde.com", "preux.org"]
    return f"user{_RNG.randint(1000,99999)}@{_RNG.choice(domains)}"[:50]

def _num_tel() -> str:
    if _FAKER:
        return _FAKER.phone_number()[:20]
    return f"+33{_RNG.randint(100000000,999999999)}"[:20]

def _nom_orga() -> str:
    if _FAKER:
        return _FAKER.company()[:50]
    return _raison_sociale()[:50]

# ---------------------------------------------------------------------------
# Générateurs de tables
# ---------------------------------------------------------------------------

def gen_grade():
    """Exactement 10 grades nommés — jamais plus."""
    yield from GRADES

def gen_titre():
    """Exactement 10 titres nommés — jamais plus."""
    yield from TITRES

def gen_dignite():
    """Exactement 10 dignités nommées — jamais plus."""
    yield from DIGNITES

def gen_rang():
    """Exactement 10 rangs nommés — jamais plus."""
    yield from RANGS

def gen_organisme(n: int):
    """SIRET unique, raison_sociale cohérente."""
    seen = set()
    i = 0
    while i < n:
        s = _siret()
        if s in seen:
            continue
        seen.add(s)
        yield (s, _raison_sociale())
        i += 1

def gen_territoire(n: int):
    for i in range(1, n + 1):
        yield (i, _nom_territoire())

def gen_repas(n: int):
    """Dates concentrées printemps/automne avec tendance croissante dans le temps."""
    for i in range(1, n + 1):
        yield (i, _nom_repas(), _rand_date_repas(), _adresse(), _nom_chevalier())

def gen_composant(n: int):
    """
    Type_aliment cohérent avec le nom ET distribué selon POIDS_CATALOGUE
    (épices et herbes majoritaires, poisson et produit laitier rares).
    """
    # Construire la liste pondérée une seule fois
    types_disponibles = list(POIDS_CATALOGUE.keys())
    poids_liste       = list(POIDS_CATALOGUE.values())

    # Regrouper le catalogue par type pour le tirage pondéré
    catalogue_par_type: dict[str, list[str]] = {}
    for nom_base, type_ali in COMPOSANTS_CATALOGUE:
        catalogue_par_type.setdefault(type_ali, []).append(nom_base)

    for i in range(1, n + 1):
        # Tirer le type selon les poids
        type_aliment = _RNG.choices(types_disponibles, weights=poids_liste, k=1)[0]
        # Tirer un nom dans ce type (fallback si le type n'a pas de nom dédié)
        noms_dispo = catalogue_par_type.get(type_aliment, ["Composant"])
        nom_base   = _RNG.choice(noms_dispo)
        nom        = f"{nom_base} #{_RNG.randint(1, 999)}"[:50]
        yield (i, type_aliment, nom, _allergene(type_aliment))

def gen_sauce(n: int, max_idc: int):
    """PK propre idS, FK vers composant."""
    idc_pool = list(range(1, max_idc + 1))
    _RNG.shuffle(idc_pool)
    for i, idc in enumerate(idc_pool[:n], start=1):
        yield (i, idc)

def gen_ingredient(n: int, max_idc: int):
    """PK propre idI, FK vers composant."""
    idc_pool = list(range(1, max_idc + 1))
    _RNG.shuffle(idc_pool)
    for i, idc in enumerate(idc_pool[:n], start=1):
        yield (i, idc)

def gen_legume(n: int):
    """Noms de légumes cohérents tirés d'une liste fixe."""
    for i in range(1, n + 1):
        yield (i, _RNG.randint(0, 1), _RNG.choice(LEGUMES))

def gen_machine(n: int):
    for i in range(1, n + 1):
        yield (i, _nom_machine())

def gen_modele(n: int):
    for i in range(1, n + 1):
        yield (i, _nom_modele())

def gen_organisation(n: int, max_idt: int):
    """type_orga distribué selon POIDS_ORGA (Club/Association majoritaires, Ordre/Fraternité rares)."""
    for i in range(1, n + 1):
        type_orga = _RNG.choices(TYPES_ORGA, weights=POIDS_ORGA, k=1)[0]
        yield (i, _nom_orga()[:50], type_orga, _RNG.randint(1, max_idt))

def gen_ordre(n: int, orga_ids: list):
    pool = orga_ids[:]
    _RNG.shuffle(pool)
    for i, ido in enumerate(pool[:n], start=1):
        yield (i, ido)

def gen_club(n: int, orga_ids: list, ordre_orga_ids: list):
    seen = set()
    i = 0
    attempts = 0
    while i < n and attempts < n * 10:
        attempts += 1
        ido    = _RNG.choice(orga_ids)
        parent = _RNG.choice(ordre_orga_ids) if _RNG.random() > 0.2 else None
        if ido in seen or parent == ido:
            continue
        seen.add(ido)
        yield (i + 1, ido, parent)
        i += 1

def gen_membre(n: int):
    """
    CodeMembre : entier auto-incrémenté.
    IdGr       : distribution pyramidale — 30% Apprenti, 1% Chancelier.
    IdD, IdTi, IdRa : optionnels, distribués uniformément sur 1..10.
    """
    ids_grades = [g[0] for g in GRADES]   # [1, 2, ..., 10]
    for i in range(1, n + 1):
        yield (
            i,
            _nom_membre(),
            _adresse(),
            _courriel(),
            _num_tel(),
            _RNG.randint(1, 10) if _RNG.random() > 0.1 else None,
            _RNG.randint(1, 10) if _RNG.random() > 0.1 else None,
            _RNG.randint(1, 10) if _RNG.random() > 0.1 else None,
            _RNG.choices(ids_grades, weights=POIDS_GRADES, k=1)[0],   # pyramide
        )

def gen_groupe(n: int, max_idr: int):
    for i in range(1, n + 1):
        yield (i, _RNG.randint(1, max_idr))

def gen_plat(n: int, max_idl: int):
    for i in range(1, n + 1):
        yield (i, _RNG.randint(1, max_idl) if _RNG.random() > 0.15 else None)

def gen_entretien(n: int, max_codemembre: int, dates_repas: list):
    """
    60% des entretiens ont lieu dans les 30 jours suivant un repas (corrélation).
    40% ont une date indépendante.
    """
    for i in range(1, n + 1):
        if dates_repas and _RNG.random() < 0.60:
            date_base = _RNG.choice(dates_repas)
            date_cert = _date_apres_repas(date_base)
        else:
            date_cert = _rand_date()
        yield (i, date_cert, _RNG.randint(1, max_codemembre))

# ---------------------------------------------------------------------------
# Tables d'association
# ---------------------------------------------------------------------------

def _assoc(keys_a, keys_b, n: int):
    seen = set()
    i = 0
    attempts = 0
    while i < n and attempts < n * 20:
        attempts += 1
        a = _RNG.choice(keys_a)
        b = _RNG.choice(keys_b)
        if (a, b) not in seen:
            seen.add((a, b))
            yield (a, b)
            i += 1

def gen_est_affilie(codes, sirets, n):   yield from _assoc(codes, sirets, n)
def gen_adhere(codes, orga_ids, n):      yield from _assoc(codes, orga_ids, n)
def gen_appartient(codes, grp_ids, n):   yield from _assoc(codes, grp_ids, n)
def gen_contient(repas_ids, plat_ids, n): yield from _assoc(repas_ids, plat_ids, n)
def gen_est_organise(codes, repas_ids, n): yield from _assoc(codes, repas_ids, n)
def gen_est_compose(plat_ids, comp_ids, n): yield from _assoc(plat_ids, comp_ids, n)
def gen_comporte(sauce_ids, ingred_ids, n): yield from _assoc(sauce_ids, ingred_ids, n)
def gen_est(machine_ids, modele_ids, n):  yield from _assoc(machine_ids, modele_ids, n)
def gen_participe(repas_ids, mach_ids, n): yield from _assoc(repas_ids, mach_ids, n)
def gen_effectue(mach_ids, entr_ids, n):  yield from _assoc(mach_ids, entr_ids, n)

def gen_historique_entretien(orga_ids, machine_ids, entret_ids, n):
    seen = set()
    i = 0
    attempts = 0
    while i < n and attempts < n * 20:
        attempts += 1
        o = _RNG.choice(orga_ids)
        m = _RNG.choice(machine_ids)
        e = _RNG.choice(entret_ids)
        key = (o, m, e)
        if key not in seen:
            seen.add(key)
            yield (*key, _rand_date())
            i += 1

# ---------------------------------------------------------------------------
# Schéma
# ---------------------------------------------------------------------------

HEADERS = {
    "Organisme":             ["SIRET", "raison_sociale"],
    "territoire":            ["IdT", "nom_territoire"],
    "Repas":                 ["IdR", "nom_repas", "date_repas", "adr_repas", "nom_chevalier_dame"],
    "grade":                 ["IdGr", "libelle"],
    "Titre":                 ["IdTi", "libelle"],
    "Dignite":               ["IdD", "libelle"],
    "rang":                  ["IdRa", "libelle"],
    "composant":             ["IdC", "type_aliment", "nom", "allergene"],
    "Sauce":                 ["idS", "IdC"],
    "Ingredient":            ["idI", "IdC"],
    "Legume":                ["IdL", "verifie", "nom"],
    "machine":               ["IdM", "nom"],
    "modele":                ["IdMo", "nom_modele"],
    "Membre":                ["CodeMembre", "nom_membre", "adresse", "courriel",
                              "num_tel", "IdD", "IdTi", "IdRa", "IdGr"],
    "organisation":          ["IdO", "nom_orga", "type_orga", "IdT"],
    "Groupe":                ["IdG", "IdR"],
    "plat":                  ["IdP", "IdL"],
    "Entretien":             ["IdE", "certificat_entretien", "CodeMembre"],
    "Ordre":                 ["IdOrdre", "IdO"],
    "Club":                  ["IdClub", "IdO", "IdO_parent"],
    "est_affilie":           ["CodeMembre", "SIRET"],
    "adhere":                ["CodeMembre", "IdO"],
    "Appartient":            ["CodeMembre", "IdG"],
    "contient":              ["IdR", "IdP"],
    "est_organise":          ["CodeMembre", "IdR"],
    "est_compose":           ["IdP", "IdC"],
    "Comporte":              ["idS", "idI"],
    "Est":                   ["IdM", "IdMo"],
    "Historique_entretien":  ["IdO", "IdM", "IdE", "date_entretien"],
    "Participe":             ["IdR", "IdM"],
    "Effectue":              ["IdM", "IdE"],
}

# ---------------------------------------------------------------------------
# Sérialisation
# ---------------------------------------------------------------------------

def write_csv(table, rows, out_dir):
    path = out_dir / f"{table}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADERS[table])
        w.writerows(rows)
    return path

def write_sql(table, rows, out_dir):
    path = out_dir / f"{table}.sql"
    cols = ", ".join(HEADERS[table])
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            vals = ", ".join(
                "NULL" if v is None
                else str(v) if isinstance(v, (int, float))
                else "'" + str(v).replace("'", "''") + "'"
                for v in row
            )
            f.write(f"INSERT INTO {table} ({cols}) VALUES ({vals});\n")
    return path

def write_json(table, rows, out_dir):
    path = out_dir / f"{table}.json"
    headers = HEADERS[table]
    with path.open("w", encoding="utf-8") as f:
        f.write("[\n")
        first = True
        for row in rows:
            obj = dict(zip(headers, row))
            if not first:
                f.write(",\n")
            f.write("  " + json.dumps(obj, ensure_ascii=False, default=str))
            first = False
        f.write("\n]\n")
    return path

WRITERS = {"csv": write_csv, "sql": write_sql, "json": write_json}

# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def build_all(n: int, output: str, out_dir: Path, tables_filter=None):
    out_dir.mkdir(parents=True, exist_ok=True)
    writer = WRITERS[output]

    def should(name):
        return tables_filter is None or name in tables_filter

    # Volumes : les lookup tables sont fixes (10), les autres s'adaptent à n
    n_ref  = max(100, min(n // 10, 5000))
    n_main = n

    stats = {}

    def run(name, gen):
        if not should(name):
            return []
        t0 = time.time()
        rows = list(gen)
        elapsed = time.time() - t0
        path = writer(name, rows, out_dir)
        stats[name] = {"rows": len(rows), "time_s": round(elapsed, 3)}
        print(f"  ✓ {name:<28} {len(rows):>9,} lignes  ({elapsed:.2f}s)  → {path.name}")
        return rows

    print(f"\n{'='*62}")
    print(f"  Génération MLD v3 — format={output}, n={n:,}")
    print(f"  Dossier : {out_dir.resolve()}")
    print(f"{'='*62}")

    # ---- Tables lookup : exactement 10 valeurs nommées chacune ----
    run("grade",   gen_grade())
    run("Titre",   gen_titre())
    run("Dignite", gen_dignite())
    run("rang",    gen_rang())

    # ---- Entités de référence ----
    territoires = run("territoire",   gen_territoire(n_ref))
    repas_rows  = run("Repas",        gen_repas(n_ref))
    composants  = run("composant",    gen_composant(n_ref))
    legumes     = run("Legume",       gen_legume(n_ref))
    machines    = run("machine",      gen_machine(n_ref))
    modeles     = run("modele",       gen_modele(n_ref))
    organisatns = run("organisation", gen_organisation(n_ref, max(1, len(territoires))))
    organismes  = run("Organisme",    gen_organisme(n_ref))

    # ---- Sous-types ----
    n_sous = max(50, n_ref // 2)
    sauces      = run("Sauce",      gen_sauce(n_sous, max(1, len(composants))))
    ingredients = run("Ingredient", gen_ingredient(n_sous, max(1, len(composants))))

    orga_ids       = [r[0] for r in organisatns] or [1]
    ordre_rows     = run("Ordre", gen_ordre(max(5, len(orga_ids) // 5), orga_ids))
    ordre_orga_ids = [r[1] for r in ordre_rows] if ordre_rows else orga_ids[:1]
    run("Club", gen_club(max(10, len(orga_ids) // 3), orga_ids, ordre_orga_ids))

    # ---- Tables principales ----
    membres_rows = run("Membre", gen_membre(n_main))
    codes        = list(range(1, n_main + 1))

    groupes = run("Groupe", gen_groupe(n_ref, max(1, len(repas_rows))))
    plats   = run("plat",   gen_plat(n_ref, max(1, len(legumes))))
    dates_repas = [r[2] for r in repas_rows] if repas_rows else []
    entrets = run("Entretien", gen_entretien(n_ref, n_main, dates_repas))

    # ---- Clés ----
    sirets      = [r[0] for r in organismes] or [1234567890]
    repas_ids   = [r[0] for r in repas_rows] or [1]
    comp_ids    = [r[0] for r in composants] or [1]
    plat_ids    = [r[0] for r in plats] or [1]
    groupe_ids  = [r[0] for r in groupes] or [1]
    machine_ids = [r[0] for r in machines] or [1]
    modele_ids  = [r[0] for r in modeles] or [1]
    entret_ids  = [r[0] for r in entrets] or [1]
    sauce_ids   = [r[0] for r in sauces] or [1]
    ingred_ids  = [r[0] for r in ingredients] or [1]

    # ---- Associations ----
    run("est_affilie",          gen_est_affilie(codes, sirets, n_main))
    run("adhere",               gen_adhere(codes, orga_ids, n_main))
    run("Appartient",           gen_appartient(codes, groupe_ids, n_main))
    run("contient",             gen_contient(repas_ids, plat_ids, n_main))
    run("est_organise",         gen_est_organise(codes, repas_ids, n_main))
    run("est_compose",          gen_est_compose(plat_ids, comp_ids, n_main))
    run("Comporte",             gen_comporte(sauce_ids, ingred_ids, n_ref))
    run("Est",                  gen_est(machine_ids, modele_ids, n_ref))
    run("Historique_entretien", gen_historique_entretien(orga_ids, machine_ids, entret_ids, n_ref))
    run("Participe",            gen_participe(repas_ids, machine_ids, n_ref))
    run("Effectue",             gen_effectue(machine_ids, entret_ids, n_ref))

    total_rows = sum(v["rows"] for v in stats.values())
    total_time = sum(v["time_s"] for v in stats.values())
    print(f"\n{'='*62}")
    print(f"  Total : {total_rows:,} tuples  |  {total_time:.2f}s  |  {len(stats)} tables")
    print(f"  Dossier : {out_dir.resolve()}")
    print(f"{'='*62}\n")
    return stats

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Faker MLD v3 — données propres sans fix nécessaire"
    )
    parser.add_argument("--rows",    type=int, default=1_000,
                        help="Tuples cibles pour les tables principales (1–1 000 000)")
    parser.add_argument("--output",  choices=["csv", "sql", "json"], default="csv")
    parser.add_argument("--out-dir", default="./faker_output_v3")
    parser.add_argument("--table",   default=None,
                        help="Générer une seule table (nom exact)")
    parser.add_argument("--seed",    type=int, default=None,
                        help="Graine aléatoire pour reproductibilité")
    args = parser.parse_args()

    if not (1 <= args.rows <= 1_000_000):
        print("[ERREUR] --rows doit être compris entre 1 et 1 000 000", file=sys.stderr)
        sys.exit(1)

    if args.seed is not None:
        _RNG.seed(args.seed)
        if _FAKER:
            _FakerLib.seed(args.seed)

    build_all(
        n=args.rows,
        output=args.output,
        out_dir=Path(args.out_dir),
        tables_filter=[args.table] if args.table else None,
    )

if __name__ == "__main__":
    main()
