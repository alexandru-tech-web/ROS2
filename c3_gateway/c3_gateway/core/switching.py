#!/usr/bin/env python3
"""switching.py -- masina de stare care decide CAND se comuta transportul.
NUCLEU PUR: nu importa rclpy, socket sau os.environ.

Politica (policy.py) spune ce transport e mai bun INTR-UN PUNCT. Modulul asta decide daca
merita sa te MISTI acolo. Sunt intrebari diferite: prima e despre date, a doua despre cost.

TREI FRANE, fiecare cu alt rol:

1. DWELL-TIME MINIM -- derivat din DOUA masuratori, se ia maximul
   In dual-path ambii agenti raman pornit permanent, deci o comutare NU reporneste nimic:
   costul ei e redirectionarea octetilor pe alt socket UNIX. Masurat la etapa 2 (UDS, 4 KB):
   p50 = 92.6 us, p99 = 214 us per traversare. Se ia p99, conservator.
       termen_1 = COST_COMUTARE_S * FACTOR_AMORTIZARE = 214 us * 10 = 2.14 ms
   Termenul asta e insa neglijabil. Ce leaga cu adevarat mainile gateway-ului e cat ii ia
   ESTIMATORULUI sa afle ca regimul s-a schimbat: daca ai voie sa comuti iar inainte ca
   estimarea sa se fi asezat, decizi pe o stare care inca descrie regimul VECHI.
   Masurat cu tools/measure_settling.py (treapta pe canal GE sintetic, 9 celule ale grilei
   C2 x 3 regimuri de plecare x 40 seed-uri, asezare = biasul intra si ramane in +/-1 sigma):
       mediana 171 esantioane   p95 817 esantioane
   In secunde, cifra depinde de RITMUL cu care e hranit estimatorul:
       termen_2 = ASEZARE_ESANTIOANE / HZ_SONDA_CANAL = 171 / 20 = 8.55 s
       DWELL_MIN_S = max(termen_1, termen_2) = 8.55 s

   ATENTIE, AICI S-A SCHIMBAT CEVA LA ETAPA 3.5. Pana la corectia sondei, estimatorul era
   hranit de ECOURILE APLICATIEI pe calea activa, adica la 50 Hz, si dwell-ul iesea 3.42 s.
   Dupa corectie estimatorul (L,B) e hranit EXCLUSIV de sonda de canal, care merge la 20 Hz
   (vezi sonda/sonda_canal.py pentru de ce 20 si nu altceva). Aceleasi 171 de esantioane
   inseamna acum 8.55 s. Cifra a crescut nu fiindca s-a schimbat un prag, ci fiindca s-a
   schimbat CINE hraneste estimatorul -- si asta e tocmai ce trebuia reparat: la 50 Hz
   estimarea era rapida dar masura marimea GRESITA (pierderea vazuta prin transport, nu
   cea injectata in canal).

   In schimb a DISPARUT punctul orb de 34 s: inainte, calea inactiva era estimata doar din
   sonda de 5 Hz, deci sanatatea ei se afla de zece ori mai incet decat a caii active. Acum
   nu mai exista doua estimari: canalul e unul singur si e masurat o singura data, la 20 Hz,
   indiferent pe ce transport curge traficul.

   De ce MEDIANA si nu p95: cele mai lente celule sunt cele cu pierdere mica si rafale
   lungi (L=5%, B=8: 817 esantioane), unde golurile vin rar si estimatorul afla incet. Dar
   exact acolo marja dintre transporturi e uriasa (98.3 pp in tabela C2), deci o estimare
   inca neasezata da oricum raspunsul corect. Alegerea NU mai e o afirmatie: e verificata
   in test/test_dwell_mediana.py, care compara pe toata grila decizia luata la dwell cu
   decizia luata pe estimarea asezata. Rezultat masurat: 0 dezacorduri din 720 la nivelul
   deciziei comutatorului. (Cautarea BRUTA in tabela basculeaza pe 9 combinatii, toate la
   65536 B, unde grila C2 are doar 3 celule masurate -- dar franele le suprima pe toate.)

2. HISTEREZIS ASIMETRIC -- doua praguri, nu unul
   Pragurile sunt asimetrice pentru ca RISCURILE sunt asimetrice. Transportul implicit din
   tabela e cel care castiga majoritatea celulelor masurate; a pleca de la el pe o dovada
   slaba poate costa pachete nelivrate, in timp ce a te intoarce la el costa cel mult ceva
   optimalitate. Deci:
       PRAG_PLECARE   = 12 pp  (ca sa parasesti implicitul, ai nevoie de dovada tare)
       PRAG_INTOARCERE = 5 pp  (ca sa revii la implicit, e destul o dovada slaba)
   Unitatea e puncte procentuale de livrare efectiva, aceeasi ca marja din tabela C2.

3. POARTA DE INCERTITUDINE -- marja trebuie sa bata bara de eroare
   O marja de 1.7 pp (cat are celula 64 KB / L=15 / B=1 din tabela reala) nu inseamna nimic
   daca sigma estimarii lui L e 4 pp. Se cere
       marja >= K_SIGMA * sigma_L,  K_SIGMA = 2
   adica marja sa depaseasca ~2 abateri standard. Fara asta, gateway-ul comuta pe zgomot
   exact in celulele in care cele doua transporturi sunt practic egale.
   In plus, daca estimarea lui B nu e stabila (vezi estimator.py), nu se comuta deloc:
   politica e indexata si pe B, deci un B nedemn de incredere face raspunsul nedemn.
"""
import sys

