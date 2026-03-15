"""
hs_algobar.py — Algorytm Harmony Search dla receptury ALGO-BAR
===============================================================
Zapisuje wynik do wynik_hs.json oraz pamięć startową do hm_inicjalizacja.csv.

Użycie:
    python hs_algobar.py
    python hs_algobar.py --pamiec 30 --improwizacje 20000 --ziarno 42
"""

import json, csv, argparse, time
from pathlib import Path
import numpy as np

# ─────────────────────────────────────────────────────────────
# DANE SUROWCÓW
# ─────────────────────────────────────────────────────────────
SKLADNIKI = {
    "izolat": {"bialko": 0.90, "tluszcz": 0.00, "cena": 18.00, "min": 10, "max": 40},
    "pasta":  {"bialko": 0.25, "tluszcz": 0.50, "cena":  6.00, "min": 15, "max": 40},
    "syrop":  {"bialko": 0.00, "tluszcz": 0.00, "cena":  2.50, "min": 15, "max": 35},
    "quinoa": {"bialko": 0.14, "tluszcz": 0.06, "cena":  5.50, "min":  5, "max": 25},
}

NAZWY       = list(SKLADNIKI.keys())
N_ZMIENNYCH = len(NAZWY)
MASA_BATONA = 100.0
MIN_BIALKO  = 20.0
MAX_TLUSZCZ = 20.0

DolneGranice = np.array([SKLADNIKI[k]["min"]     for k in NAZWY], dtype=float)
GorneGranice = np.array([SKLADNIKI[k]["max"]     for k in NAZWY], dtype=float)
BIALKO       = np.array([SKLADNIKI[k]["bialko"]  for k in NAZWY], dtype=float)
TLUSZCZ      = np.array([SKLADNIKI[k]["tluszcz"] for k in NAZWY], dtype=float)
CENA         = np.array([SKLADNIKI[k]["cena"]    for k in NAZWY], dtype=float)

# ─────────────────────────────────────────────────────────────
# FUNKCJE POMOCNICZE
# ─────────────────────────────────────────────────────────────
def koszt(x: np.ndarray) -> float:
    return float(np.dot(x, CENA) / 100.0)

def bialko(x: np.ndarray) -> float:
    return float(np.dot(x, BIALKO))

def tluszcz(x: np.ndarray) -> float:
    return float(np.dot(x, TLUSZCZ))

def czy_poprawny(x: np.ndarray) -> bool:
    if np.any(x < DolneGranice) or np.any(x > GorneGranice):
        return False
    if abs(x.sum() - MASA_BATONA) > 0.5:
        return False
    if bialko(x) < MIN_BIALKO:
        return False
    if tluszcz(x) > MAX_TLUSZCZ:
        return False
    return True

def funkcja_celu(x: np.ndarray) -> float:
    """Koszt + kara za naruszenie ograniczeń."""
    k = koszt(x)
    if czy_poprawny(x):
        return k
    kara  = max(0.0, MIN_BIALKO  - bialko(x))  * 0.5
    kara += max(0.0, tluszcz(x)  - MAX_TLUSZCZ) * 0.5
    kara += abs(x.sum() - MASA_BATONA)           * 0.1
    return k + kara

def losowa_poprawna(rng: np.random.Generator) -> np.ndarray:
    """Losuje recepturę spełniającą wszystkie ograniczenia."""
    for _ in range(200_000):
        x1 = rng.uniform(DolneGranice[0], GorneGranice[0])
        x2 = rng.uniform(DolneGranice[1], GorneGranice[1])
        x4 = rng.uniform(DolneGranice[3], GorneGranice[3])
        x3 = MASA_BATONA - x1 - x2 - x4
        if DolneGranice[2] <= x3 <= GorneGranice[2]:
            x = np.array([x1, x2, x3, x4])
            if czy_poprawny(x):
                return x
    return np.array([25.0, 30.0, 30.0, 15.0])  # punkt awaryjny

