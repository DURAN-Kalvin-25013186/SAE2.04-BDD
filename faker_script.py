"""
Faker MLD v2 — Générateur de données de test (MLD corrigé)
Génère jusqu'à 1 000 000 de tuples pour chaque table.

Corrections prises en compte :
  - Sauce et Ingrédient ont chacune leur propre PK (idS, idI)
  - Comporte lie Sauce ↔ Ingrédient (plus d'autoréférence ambiguë)
  - Légume reste indépendant, référencé optionnellement par plat
  - Club a sa propre PK (IdClub) + FK vers organisation parente optionnelle
  - Ordre a sa propre PK (IdOrdre) + FK vers organisation
  - Historique_entretien a date_entretien DATE (plus VARCHAR)
  - grade/Titre/Dignité/rang ont un libellé
  - Entretien.certificat_entretien est DATE (pas TIMESTAMP)

Usage:
    python faker_mld_v2.py                          # 1 000 tuples (tables principales)
    python faker_mld_v2.py --rows 100000            # 100 000 tuples
    python faker_mld_v2.py --rows 1000000           # 1 million
    python faker_mld_v2.py --table Membre --rows 5000
    python faker_mld_v2.py --output sql             # INSERT SQL
    python faker_mld_v2.py --output json            # JSON
    python faker_mld_v2.py --output csv             # CSV (défaut)
    python faker_mld_v2.py --rows 500000 --out-dir ./data
"""

import argparse
import csv
import json
import os
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
# Générateurs de valeurs primitives
# ---------------------------------------------------------------------------

def _rand_date(start_year=2000, end_year=2024) -> str:
    start = date(start_year, 1, 1)
    delta = (date(end_year, 12, 31) - start).days
    return (start + timedelta(days=_RNG.randint(0, delta))).strftime("%Y-%m-%d")

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

# Libellés pour les tables de référence
_LIBELLES = {
    "grade":   ["Apprenti", "Compagnon", "Maître", "Grand Maître", "Archonte",
                "Sénéchal", "Connétable", "Maréchal", "Chambellan", "Chancelier"],
    "Titre":   ["Chevalier", "Dame", "Ecuyer", "Damoiselle", "Banneret",
                "Bachelier", "Paladin", "Preux", "Prude Femme", "Vassal"],
    "Dignite": ["Noble", "Roturier", "Bourgeois", "Anobli", "Vassal",
                "Suzerain", "Seigneur", "Baron", "Vicomte", "Comte"],
    "rang":    ["Premier rang", "Deuxième rang", "Troisième rang", "Rang d'honneur",
                "Rang de table", "Rang de cérémonie", "Rang militaire",
                "Rang civil", "Rang épiscopal", "Rang royal"],
}

def _libelle(table: str, i: int) -> str:
    opts = _LIBELLES.get(table, [])
    if opts and i <= len(opts):
        return opts[i - 1]
    return f"{table.capitalize()} #{i}"

def _type_aliment() -> str:
    return _RNG.choice(["Viande", "Poisson", "Légume", "Fruit", "Céréale",
                        "Produit laitier", "Épice", "Légumineuse", "Champignon", "Herbe"])

def _nom_composant() -> str:
    items = ["Agneau rôti", "Carpe dorée", "Navet confit", "Pomme sauvage",
             "Épeautre", "Fromage affiné", "Safran", "Lentilles du Puy",
             "Truffe noire", "Romarin", "Thym sauvage", "Poivre long",
             "Canard fumé", "Brochet en gelée", "Chou frisé",
             "Épices orientales", "Verjus", "Venaison", "Mouton braisé"]
    return (_RNG.choice(items) + f" #{_RNG.randint(1,999)}")[:50]

def _allergene() -> str:
    a = ["Gluten", "Lactose", "Arachides", "Fruits à coque", "Soja",
         "Œufs", "Poisson", "Crustacés", "Céleri", "Moutarde",
         "Sésame", "Sulfites", "Lupin", "Mollusques"]
    k = _RNG.randint(0, 3)
    return (", ".join(_RNG.sample(a, k)) if k else "Aucun")[:50]

def _nom_sauce() -> str:
    sauces = ["Cameline", "Verjus aux épices", "Galentine", "Sauce Robert",
              "Jance au gingembre", "Dodine blanche", "Sauce noire",
              "Aigre-doux médiéval", "Coulis d'herbes", "Hypocras réduit"]
    return (_RNG.choice(sauces) + f" #{_RNG.randint(1,999)}")[:50]