COST_COMUTARE_S = 214e-6        # MASURAT etapa 2: UDS 4 KB, p99 per traversare
FACTOR_AMORTIZARE = 10.0        # ALES: acceptam cel mult ~10% timp mort din comutari
ASEZARE_ESANTIOANE = 171        # MASURAT: tools/measure_settling.py, mediana (p95 = 817)
HZ_SONDA_CANAL = 20.0           # ritmul sondei de canal -- SINGURA care hraneste estimatorul
DWELL_MIN_S = max(FACTOR_AMORTIZARE * COST_COMUTARE_S,
                  ASEZARE_ESANTIOANE / HZ_SONDA_CANAL)       # 8.55 s

PRAG_PLECARE_PP = 12.0
PRAG_INTOARCERE_PP = 5.0
K_SIGMA = 2.0

# A CINCEA FRANA (V2a, DECIZII D7, 21.09.2026): EVACUAREA. Franele 1-4 raspund la 'merita sa te misti?'.
# Niciuna nu raspunde la 'calea pe care stai a murit'. Controlul pozitiv din V1.1 a masurat golul: alpha
# activ 1.0 -> 0.0, 0 comutari, livrare 0 % (tabela dadea implicitul cu marja 0, sub prag). Regula:
#   E1 daca alpha(cale activa) < prag_jos si exista o cale cu alpha > prag_sus -> comuta IMEDIAT, fara dwell
#      (motiv 'evacuare'); daca sunt mai multe, cea cu alpha cel mai mare.
#   E2 intoarcerea pe calea evacuata cere dwell complet SI alpha > prag_sus pe o fereastra INTREAGA de
#      viabilitate (durata_fereastra_s = fereastra / hz, 50 / 5 = 10 s), oricine ar cere-o (tabela) -- motiv 'intoarcere'.
#   E3 ambele moarte: nicio comutare; stare()['nicio_cale_viabila'] = True, alpha_activ raportat (0).
#   E4 evacuarea bate tabela: daca in acelasi pas tabela vrea X si evacuarea Y, se executa Y si se logheaza ambele.
#   E5 tabela si dwell-ul ei (8.55 s) raman neschimbate.
# prag_jos = LIVRARE_MINIMA_PCT / 100 (acelasi 'cale inutilizabila' ca la veto); prag_sus = 0.50 PROVIZORIU
# (DECIZII 21.09, intra in baleiajul B2) -- amandoua PARAMETRI ai Comutator-ului, nu constante noi.
#
# A patra frana: NU comuta pe o cale despre care sondele spun ca e moarta. C2 a aratat ca
# starea sesiunii minte -- o cale nefolosita poate fi cazuta exact cand ai nevoie de ea
# (zenoh: 10/10 rulari moarte in trei celule).
#
# ETAPA 3.5: intrarea acestei frane NU mai e o Estimare. Sondele de viabilitate raspund la o
# singura intrebare binara -- calea e vie? -- si atat. Nu mai produc (L,B), fiindca (L,B)
# masurat PRIN transport nu e marimea pe care e indexata tabela de politica. Vetoul are
# nevoie de mult mai putin decat o estimare: ii ajunge fractia de sonde recente intoarse.
# Pragul e scris ca INTREG si comparat prin inmultire incrucisata, nu ca 1.0 - 0.90:
# in virgula mobila 1.0 - 0.90 = 0.09999999999999998, iar o cale care livreaza exact 5 din
# 50 de sonde ar trece de veto din pur zgomot de reprezentare. Granita unui veto nu are
# voie sa depinda de reprezentarea binara a lui 0.9.
LIVRARE_MINIMA_PCT = 10         # livrare <= 10% = cale inutilizabila, oricat ar zice tabela
MIN_ESANTIOANE_CANDIDAT = 20    # sub atat nu stim nimic despre candidat; nu sarim in gol


