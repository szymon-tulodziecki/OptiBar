# Dokumentacja Modelu: Optymalizacja Receptury Batona ALGO-BAR

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
