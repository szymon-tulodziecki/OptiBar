import csv
import random

SKLADNIKI = ["izolat_serwatki", "pasta_orzechowa", "syrop_ryzowy", "quinoa"]
BIALKO    = [0.90, 0.25, 0.00, 0.14]
TLUSZCZ   = [0.00, 0.50, 0.00, 0.06]
KOSZT     = [18.00, 6.00, 2.50, 5.50]
MIN_MASA  = [10, 15, 15, 5]
MAX_MASA  = [40, 40, 35, 25]

def generuj_recepture():
    for _ in range(50_000):
        x1 = random.uniform(MIN_MASA[0], MAX_MASA[0])
        x2 = random.uniform(MIN_MASA[1], MAX_MASA[1])
        x3 = random.uniform(MIN_MASA[2], MAX_MASA[2])
        x4 = 100.0 - x1 - x2 - x3
        if MIN_MASA[3] <= x4 <= MAX_MASA[3]:
            return [x1, x2, x3, x4]

wiersze = []
for nr in range(1, 10_001):
    x = generuj_recepture()
    koszt   = sum(x[i] * KOSZT[i]   for i in range(4))
    bialko  = sum(x[i] * BIALKO[i]  for i in range(4))
    tluszcz = sum(x[i] * TLUSZCZ[i] for i in range(4))
    wiersze.append({
        "nr":                   nr,
        "x1_izolat_g":          round(x[0], 4),
        "x2_pasta_g":           round(x[1], 4),
        "x3_syrop_g":           round(x[2], 4),
        "x4_quinoa_g":          round(x[3], 4),
        "koszt_PLN":            round(koszt,   4),
        "bialko_g":             round(bialko,  4),
        "tluszcz_g":            round(tluszcz, 4),
        "spelnia_ograniczenia": int(bialko >= 25 and tluszcz <= 20),
    })

with open("receptury.csv", "w", newline="", encoding="utf-8") as f:
    zapis = csv.DictWriter(f, fieldnames=wiersze[0].keys())
    zapis.writeheader()
    zapis.writerows(wiersze)

print(f"Zapisano {len(wiersze)} receptur → receptury.csv")