class Viabilitate(object):
    """Raspunsul sondei de viabilitate pentru o cale: cate sonde recente s-au intors.
    Obiect de date. NU contine (L,B): daca ar contine, cineva ar fi tentat sa il bage in
    tabela de politica -- exact greseala reparata la etapa 3.5."""

    __slots__ = ("n_trimise", "n_intoarse")

    def __init__(self, n_trimise, n_intoarse):
        self.n_trimise = int(n_trimise)
        self.n_intoarse = int(n_intoarse)

    @property
    def livrare(self):
        return self.n_intoarse / float(self.n_trimise) if self.n_trimise else 0.0

    def __repr__(self):
        return ("Viabilitate(%d/%d = %.0f%%)"
                % (self.n_intoarse, self.n_trimise, 100.0 * self.livrare))


def cale_utilizabila(v):
    """O cale pe care AI VOIE sa comuti. Necunoscuta = neutilizabila (conservator):
    daca sonda de viabilitate nu a apucat inca sa stranga destule raspunsuri, a comuta
    ar fi un pariu, nu o decizie."""
    if v is None or v.n_trimise < MIN_ESANTIOANE_CANDIDAT:
        return False, "candidat necunoscut (%s sonde)" % (
            "0" if v is None else v.n_trimise)
    if v.n_intoarse * 100 <= LIVRARE_MINIMA_PCT * v.n_trimise:
        return False, "candidatul livreaza %.0f%% (sonda de viabilitate)" % (
            100.0 * v.livrare)
    return True, ""


