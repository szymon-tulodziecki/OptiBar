# Optymalizacja Receptury Batona ALGO-BAR

![ALGO-BAR](algobar_clean.png)

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![MATLAB](https://img.shields.io/badge/MATLAB-R2023+-e16737?style=for-the-badge&logo=mathworks&logoColor=white)
![PyQt5](https://img.shields.io/badge/PyQt5-GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)
![SciPy](https://img.shields.io/badge/SciPy-8CAAE6?style=for-the-badge&logo=scipy&logoColor=white)
![CSV](https://img.shields.io/badge/CSV-dane_losowe-FFD600?style=for-the-badge&logoColor=black)
![JSON](https://img.shields.io/badge/JSON-wynik_HS-00e5b0?style=for-the-badge&logoColor=black)
![Status](https://img.shields.io/badge/Status-W__budowie-ff4560?style=for-the-badge)

---

### 1. Cel projektu
Minimalizacja całkowitego kosztu surowców przy zachowaniu wytycznych dietetycznych oraz technologicznych. Model uwzględnia fizyczne ograniczenia składników, aby zapewnić właściwą konsystencję i smak produktu końcowego.

### 2. Parametry surowców (na 100g)

| Składnik | Symbol | Białko (%) | Tłuszcz (%) | Cena (PLN/100g) |
| :--- | :---: | :---: | :---: | :---: |
| Izolat serwatki | $x_1$ | 90 | 0 | 18.00 |
| Pasta orzechowa | $x_2$ | 25 | 50 | 6.00 |
| Syrop ryżowy | $x_3$ | 0 | 0 | 2.50 |
| Ekspandowana quinoa | $x_4$ | 14 | 6 | 5.50 |

---

### 3. Założenia technologiczne (Zakresy masy)

Wprowadzenie limitów dolnych i górnych zapobiega błędom strukturalnym batona (np. nadmiernej sypkości lub braku kleistości):

* **Izolat ($x_1$):** od 10g do 40g
* **Pasta orzechowa ($x_2$):** od 15g do 40g
* **Syrop ryżowy ($x_3$):** od 15g do 35g
* **Quinoa ($x_4$):** od 5g do 25g

---

### 4. Algorytm optymalizacji — Harmony Search

Optymalizacja realizowana jest metodą **Harmony Search (HS)** — algorytmem metaheurystycznym wzorowanym na improwizacji muzycznej. Algorytm zapisany jest w MATLAB i wykonywany przez Python via **MATLAB Engine for Python**.

#### Parametry algorytmu

| Parametr | Symbol | Wartość | Opis |
| :--- | :---: | :---: | :--- |
| Rozmiar pamięci harmonii | HMS | 20 | Liczba rozwiązań przechowywanych w pamięci |
| Współczynnik uwzględnienia pamięci | HMCR | 0.90 | Prawdopodobieństwo losowania z pamięci |
| Współczynnik korekty dźwięku | PAR | 0.30 | Prawdopodobieństwo perturbacji wartości |
| Szerokość pasma | BW | 0.05 | Maksymalna korekta (% zakresu zmiennej) |
| Liczba improwizacji | NI | 10 000 | Liczba iteracji algorytmu |

#### Schemat działania

```
Krok 1 — Inicjalizacja HM
         Wypełnij pamięć HMS=20 losowymi recepturami spełniającymi ograniczenia

Krok 2 — Improwizacja nowej harmonii
         Dla każdego składnika x_i:
           z prawdop. HMCR → pobierz wartość z pamięci HM
             z prawdop. PAR  → lekko skoryguj ±BW
           z prawdop. 1-HMCR → losuj z pełnego zakresu [min, max]

Krok 3 — Aktualizacja pamięci
         Jeśli nowa receptura spełnia ograniczenia
           i jej koszt < najgorszy koszt w HM
             → zastąp najgorsze rozwiązanie w HM

Krok 4 — Powtórz NI=10 000 razy kroki 2-3

Krok 5 — Zwróć najlepsze rozwiązanie z HM → wynik_hs.json
```

#### Przepływ danych

```
harmony_search.m          zapis algorytmu (MATLAB)
       ↓  MATLAB Engine for Python
hs_algobar.py             wykonanie algorytmu (Python)
       ↓
wynik_hs.json             wynik optymalizacji
       ↓
gui_algobar.py            wizualizacja (PyQt5)
```

---

### 5. Generator danych losowych

Plik `generator.py` generuje 10 000 losowych receptur metodą Monte Carlo i zapisuje je do `receptury.csv`. Dane te służą jako **punkt odniesienia** (brute-force reference) do porównania z wynikiem Harmony Search.

```
generator.py  →  receptury.csv  (10 000 losowych prób)
```

| Kolumna | Opis |
| :--- | :--- |
| `x1_izolat_g` | masa izolatu serwatki [g] |
| `x2_pasta_g` | masa pasty orzechowej [g] |
| `x3_syrop_g` | masa syropu ryżowego [g] |
| `x4_quinoa_g` | masa quinoa [g] |
| `koszt_PLN` | całkowity koszt receptury [PLN/100g] |
| `bialko_g` | zawartość białka [g/100g] |
| `tluszcz_g` | zawartość tłuszczu [g/100g] |
| `spelnia_ograniczenia` | 1 = spełnia, 0 = narusza |

---

### 6. GUI — PyQt5

Interfejs graficzny `gui_algobar.py` wczytuje `wynik_hs.json` oraz `receptury.csv` i prezentuje wyniki w formie wizualnej.

#### Funkcje interfejsu

* **Paski porównawcze** — zestawienie receptury losowej, wyniku HS i optimum dla każdego składnika oraz makroskładnika (koszt, białko, tłuszcz)
* **Wykres zbieżności** — spadek kosztu w kolejnych iteracjach algorytmu (NI = 10 000)
* **Tabela receptur** — przeglądanie wygenerowanych prób z podświetleniem najlepszych wyników
* **Karty statystyk** — koszt aktualny, różnica do optimum, status spełnienia ograniczeń

#### Uruchomienie

```bash
pip install PyQt5 scipy numpy
python gui_algobar.py
```

---

### 7. Struktura plików

```
├── generator.py            generator danych losowych
├── hs_algobar.py           algorytm Harmony Search (Python)
├── harmony_search.m        zapis algorytmu (MATLAB)
├── gui_algobar.py          interfejs graficzny (PyQt5)
├── receptury.csv           10 000 losowych receptur
├── hm_inicjalizacja.csv    pamięć harmonii — rozwiązania startowe
└── wynik_hs.json           wynik optymalizacji HS
```