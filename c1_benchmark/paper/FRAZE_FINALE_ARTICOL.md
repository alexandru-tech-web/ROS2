# FRAZE FINALE -- gata de lipit in articol (jitter UNIFORM, finding 1d)

NU am editat textul articolului (Regula 3: doar imagini; textul il scrie/lipeste
Alexandru). Aici e textul FINAL (scris de Alexandru) transcris verbatim, plus
ancorele exacte gasite in word/document.xml -- fiecare pasaj e un singur <w:t>,
text ASCII simplu, FARA ecuatie OMML si FARA indici formatati (d_i, x_i, N_tab
sunt scrise literal cu underscore, apostrof ASCII U+0027). Deci sunt 4 x
find/replace curat, fara batai de cap cu formatarea.

Motiv (finding 1d): comanda tc a rulat FARA 'distribution normal'
  tc qdisc replace dev <IFACE> root netem delay 200ms 50ms loss 0.0%
-> kernelul (tabledist() in sch_netem.c) aplica fallback UNIFORM, desi man page-ul
tc-netem zice ca default e normal. Raportam distributia pe care kernelul chiar a
aplicat-o. Zero re-rulari (Regula 2: campanie inchisa).

=====================================================================
ANCORA 1 -- Sec. 3.2, fraza cu modelul de pierdere + jitter (INLOCUIRE)
=====================================================================
Runul incepe cu "Degradation is injected with tc netem [9], [10]. Table I lists
the eight conditions. " (aceasta parte RAMANE neatinsa). Se inlocuieste doar
substringul de mai jos, din acelasi <w:t>:

VECHI:
  Loss uses netem's default Bernoulli i.i.d. model (each packet dropped
  independently with probability p); delay variation (jitter) uses netem's
  default normal distribution, under which per-packet delay is

NOU:
  Loss uses netem's Bernoulli i.i.d. model (each packet dropped independently
  with probability p). Jitter is applied without a distribution table; in this
  configuration the netem kernel implementation draws the per-packet delay
  uniformly,

=====================================================================
ANCORA 2 -- ecuatia (1), paragraf centrat italic (INLOCUIRE PUNCTUALA)
=====================================================================
Se schimba doar "N_tab(0, 1)" -> "U(-1, 1)" in acelasi <w:t>:

VECHI:
  d_i = DELAY + x_i * JITTER,   x_i ~ N_tab(0, 1),   (1)

NOU:
  d_i = DELAY + x_i * JITTER,   x_i ~ U(-1, 1),   (1)

=====================================================================
ANCORA 3 -- Sec. 3.2, fraza de dupa ecuatie (INLOCUIRE)
=====================================================================
In runul de dupa ecuatie. Explicatia lui N_tab (acum obsoleta) se inlocuieste cu
noua fraza. ATENTIE: fraza urmatoare din acelasi <w:t> --
"We deliberately use the memoryless loss model for comparability with prior work;
bursty models (Gilbert-Elliott) are future work (Sec. 7)." -- RAMANE neatinsa
(inca e adevarata; justifica alegerea loss-ului memoryless + trimite la future work).

VECHI (doar aceasta propozitie):
  where N_tab denotes netem's discretized normal table [9].

NOU:
  bounding the delay to [DELAY - JITTER, DELAY + JITTER]. We note a documented
  discrepancy: the tc-netem manual page states that the default distribution is
  normal [9], while the kernel source (tabledist() in sch_netem.c) applies a
  uniform fallback when no distribution table is loaded; we report the
  distribution the kernel actually applied.

(Rezultatul final al runului = NOU + " " + fraza "We deliberately use...")

=====================================================================
ANCORA 4 -- Limitations, punctul (2) (INLOCUIRE)
=====================================================================
VECHI:
  (2) Memoryless Bernoulli loss and normal-distributed jitter; bursty loss
  (Gilbert-Elliott) is not modeled.

NOU:
  (2) Memoryless Bernoulli loss and uniformly distributed, bounded jitter
  (Sec. 3.2); bursty loss (Gilbert-Elliott) is not modeled.

=====================================================================
ANCORA 5 -- Sec. 4.5, intarire OPTIONALA (INSERARE, nu inlocuire)
=====================================================================
Se INSEREAZA dupa propozitia care se termina cu "...and with router-side
buffering." si INAINTE de "On loopback the same condition yields...". Acelasi
<w:t> mare al paragrafului.

INSEREAZA (cu un spatiu inainte):
  Because the injected jitter is uniformly bounded (Sec. 3.2), the emulated
  channel adds at most 250 ms per direction; CycloneDDS's maximum RTT of 543 ms
  in the same run bounds the medium's typical contribution. The multi-second
  Zenoh RTTs therefore cannot be explained by the emulated channel and must
  originate in the transport stack.

Verificare cifre (canonic, rep1/lat200_jit50/p4096, HIL):
  - "250 ms per direction" = DELAY 200 + JITTER 50 (max un sens). OK.
  - "CycloneDDS's maximum RTT of 543 ms" = max HIL CDDS in aceeasi rulare. OK.
  - "multi-second Zenoh RTTs" = HIL Zenoh mean 6185 ms (max 7872). OK.

=====================================================================
CONSISTENTA -- verifica in tot documentul dupa aplicare
=====================================================================
- Cauta orice alta aparitie a lui "normal" langa "jitter"/"distribution" in
  afara Sec. 3.2 si Limitations (2). Cele 5 ancore de mai sus acopera tot ce a
  gasit auditul; daca apare alta formulare cu "normal distribution", aliniaz-o.
- Referinta [9] (man page tc-netem) ramane valida si in Ancora 3 (o citam ca
  sursa a afirmatiei "default is normal").