class Comutator(object):
    """Masina de stare. decide(estimare, acum) -> (transport, motiv).
    Nu are ceas propriu: timpul vine din afara, ca sa fie testabila determinist."""

    def __init__(self, politica, payload, transport_initial=None,
                 dwell_min_s=DWELL_MIN_S, prag_plecare=PRAG_PLECARE_PP,
                 prag_intoarcere=PRAG_INTOARCERE_PP, k_sigma=K_SIGMA,
                 prag_jos_alpha=LIVRARE_MINIMA_PCT / 100.0, prag_sus_alpha=0.50, durata_fereastra_s=10.0):
        self.politica = politica
        self.payload = int(payload)
        self.implicit = politica.implicit
        self.transport = transport_initial or politica.implicit
        self.dwell_min_s = float(dwell_min_s)
        self.prag_plecare = float(prag_plecare)
        self.prag_intoarcere = float(prag_intoarcere)
        self.k_sigma = float(k_sigma)
        self.t_ultima_comutare = None
        self.n_comutari = 0
        # V2a: evacuarea (E1-E4). prag_sus 0.50 e PROVIZORIU (DECIZII 21.09); durata_fereastra_s = fereastra / hz a sondei de viabilitate
        self.prag_jos_alpha = float(prag_jos_alpha)
        self.prag_sus_alpha = float(prag_sus_alpha)
        self.durata_fereastra_s = float(durata_fereastra_s)
        self.cale_evacuata = None            # de pe ce cale am fugit (E2 se aplica intoarcerii pe ea)
        self.t_evacuare = None
        self._t_sus_de = None                # de cand alpha(cale_evacuata) e continuu > prag_sus
        self.nicio_cale_viabila = False
        self.alpha_activ = None
        self.ultima_decizie = {}             # t, cale_de, cale_spre, motiv, alpha ambele cai, ce voia tabela

    def stare(self):
        """Ce publica nodul in mesajul de stare (E3): nicio_cale_viabila, alpha_activ, transport, cale_evacuata."""
        return {"nicio_cale_viabila": self.nicio_cale_viabila, "alpha_activ": self.alpha_activ,
                "transport": self.transport, "cale_evacuata": self.cale_evacuata}

    @staticmethod
    def _alpha(v):
        """alpha al unei cai din Viabilitate; None daca nu stim destul (sub MIN_ESANTIOANE_CANDIDAT sonde)."""
        if v is None or v.n_trimise < MIN_ESANTIOANE_CANDIDAT:
            return None
        return v.livrare

    def _noteaza(self, acum, de_la, la, motiv, alfe, tabela):
        self.ultima_decizie = {"t": acum, "cale_de": de_la, "cale_spre": la, "motiv": motiv,
                               "alpha": dict(alfe), "tabela_voia": tabela}

    def _evacuare(self, acum, viabilitati, d):
        """E1 / E3 / E4. Intoarce (transport, motiv) daca a decis ceva (comutare sau 'nicio cale viabila'), altfel None."""
        alfe = {t: self._alpha(v) for t, v in viabilitati.items()}
        a_act = alfe.get(self.transport)
        self.alpha_activ = a_act
        tabela = ("%s (marja %.1f pp)" % (d.transport, d.marja)) if d is not None else "fara raport de canal"
        if a_act is None or a_act >= self.prag_jos_alpha:
            self.nicio_cale_viabila = False
            return None
        refugii = [(a, t) for t, a in alfe.items() if t != self.transport and a is not None and a > self.prag_sus_alpha]
        if not refugii:
            self.nicio_cale_viabila = True
            motiv = ("nicio cale viabila: alpha_%s=%.2f < %.2f, %s; tabela voia %s"
                     % (self.transport, a_act, self.prag_jos_alpha,
                        ", ".join("alpha_%s=%s" % (t, "?" if a is None else "%.2f" % a) for t, a in alfe.items() if t != self.transport), tabela))
            self._noteaza(acum, self.transport, self.transport, motiv, alfe, tabela)
            return self.transport, motiv
        a_ref, refugiu = max(refugii)
        de_la = self.transport
        motiv = ("evacuare: alpha_%s=%.2f < %.2f, alpha_%s=%.2f > %.2f; tabela voia %s%s"
                 % (de_la, a_act, self.prag_jos_alpha, refugiu, a_ref, self.prag_sus_alpha, tabela,
                    "" if (d is None or d.transport == refugiu) else " -- EVACUAREA BATE TABELA (E4)"))
        self.transport = refugiu
        self.cale_evacuata = de_la
        self.t_evacuare = acum
        self._t_sus_de = None
        self.t_ultima_comutare = acum
        self.n_comutari += 1
        self.nicio_cale_viabila = False
        self._noteaza(acum, de_la, refugiu, motiv, alfe, tabela)
        return refugiu, motiv

    def _intoarcere_permisa(self, acum, viabilitati):
        """E2: pe cale_evacuata se revine doar cu dwell complet SI alpha > prag_sus pe o fereastra intreaga."""
        a = self._alpha(viabilitati.get(self.cale_evacuata)) if viabilitati else None
        if a is None or a <= self.prag_sus_alpha:
            self._t_sus_de = None
            return False, "alpha_%s=%s <= %.2f" % (self.cale_evacuata, "?" if a is None else "%.2f" % a, self.prag_sus_alpha)
        if self._t_sus_de is None:
            self._t_sus_de = acum
        if acum - self._t_sus_de < self.durata_fereastra_s:
            return False, ("alpha_%s > %.2f doar de %.1f s din %.1f s (fereastra)"
                           % (self.cale_evacuata, self.prag_sus_alpha, acum - self._t_sus_de, self.durata_fereastra_s))
        if self.t_evacuare is not None and acum - self.t_evacuare < self.dwell_min_s:
            return False, "dwell dupa evacuare: %.2f s din %.2f s" % (acum - self.t_evacuare, self.dwell_min_s)
        return True, ""

    def _prag(self, candidat):
        """Asimetria: spre implicit e ieftin, dinspre implicit e scump."""
        return self.prag_intoarcere if candidat == self.implicit else self.prag_plecare

    def decide(self, estimare, acum, viabilitati=None):
        """estimare: starea CANALULUI, de la sonda de canal transport-neutra (.L fractie,
        .B, .sigma_L, .stable). E o singura estimare, nu una per cale: canalul fizic e unul
        singur, iar tabela de politica e indexata pe (L,B) INJECTATE in el, nu pe ce vede
        fiecare transport prin propriile lui retransmisii.
        acum: secunde. viabilitati: {transport: Viabilitate} -- raspunsul binar al sondelor
        de viabilitate, folosit DOAR ca sa nu comutam pe o cale moarta -- si, de la V2a, ca sa FUGIM de pe una
        (E1-E4). estimare poate fi None (fara raport proaspat de canal): atunci tabela nu se consulta, dar
        evacuarea se judeca oricum (E1 e 'imediat', nu asteapta sonda de canal)."""
        d = (self.politica.decide(estimare.L * 100.0, estimare.B, self.payload)
             if estimare is not None else None)
        if viabilitati is not None:
            ev = self._evacuare(acum, viabilitati, d)
            if ev is not None:
                return ev
        if d is None:
            return self.transport, "fara raport proaspat de la sonda de canal"
        candidat = d.transport

        if candidat == self.transport:
            return self.transport, "stabil (deja pe %s)" % self.transport

        if not estimare.stable:
            return self.transport, "estimare instabila (B nedemn de incredere)"

        if viabilitati is not None:
            ok, de_ce = cale_utilizabila(viabilitati.get(candidat))
            if not ok:
                return self.transport, "candidatul %s nu e utilizabil: %s" % (candidat, de_ce)

        prag = self._prag(candidat)
        if d.marja < prag:
            return self.transport, ("marja %.1f pp sub pragul de %.1f pp (%s)"
                                    % (d.marja, prag,
                                       "intoarcere" if candidat == self.implicit
                                       else "plecare"))

        nevoie = self.k_sigma * estimare.sigma_L * 100.0
        if d.marja < nevoie:
            return self.transport, ("marja %.1f pp sub incertitudine (%.1f x sigma = %.1f pp)"
                                    % (d.marja, self.k_sigma, nevoie))

        if (self.t_ultima_comutare is not None
                and acum - self.t_ultima_comutare < self.dwell_min_s):
            return self.transport, ("dwell: %.2f s din %.2f s"
                                    % (acum - self.t_ultima_comutare, self.dwell_min_s))

        intoarcere = (candidat == self.cale_evacuata)
        if intoarcere:
            ok, de_ce = self._intoarcere_permisa(acum, viabilitati)
            if not ok:
                return self.transport, "intoarcere pe %s refuzata (E2): %s" % (candidat, de_ce)

        de_la = self.transport
        self.transport = candidat
        self.t_ultima_comutare = acum
        self.n_comutari += 1
        if intoarcere:
            self.cale_evacuata, self.t_evacuare, self._t_sus_de = None, None, None
            motiv = "intoarcere pe %s (marja %.1f pp, sursa %s; dwell si fereastra complete)" % (candidat, d.marja, d.sursa)
        else:
            motiv = "comutat pe %s (marja %.1f pp, sursa %s)" % (candidat, d.marja, d.sursa)
        alfe = {t: self._alpha(v) for t, v in (viabilitati or {}).items()}
        self._noteaza(acum, de_la, candidat, motiv, alfe, "%s (marja %.1f pp)" % (d.transport, d.marja))
        return self.transport, motiv


