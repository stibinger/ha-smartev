# SmartEV API Analysis

## Endpoint

```
GET /data/flatMetersChart.php
```

## Parametry

| Parametr | Popis |
|----------|-------|
| flatId | ID bytu |
| y | Rok |
| m | Měsíc |
| d | Den |

---

# Chování API

## Přehled

| y | m | d | chartInterval | Význam |
|---|---|---|---------------|---------|
| 0 | 0 | 0 | Y | Spotřeba po jednotlivých letech |
| YYYY | 0 | 0 | m | Spotřeba po jednotlivých měsících |
| YYYY | MM | 0 | d | Spotřeba po jednotlivých dnech |
| YYYY | MM | DD | H | Spotřeba po jednotlivých hodinách |

API je hierarchické.

```
Rok
 └── Měsíc
      └── Den
           └── Hodina
```

---

# Struktura odpovědi

## Objekt meter

| Pole | Význam |
|------|--------|
| id | ID elektroměru |
| value1 | Aktuální stav elektroměru |
| value2 | Zatím neznámý význam |
| unit | Jednotka |
| type | Typ elektroměru |
| dt | Unix timestamp posledního odečtu |
| dtStr | Formátovaný čas |
| chartInterval | Interval grafu |
| chartData | Agregovaná historie |

---

# chartData

## Interval Y

```
2023
2024
2025
2026
```

Vrací spotřebu jednotlivých roků.

---

## Interval m

```
01
02
03
...
12
```

Vrací spotřebu jednotlivých měsíců.

---

## Interval d

```
01
02
03
...
31
```

Vrací spotřebu jednotlivých dnů.

---

## Interval H

```
00
01
02
...
23
```

Vrací hodinovou spotřebu.

Každá položka obsahuje

| Pole | Význam |
|------|--------|
| idx | Hodina |
| val1 | Spotřeba |
| dt0 | Začátek intervalu |
| dt1 | Konec intervalu |

---

# Ověřené poznatky

## value1

Pole `value1` představuje vždy aktuální stav elektroměru.

Není ovlivněno parametry `y`, `m` ani `d`.

---

## chartData

Pole `chartData` neobsahuje historii odečtů elektroměru.

Obsahuje již serverem vypočtené agregace.

Home Assistant tedy nemusí:

- počítat rozdíly elektroměru,
- řešit přelom dne,
- řešit přelom měsíce,
- řešit Nový rok,
- řešit výměnu elektroměru.

Veškeré agregace provádí server SmartEV.

---

# Návrh SmartEVClient

Místo pevně zadaného dotazu

```python
client.get_flat_info()
```

bude klient podporovat

```python
client.get_flat_info(
    year=0,
    month=0,
    day=0,
)
```

Příklady

```python
client.get_flat_info()
```

Aktuální stav + roční historie.

```python
client.get_flat_info(
    year=current_year
)
```

Měsíční historie.

```python
client.get_flat_info(
    year=current_year,
    month=current_month,
)
```

Denní historie.

```python
client.get_flat_info(
    year=current_year,
    month=current_month,
    day=current_day,
)
```

Hodinová historie.

---

# Návrh koordinátoru

Koordinátor nebude načítat hodinová data.

Každou minutu provede pouze tři dotazy.

## Dotaz 1

```python
client.get_flat_info()
```

Použití

- Celková energie
- Čas posledního odečtu

---

## Dotaz 2

```python
client.get_flat_info(
    year=current_year,
)
```

Použití

- Spotřeba tento měsíc
- Spotřeba tento rok
- Budoucí graf po měsících

---

## Dotaz 3

```python
client.get_flat_info(
    year=current_year,
    month=current_month,
)
```

Použití

- Spotřeba dnes
- Budoucí graf po dnech

---

# Návrh entit

## Verze 0.5.0

- Celková energie
- Čas posledního odečtu

---

## Verze 0.6.0

- Spotřeba tento měsíc
- Spotřeba dnes

---

## Verze 0.7.0

- Spotřeba tento rok
- Graf spotřeby po měsících
- Graf spotřeby po dnech

---

## Verze 0.8.0

- Hodinová historie
- Export dat
- Další diagnostické entity

---

# Otevřené otázky

- význam `value2`
- význam `type`
- více elektroměrů (`meters[]`)
- další endpointy SmartEV
- využití hodinových dat v Home Assistantu

---

# Poznámky

Reverzní analýza API byla provedena dne 16. 7. 2026 pomocí testovacího skriptu `test_api.py`.

Byly experimentálně ověřeny všechny čtyři úrovně agregace:

- Rok
- Měsíc
- Den
- Hodina

Výsledky odpovídají konzistentně navrženému hierarchickému API.