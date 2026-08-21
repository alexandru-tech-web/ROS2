# Limite de efort si viteza -- DERIVATE, cu provenienta

Generat din `scripts/spec_derivate.py` (nucleu pur, 27 verificari in selftest).
Nicio cifra de aici nu e rotunda fara eticheta: ori e citita din document, ori are
formula si sursele ei. Modelul mostenit avea 120/300/500 Nm si 2.0/0.03/0.05 rad/s,
fara nicio sursa; acelea au disparut.

## Fapte citite din document

| marime | valoare | sursa |
|---|---|---|
| raport total sold | 2700:11 = 245.4545 | [PDF Tabel 3.1, p.10-11] |
| raport total genunchi | 2160:11 = 196.3636 | [PDF Tabel 3.1, p.10-11] |
| raport total glezna | 100 | [PDF Tabel 3.1, p.10-11] |
| cuplu nominal SHG-40 | 345 Nm | [PDF Tabel 6.1 p.23; foaie p.25-28] |
| cuplu nominal SHG-32 | 178 Nm | [PDF Tabel 6.1 p.23; foaie p.25-28] |
| cuplu nominal SHG-20 | 52 Nm | [PDF Tabel 6.1 p.23; foaie p.25-28] |
| cuplu continuu SMP8048 | 0.9 Nm | [PDF foaie p.29-33] |
| turatie nominala SMP8048 | 3700 rpm | [PDF foaie p.29-33] |
| cuplu continuu TBM(S)-6025 | 0.706 Nm | [PDF foaie p.34-42] |

## Ipoteze declarate (NU sunt in document)

| ipoteza | valoare | de ce si ce risca |
|---|---|---|
| randament lant (eta) | 0.80 | curea + reductor armonic. La glezna exista un PRAG: eta = 52/(0.706x100) = 0.7365. Peste el limiteaza reductorul, sub el motorul. Ipoteza de 0.80 e PESTE prag, deci daca randamentul real e mai mic, efortul gleznei scade sub 52 Nm. |
| turatie TBM(S)-6025 | 1500 rpm | nu apare in partea citita a foii. Afecteaza DOAR viteza gleznei, nu efortul. |
| motor sold/genunchi | SMP8048 | lista de componente [PDF Tabel 3.2, p.11] numeste SMP802**4B**, dar foaia anexata e pentru 80**48**. Se folosesc cifrele foii, si discrepanta ramane vizibila in cod (campurile `nume` si `foaie` difera). DE CONFIRMAT PE MOTORUL FIZIC. |

## Valori derivate

Formule:

    viteza [rad/s] = (rpm_motor / 60) * 2*pi / raport_total
    efort  [Nm]    = min(cuplu_motor * raport_total * eta, cuplu_nominal_reductor)

| articulatie | raport | rpm | viteza [rad/s] | viteza [grade/s] | efort [Nm] | limitat de |
|---|---|---|---|---|---|---|
| sold | 245.45 | 3700 | 1.5786 | 90.4 | 176.7 | motorul |
| genunchi | 196.36 | 3700 | 1.9732 | 113.1 | 141.4 | motorul |
| glezna | 100.00 | 1500 | 1.5708 | 90.0 | 52.0 | reductorul |

Observatie de proiectare, nu detaliu: la sold si genunchi MOTORUL limiteaza
(176.7 din 345 disponibili, respectiv 141.4 din 178), la glezna REDUCTORUL.

## Ce NU acopera acest document

Axele prismatice (push rod-uri de pozitionare: scaun 101/113, coapsa 306, baze
307, gamba 403) NU au date de forta sau viteza in documentul tehnic. Limitele lor
din URDF raman placeholdere, etichetate NEVERIFICAT, ca si masele (GAP 1).

## Separatia de safety_limits.yaml

URDF-ul poarta CAPABILITATEA documentata a masinii. `config/safety_limits.yaml`
poarta pragul TERAPEUTIC, deliberat mult mai mic, supravegheat de supervizor.
Cele doua nu se confunda si nu se sincronizeaza: prima spune ce POATE dispozitivul,
a doua ce ARE VOIE cu un pacient pe el. Etajarea reala e in trei straturi --
mecanic (opritoare), electric (proximitati), software (yaml) -- vezi README.