def _selftest():
    from estimator import Estimare
    from policy import Politica, _tabela_sintetica

    def est(L, B=8.0, sigma=0.005, stable=True):
        return Estimare(L, B, sigma, 1000, 50, stable)

    pol = Politica(_tabela_sintetica())

    # 1. dwell-time-ul e DERIVAT din doua masuratori, si castiga cea mai mare
    assert abs(DWELL_MIN_S - 171 / 20.0) < 1e-9, DWELL_MIN_S
    assert DWELL_MIN_S == max(FACTOR_AMORTIZARE * COST_COMUTARE_S,
                              ASEZARE_ESANTIOANE / HZ_SONDA_CANAL)
    assert DWELL_MIN_S > FACTOR_AMORTIZARE * COST_COMUTARE_S, \
        "asezarea estimatorului trebuie sa domine costul de comutare, nu invers"

    # 2. pe payload 64 KB, la (L=15, B=1), tabela zice zenoh -- dar marja e 1.7 pp,
    # sub pragul de plecare: NU se comuta. Exact celula pentru care exista pragurile.
    c = Comutator(pol, 65536)
    t, motiv = c.decide(est(0.15, 1.0), 100.0)
    assert t == "cyclonedds" and c.n_comutari == 0, (t, motiv)
    assert "sub pragul" in motiv, motiv

    # 3. marja mare, estimare stabila -> se comuta (si se cere payload-ul potrivit)
    pol2 = Politica({
        "schema": "c3_policy_table/1", "default_transport": "cyclonedds",
        "default_motiv": "sintetic",
        "celule": [{"L": 15.0, "B": 8.0, "payload": 4096, "transport": "zenoh",
                    "marja": 40.0, "covered": True, "sursa": "t.md"}]})
    c = Comutator(pol2, 4096)
    t, motiv = c.decide(est(0.15), 10.0)
    assert t == "zenoh" and c.n_comutari == 1, (t, motiv)
    assert "comutat" in motiv, motiv

    # 4. DWELL: imediat dupa o comutare, alta comutare e refuzata
    c.transport = "cyclonedds"                 # simulam ca politica vrea inapoi
    t, motiv = c.decide(est(0.15), 10.5)       # 0.5 s < 4.3 s
    assert t == "cyclonedds" and "dwell" in motiv, (t, motiv)
    t, motiv = c.decide(est(0.15), 10.0 + DWELL_MIN_S + 0.01)
    assert t == "zenoh" and c.n_comutari == 2, (t, motiv)

    # 5. POARTA DE INCERTITUDINE: aceeasi marja, dar sigma mare -> nu se comuta
    c = Comutator(pol2, 4096)
    t, motiv = c.decide(est(0.15, sigma=0.30), 10.0)     # 2*30 pp = 60 pp > marja 40
    assert t == "cyclonedds" and "incertitudine" in motiv, (t, motiv)

    # 6. ESTIMARE INSTABILA: nu se comuta, oricat de mare ar fi marja
    c = Comutator(pol2, 4096)
    t, motiv = c.decide(est(0.15, stable=False), 10.0)
    assert t == "cyclonedds" and "instabila" in motiv, (t, motiv)

    # 7. ASIMETRIA pragurilor: plecarea de la implicit cere mai mult decat intoarcerea.
    # Marja de 8 pp: nu ajunge sa pleci, dar ajunge sa te intorci.
    pol8 = Politica({
        "schema": "c3_policy_table/1", "default_transport": "cyclonedds",
        "default_motiv": "sintetic",
        "celule": [{"L": 15.0, "B": 8.0, "payload": 4096, "transport": "zenoh",
                    "marja": 8.0, "covered": True, "sursa": "t.md"},
                   {"L": 30.0, "B": 8.0, "payload": 4096, "transport": "cyclonedds",
                    "marja": 8.0, "covered": True, "sursa": "t.md"}]})
    c = Comutator(pol8, 4096)
    t, _ = c.decide(est(0.15), 10.0)
    assert t == "cyclonedds", "8 pp nu ar trebui sa ajunga pentru PLECARE"
    c.transport = "zenoh"                       # acum suntem in afara implicitului
    t, motiv = c.decide(est(0.30), 100.0)
    assert t == "cyclonedds" and "comutat" in motiv, ("8 pp ar trebui sa ajunga pentru "
                                                      "INTOARCERE", motiv)
    # 8. VETO DE CALE MOARTA: tabela zice sa comutam, marja e uriasa, dar sonda de
    # VIABILITATE spune ca respectiva cale nu raspunde. Exact scenariul din C2 (zenoh
    # 10/10 rulari moarte in trei celule).
    c = Comutator(pol2, 4096)
    moarta = Viabilitate(50, 1)                            # 2% din sonde s-au intors
    t, motiv = c.decide(est(0.15), 10.0, {"zenoh": moarta})
    assert t == "cyclonedds" and c.n_comutari == 0, (t, motiv)
    assert "nu e utilizabil" in motiv and "livreaza" in motiv, motiv
    # aceeasi decizie, dar cu candidatul viu: se comuta
    c2 = Comutator(pol2, 4096)
    t, motiv = c2.decide(est(0.15), 10.0, {"zenoh": Viabilitate(50, 43)})
    assert t == "zenoh" and "comutat" in motiv, (t, motiv)
    # candidat NECUNOSCUT (sonda nu a apucat sa stranga destule) = nu sarim in gol
    c3 = Comutator(pol2, 4096)
    t, motiv = c3.decide(est(0.15), 10.0, {"zenoh": Viabilitate(3, 3)})
    assert t == "cyclonedds" and "necunoscut" in motiv, (t, motiv)
    assert cale_utilizabila(None) == (False, "candidat necunoscut (0 sonde)")

    # 9. PRAGUL DE VIABILITATE e o granita EXACTA, nu o zona de gri: exact 10% e inca
    # moarta, 12% e vie. Cu comparatie in virgula mobila (1.0 - 0.90) cazul de 5 din 50
    # trecea de veto; de aceea comparatia e pe intregi. Granita se testeaza, nu se crede.
    assert cale_utilizabila(Viabilitate(50, 5))[0] is False
    assert cale_utilizabila(Viabilitate(50, 6))[0] is True
    # si o cale PERFECTA trece, evident -- dar si asta se verifica, ca sa nu treaca testul
    # de mai sus doar fiindca functia intoarce mereu False
    assert cale_utilizabila(Viabilitate(50, 50)) == (True, "")

    # 10. VIABILITATEA NU E O ESTIMARE. Daca cineva ii adauga vreodata un camp L sau B,
    # urmatorul pas ar fi sa il bage in tabela de politica -- fix greseala reparata la
    # etapa 3.5, unde (L,B) vazut PRIN transport hranea lookup-ul. Se blocheaza aici.
    assert set(Viabilitate.__slots__) == {"n_trimise", "n_intoarse"}, Viabilitate.__slots__
    assert not hasattr(Viabilitate(1, 1), "__dict__"), \
        "Viabilitate trebuie sa ramana cu __slots__, ca sa nu i se poata lipi campuri"

    print("SELFTEST switching OK (dwell derivat din sonda de canal = %.2f s, histerezis "
          "asimetric, poarta de incertitudine, veto binar de viabilitate)." % DWELL_MIN_S)


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    print(__doc__.strip())
    print("\ncomutare %.0f us x %.0f = %.2f ms | asezare %d esantioane / %.0f Hz = %.2f s"
          "  ->  DWELL_MIN_S = %.2f s"
          % (COST_COMUTARE_S * 1e6, FACTOR_AMORTIZARE,
             FACTOR_AMORTIZARE * COST_COMUTARE_S * 1e3, ASEZARE_ESANTIOANE,
             RATA_ESTIMARE_HZ, ASEZARE_ESANTIOANE / RATA_ESTIMARE_HZ, DWELL_MIN_S))
    print("PRAG_PLECARE = %.1f pp | PRAG_INTOARCERE = %.1f pp | K_SIGMA = %.1f"
          % (PRAG_PLECARE_PP, PRAG_INTOARCERE_PP, K_SIGMA))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