def _nom_ingredient() -> str:
    ingredients = ["Fleur de sel", "Poivre long", "Gingembre frais",
                   "Cannelle", "Muscade", "Clou de girofle", "Safran",
                   "Verjus", "Vinaigre de vin", "Miel sauvage",
                   "Persil plat", "Ail nouveau", "Oignon blanc"]
    return (_RNG.choice(ingredients) + f" #{_RNG.randint(1,999)}")[:50]

def _nom_legume() -> str:
    legumes = ["Carotte", "Navet", "Panais", "Poireau", "Chou", "Betterave",
               "Raifort", "Salsifis", "Artichaut", "Topinambour", "Ail", "Oignon"]
    return _RNG.choice(legumes)

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
    user = f"user{_RNG.randint(1000,99999)}"
    return f"{user}@{_RNG.choice(domains)}"[:50]

def _num_tel() -> str:
    if _FAKER:
        return _FAKER.phone_number()[:20]
    return f"+33{_RNG.randint(100000000,999999999)}"[:20]

def _nom_orga() -> str:
    if _FAKER:
        return _FAKER.company()[:50]
    return _raison_sociale()[:50]

def _type_orga() -> str:
    return _RNG.choice(["Ordre", "Club", "Association", "Confrérie",
                        "Guilde", "Loge", "Cercle", "Fraternité"])

# ---------------------------------------------------------------------------
# Générateurs de tables
# ---------------------------------------------------------------------------

def gen_organisme(n: int):
    """SIRET NUMBER(10), raison_sociale VARCHAR2(50)"""
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
    """IdT NUMBER(10), nom_territoire VARCHAR2(50)"""
    for i in range(1, n + 1):
        yield (i, _nom_territoire())

def gen_repas(n: int):
    """IdR, nom_repas, date_repas DATE, adr_repas, nom_chevalier_dame"""
    for i in range(1, n + 1):
        yield (i, _nom_repas(), _rand_date(), _adresse(), _nom_chevalier())

def gen_grade(n: int):
    """IdGr NUMBER(10), libelle VARCHAR2(50)"""
    for i in range(1, n + 1):
        yield (i, _libelle("grade", i))

def gen_titre(n: int):
    """IdTi NUMBER(10), libelle VARCHAR2(50)"""
    for i in range(1, n + 1):
        yield (i, _libelle("Titre", i))

def gen_dignite(n: int):
    """IdD NUMBER(10), libelle VARCHAR2(50)"""
    for i in range(1, n + 1):
        yield (i, _libelle("Dignite", i))

def gen_rang(n: int):
    """IdRa NUMBER(10), libelle VARCHAR2(50)"""
    for i in range(1, n + 1):
        yield (i, _libelle("rang", i))

def gen_composant(n: int):
    """IdC, type_aliment, nom, allergene"""
    for i in range(1, n + 1):
        yield (i, _type_aliment(), _nom_composant(), _allergene())

def gen_sauce(n: int, max_idc: int):
    """idS NUMBER(10), #IdC — PK propre, FK vers composant"""
    idc_pool = list(range(1, max_idc + 1))
    _RNG.shuffle(idc_pool)
    for i, idc in enumerate(idc_pool[:n], start=1):
        yield (i, idc)

def gen_ingredient(n: int, max_idc: int):
    """idI NUMBER(10), #IdC — PK propre, FK vers composant"""
    idc_pool = list(range(1, max_idc + 1))
    _RNG.shuffle(idc_pool)
    for i, idc in enumerate(idc_pool[:n], start=1):
        yield (i, idc)

def gen_legume(n: int):
    """IdL NUMBER(10), verifie NUMBER(1), nom VARCHAR2(50)"""
    for i in range(1, n + 1):
        yield (i, _RNG.randint(0, 1), _nom_legume()[:50])

def gen_machine(n: int):
    """IdM NUMBER(10), nom VARCHAR2(50)"""
    for i in range(1, n + 1):
        yield (i, _nom_machine())

def gen_modele(n: int):
    """IdMo NUMBER(10), nom_modele VARCHAR2(50)"""
    for i in range(1, n + 1):
        yield (i, _nom_modele())

def gen_membre(n: int, max_idd: int, max_idti: int, max_idra: int, max_idgr: int):
    """CodeMembre, nom_membre, adresse, courriel, num_tel, #IdD*, #IdTi*, #IdRa*, #IdGr"""
    for i in range(1, n+1):
        yield (	
            i,
            _nom_membre(),
            _adresse(),
            _courriel(),
            _num_tel(),
            _RNG.randint(1, max_idd)  if _RNG.random() > 0.1 else None,   # IdD optionnel
            _RNG.randint(1, max_idti) if _RNG.random() > 0.1 else None,   # IdTi optionnel
            _RNG.randint(1, max_idra) if _RNG.random() > 0.1 else None,   # IdRa optionnel
            _RNG.randint(1, max_idgr),                                      # IdGr obligatoire
        )
        i += 1