# ─────────────────────────────────────────────────────────────
# ALGORYTM HARMONY SEARCH
# ─────────────────────────────────────────────────────────────
def harmonia_search(
    pamiec:       int   = 20,
    wsp_pamiec:   float = 0.90,
    wsp_korekta:  float = 0.30,
    szer_pasmo:   float = 0.05,
    improwizacje: int   = 10_000,
    ziarno:       int   = 42,
    log_co:       int   = 1_000,
) -> dict:
    """
    Harmony Search — minimalizacja kosztu receptury ALGO-BAR.

    Parametry
    ---------
    pamiec        HMS  — rozmiar pamięci harmonii
    wsp_pamiec    HMCR — współczynnik uwzględnienia pamięci (0–1)
    wsp_korekta   PAR  — współczynnik korekty dźwięku (0–1)
    szer_pasmo    BW   — szerokość pasma korekty (% zakresu)
    improwizacje  NI   — liczba improwizacji
    ziarno              ziarno generatora losowego
    """
    rng    = np.random.default_rng(ziarno)
    zakresy = GorneGranice - DolneGranice

    # ── Krok 1: Inicjalizacja pamięci harmonii ────────────────
    print(f"[HS] Inicjalizacja pamięci harmonii (HMS={pamiec})...")
    PamiecH  = np.array([losowa_poprawna(rng) for _ in range(pamiec)])
    KosztyH  = np.array([funkcja_celu(x) for x in PamiecH])

    zapisz_pamiec_csv(PamiecH, KosztyH, "hm_inicjalizacja.csv")
    print("[HS] Pamięć startowa zapisana → hm_inicjalizacja.csv")

    zbieznosc = np.zeros(improwizacje)
    t_start   = time.time()
    print(f"[HS] Start: {improwizacje:,} improwizacji...\n")

    # ── Kroki 2–4: Pętla główna ───────────────────────────────
    for it in range(improwizacje):

        # Improwizacja nowej harmonii
        nowa_x = np.empty(N_ZMIENNYCH)
        for i in range(N_ZMIENNYCH):
            if rng.random() < wsp_pamiec:
                # Losuj z pamięci harmonii
                val = PamiecH[rng.integers(0, pamiec), i]
                # Korekta dźwięku (pitch adjustment)
                if rng.random() < wsp_korekta:
                    val += rng.uniform(-szer_pasmo, szer_pasmo) * zakresy[i]
            else:
                # Losowa improwizacja z pełnego zakresu
                val = rng.uniform(DolneGranice[i], GorneGranice[i])
            nowa_x[i] = np.clip(val, DolneGranice[i], GorneGranice[i])

        # Projekcja na sumę = 100g
        # Krok 1: reguluj syrop ryżowy (x3)
        x3 = MASA_BATONA - nowa_x[0] - nowa_x[1] - nowa_x[3]
        nowa_x[2] = np.clip(x3, DolneGranice[2], GorneGranice[2])
        # Krok 2: jeśli x3 był przycięty — dopasuj izolat (x1)
        reszta = MASA_BATONA - nowa_x.sum()
        if abs(reszta) > 0.01:
            nowa_x[0] = np.clip(nowa_x[0] + reszta, DolneGranice[0], GorneGranice[0])
        # Krok 3: jeśli nadal != 100g — dopasuj pastę (x2)
        reszta = MASA_BATONA - nowa_x.sum()
        if abs(reszta) > 0.01:
            nowa_x[1] = np.clip(nowa_x[1] + reszta, DolneGranice[1], GorneGranice[1])

        nowy_koszt = funkcja_celu(nowa_x)

        # Aktualizacja pamięci harmonii
        najgorszy = int(np.argmax(KosztyH))
        if nowy_koszt < KosztyH[najgorszy]:
            PamiecH[najgorszy] = nowa_x
            KosztyH[najgorszy] = nowy_koszt

        zbieznosc[it] = KosztyH.min()

        if (it + 1) % log_co == 0:
            elapsed = time.time() - t_start
            print(
                f"  iter {it+1:6,}/{improwizacje:,}  ({(it+1)/improwizacje*100:5.1f}%)"
                f"  koszt={zbieznosc[it]:.4f} PLN  czas={elapsed:.1f}s"
            )

    # ── Krok 5: Najlepsze rozwiązanie ─────────────────────────
    najlepszy_idx  = int(np.argmin(KosztyH))
    najlepsza_x    = PamiecH[najlepszy_idx]
    najlepszy_koszt = float(KosztyH[najlepszy_idx])
    elapsed_total  = time.time() - t_start

    print(f"\n[HS] Zakończono w {elapsed_total:.1f}s")
    print(f"     Koszt optymalny : {najlepszy_koszt:.4f} PLN/100g")
    print(f"     Receptura       : " +
          " | ".join(f"{k}={v:.2f}g" for k, v in zip(NAZWY, najlepsza_x)))
    print(f"     Białko          : {bialko(najlepsza_x):.2f}g  (min {MIN_BIALKO}g)")
    print(f"     Tłuszcz         : {tluszcz(najlepsza_x):.2f}g  (max {MAX_TLUSZCZ}g)")
    print(f"     Masa łączna     : {najlepsza_x.sum():.2f}g")
    print(f"     Spełnia ogr.    : {czy_poprawny(najlepsza_x)}")

    return {
        "best_recipe":    {n: round(float(v), 4) for n, v in zip(NAZWY, najlepsza_x)},
        "best_cost":      round(najlepszy_koszt, 6),
        "protein_g":      round(bialko(najlepsza_x), 4),
        "fat_g":          round(tluszcz(najlepsza_x), 4),
        "total_weight_g": round(float(najlepsza_x.sum()), 4),
        "feasible":       bool(czy_poprawny(najlepsza_x)),
        "convergence":    [round(float(v), 6) for v in zbieznosc],
        "hm_final": [
            {
                "recipe":    {n: round(float(v), 4) for n, v in zip(NAZWY, PamiecH[i])},
                "cost":      round(float(KosztyH[i]), 6),
                "protein_g": round(bialko(PamiecH[i]), 4),
                "fat_g":     round(tluszcz(PamiecH[i]), 4),
            }
            for i in range(pamiec)
        ],
        "params": {
            "HMS": pamiec, "HMCR": wsp_pamiec, "PAR": wsp_korekta,
            "BW": szer_pasmo, "NI": improwizacje, "seed": ziarno,
        },
        "constraints": {
            "min_protein_g": MIN_BIALKO,
            "max_fat_g":     MAX_TLUSZCZ,
            "bar_weight_g":  MASA_BATONA,
        },
        "elapsed_seconds": round(elapsed_total, 2),
    }

