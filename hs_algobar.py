import csv
import random

SKLADNIKI = ["izolat_serwatki", "pasta_orzechowa", "syrop_ryzowy", "quinoa"]
KOSZT     = [18.00, 6.00, 2.50, 5.50]
MIN_MASA  = [10, 15, 15, 5]
MAX_MASA  = [40, 40, 35, 25]

HMS  = 20      # ile rozwiązań przechowuje pamięć harmonii
HMCR = 0.90    # z jakim prawdopodobieństwem nowa receptura czerpie z pamięci

# ─────────────────────────────────────────────
#  WYPEŁNIENIE PAMIĘCI HARMONII
# ─────────────────────────────────────────────
def losuj_recepture():
    for _ in range(50_000):
        x1 = random.uniform(MIN_MASA[0], MAX_MASA[0])
        x2 = random.uniform(MIN_MASA[1], MAX_MASA[1])
        x3 = random.uniform(MIN_MASA[2], MAX_MASA[2])
        x4 = 100.0 - x1 - x2 - x3
        if MIN_MASA[3] <= x4 <= MAX_MASA[3]:
            return [x1, x2, x3, x4]

HM = [losuj_recepture() for _ in range(HMS)]

# ─────────────────────────────────────────────
#  PODGLĄD PAMIĘCI HARMONII
# ─────────────────────────────────────────────
print(f"HMS  = {HMS}")
print(f"HMCR = {HMCR}\n")
print(f"{'Nr':>3}  {'x1':>7}  {'x2':>7}  {'x3':>7}  {'x4':>7}  {'Koszt':>8}")
print("─" * 48)
for i, x in enumerate(HM, 1):
    k = sum(x[j] * KOSZT[j] for j in range(4))
    print(f"{i:>3}  {x[0]:>7.2f}  {x[1]:>7.2f}  {x[2]:>7.2f}  {x[3]:>7.2f}  {k:>8.2f}")

# ─────────────────────────────────────────────
#  ZAPIS DO CSV
# ─────────────────────────────────────────────
with open("hm_inicjalizacja.csv", "w", newline="", encoding="utf-8") as f:
    zapis = csv.writer(f)
    zapis.writerow(["nr", "x1_izolat_g", "x2_pasta_g", "x3_syrop_g", "x4_quinoa_g", "koszt_PLN"])
    for i, x in enumerate(HM, 1):
        k = sum(x[j] * KOSZT[j] for j in range(4))
        zapis.writerow([i, round(x[0], 4), round(x[1], 4), round(x[2], 4), round(x[3], 4), round(k, 4)])

print(f"\nZapisano {HMS} rozwiązań startowych → hm_inicjalizacja.csv")