def gen_organisation(n: int, max_idt: int):
    """IdO, nom_orga, type_orga, #IdT"""
    for i in range(1, n + 1):
        yield (i, _nom_orga(), _type_orga(), _RNG.randint(1, max_idt))

def gen_ordre(n: int, orga_ids: list):
    """IdOrdre NUMBER(10), #IdO — PK propre, FK vers organisation"""
    pool = orga_ids[:]
    _RNG.shuffle(pool)
    for i, ido in enumerate(pool[:n], start=1):
        yield (i, ido)

def gen_club(n: int, orga_ids: list, ordre_ids_orga: list):
    """IdClub NUMBER(10), #IdO, #IdO_parent* — PK propre, lien vers orga parente optionnel"""
    seen_ido = set()
    i = 0
    attempts = 0
    while i < n and attempts < n * 10:
        attempts += 1
        ido = _RNG.choice(orga_ids)
        if ido in seen_ido:
            continue
        seen_ido.add(ido)
        parent = _RNG.choice(ordre_ids_orga) if _RNG.random() > 0.2 else None
        if parent == ido:
            continue
        yield (i + 1, ido, parent)
        i += 1

def gen_groupe(n: int, max_idr: int):
    """IdG NUMBER(10), #IdR"""
    for i in range(1, n + 1):
        yield (i, _RNG.randint(1, max_idr))

def gen_plat(n: int, max_idl: int):
    """IdP NUMBER(10), #IdL*"""
    for i in range(1, n + 1):
        yield (i, _RNG.randint(1, max_idl) if _RNG.random() > 0.15 else None)

def gen_entretien(n: int, codes: list):
    """IdE NUMBER(10), certificat_entretien DATE, #CodeMembre"""
    for i in range(1, n + 1):
        yield (i, _rand_date(), _RNG.choice(codes))

# ---------------------------------------------------------------------------
# Tables d'association
# ---------------------------------------------------------------------------

def _assoc(keys_a, keys_b, n: int):
    """Génère n paires (a, b) uniques sans répétition."""
    seen = set()
    i = 0
    attempts = 0
    limit = n * 20
    while i < n and attempts < limit:
        attempts += 1
        a = _RNG.choice(keys_a)
        b = _RNG.choice(keys_b)
        if (a, b) not in seen:
            seen.add((a, b))
            yield (a, b)
            i += 1

def gen_est_affilie(codes, sirets, n):
    yield from _assoc(codes, sirets, n)

def gen_adhere(codes, orga_ids, n):
    yield from _assoc(codes, orga_ids, n)

def gen_appartient(codes, groupe_ids, n):
    yield from _assoc(codes, groupe_ids, n)

def gen_contient(repas_ids, plat_ids, n):
    yield from _assoc(repas_ids, plat_ids, n)

def gen_est_organise(codes, repas_ids, n):
    yield from _assoc(codes, repas_ids, n)

def gen_est_compose(plat_ids, comp_ids, n):
    yield from _assoc(plat_ids, comp_ids, n)

def gen_comporte(sauce_ids, ingredient_ids, n):
    """Comporte(#idS, #idI) — Sauce ↔ Ingrédient (plus d'autoréférence)"""
    yield from _assoc(sauce_ids, ingredient_ids, n)

def gen_est(machine_ids, modele_ids, n):
    """Est(#IdM, #IdMo)"""
    yield from _assoc(machine_ids, modele_ids, n)

def gen_historique_entretien(orga_ids, machine_ids, entretien_ids, n):
    """Historique_entretien(#IdO, #IdM, #IdE, date_entretien DATE)"""
    seen = set()
    i = 0
    attempts = 0
    while i < n and attempts < n * 20:
        attempts += 1
        o = _RNG.choice(orga_ids)
        m = _RNG.choice(machine_ids)
        e = _RNG.choice(entretien_ids)
        key = (o, m, e)
        if key not in seen:
            seen.add(key)
            yield (*key, _rand_date())
            i += 1

def gen_participe(repas_ids, machine_ids, n):
    yield from _assoc(repas_ids, machine_ids, n)

def gen_effectue(machine_ids, entretien_ids, n):
    yield from _assoc(machine_ids, entretien_ids, n)