# ─────────────────────────────────────────────────────────────
# ZAPIS PAMIĘCI DO CSV
# ─────────────────────────────────────────────────────────────
def zapisz_pamiec_csv(PamiecH: np.ndarray, KosztyH: np.ndarray, sciezka: str):
    with open(sciezka, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([*NAZWY, "koszt_PLN", "bialko_g", "tluszcz_g", "poprawny"])
        for x, c in zip(PamiecH, KosztyH):
            w.writerow([
                *[round(float(v), 4) for v in x],
                round(float(c), 6),
                round(bialko(x), 4),
                round(tluszcz(x), 4),
                int(czy_poprawny(x)),
            ])

# ─────────────────────────────────────────────────────────────
# ARGUMENTY CLI
# ─────────────────────────────────────────────────────────────
def parsuj_arg():
    p = argparse.ArgumentParser(description="ALGO-BAR Harmony Search (pure Python)")
    p.add_argument("--pamiec",      type=int,   default=20,     help="Rozmiar pamięci harmonii (HMS)")
    p.add_argument("--wsp_pamiec",  type=float, default=0.90,   help="Współczynnik pamięci HMCR (0-1)")
    p.add_argument("--wsp_korekta", type=float, default=0.30,   help="Współczynnik korekty PAR (0-1)")
    p.add_argument("--szer_pasmo",  type=float, default=0.05,   help="Szerokość pasma BW")
    p.add_argument("--improwizacje",type=int,   default=10_000, help="Liczba improwizacji (NI)")
    p.add_argument("--ziarno",      type=int,   default=42,     help="Ziarno losowości")
    p.add_argument("--output",      type=str,   default="wynik_hs.json", help="Plik wyjściowy JSON")
    return p.parse_args()

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args  = parsuj_arg()
    wynik = harmonia_search(
        pamiec=args.pamiec,
        wsp_pamiec=args.wsp_pamiec,
        wsp_korekta=args.wsp_korekta,
        szer_pasmo=args.szer_pasmo,
        improwizacje=args.improwizacje,
        ziarno=args.ziarno,
    )
    out = Path(args.output)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(wynik, f, indent=2, ensure_ascii=False)
    print(f"\n[HS] Wynik zapisany → {out.resolve()}")