# ---------------------------------------------------------------------------
# Schéma : en-têtes CSV / JSON
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

def write_csv(table: str, rows, out_dir: Path):
    path = out_dir / f"{table}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS[table])
        writer.writerows(rows)
    return path

def write_sql(table: str, rows, out_dir: Path):
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

def write_json(table: str, rows, out_dir: Path):
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

    # Calibration des volumes
    n_lu   = max(10, min(n // 100, 500))    # lookup tables (grade, titre…)
    n_ref  = max(100, min(n // 10, 5000))   # entités de référence
    n_main = n                               # tables principales

    stats = {}

    def run(name, gen):
        if not should(name):
            return []
        t0 = time.time()
        rows = list(gen)
        elapsed = time.time() - t0
        path = writer(name, rows, out_dir)
        stats[name] = {"rows": len(rows), "time_s": round(elapsed, 3), "file": str(path)}
        print(f"  ✓ {name:<28} {len(rows):>9,} lignes  ({elapsed:.2f}s)  → {path.name}")
        return rows

    print(f"\n{'='*62}")
    print(f"  Génération MLD v2 — format={output}, n={n:,}")
    print(f"  Dossier : {out_dir.resolve()}")
    print(f"{'='*62}")

    # ---- Tables lookup (libellés) ----
    grades   = run("grade",   gen_grade(n_lu))
    titres   = run("Titre",   gen_titre(n_lu))
    dignites = run("Dignite", gen_dignite(n_lu))
    rangs    = run("rang",    gen_rang(n_lu))

    # ---- Entités de référence ----
    territoires = run("territoire", gen_territoire(n_ref))
    repas_rows  = run("Repas",      gen_repas(n_ref))
    composants  = run("composant",  gen_composant(n_ref))
    legumes     = run("Legume",     gen_legume(n_ref))
    machines    = run("machine",    gen_machine(n_ref))
    modeles     = run("modele",     gen_modele(n_ref))
    organisatns = run("organisation", gen_organisation(n_ref, max(1, len(territoires))))
    organismes  = run("Organisme",  gen_organisme(n_ref))

    # ---- Sous-types avec PK propre ----
    sauces      = run("Sauce",      gen_sauce(n_lu * 5, max(1, len(composants))))
    ingredients = run("Ingredient", gen_ingredient(n_lu * 5, max(1, len(composants))))

    orga_ids    = [r[0] for r in organisatns] or [1]
    ordre_rows  = run("Ordre", gen_ordre(max(5, n_lu), orga_ids))
    ordre_orga_ids = [r[1] for r in ordre_rows] if ordre_rows else orga_ids[:1]

    club_rows   = run("Club",  gen_club(max(10, n_lu * 2), orga_ids, ordre_orga_ids))

    # ---- Tables principales ----
    membres_rows = run("Membre", gen_membre(
        n_main,
        max(1, len(dignites)),
        max(1, len(titres)),
        max(1, len(rangs)),
        max(1, len(grades)),
    ))

    groupes  = run("Groupe",   gen_groupe(n_ref, max(1, len(repas_rows))))
    plats    = run("plat",     gen_plat(n_ref, max(1, len(legumes))))
    codes    = [r[0] for r in membres_rows] or [0]
    entrets  = run("Entretien", gen_entretien(n_ref, codes))

    # ---- Clés pour les associations ----
    sirets       = [r[0] for r in organismes] or [1234567890]
    repas_ids    = [r[0] for r in repas_rows] or [1]
    comp_ids     = [r[0] for r in composants] or [1]
    plat_ids     = [r[0] for r in plats] or [1]
    groupe_ids   = [r[0] for r in groupes] or [1]
    machine_ids  = [r[0] for r in machines] or [1]
    modele_ids   = [r[0] for r in modeles] or [1]
    entret_ids   = [r[0] for r in entrets] or [1]
    sauce_ids    = [r[0] for r in sauces] or [1]
    ingred_ids   = [r[0] for r in ingredients] or [1]

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

    # ---- Résumé ----
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
        description="Faker MLD v2 — données de test pour le MLD chevalerie corrigé"
    )
    parser.add_argument("--rows",    type=int,   default=1_000,
                        help="Tuples cibles pour les tables principales (1–1 000 000)")
    parser.add_argument("--output",  choices=["csv", "sql", "json"], default="csv")
    parser.add_argument("--out-dir", type=str,   default="./faker_output_v2")
    parser.add_argument("--table",   type=str,   default=None,
                        help="Générer une seule table (nom exact)")
    parser.add_argument("--seed",    type=int,   default=None,
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
