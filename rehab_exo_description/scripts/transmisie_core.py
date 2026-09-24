#!/usr/bin/python3
"""transmisie_core.py -- NUCLEU PUR: lantul de transmisie si citirea encoderelor.

Ce modeleaza, si de unde:
  raport TOTAL articulatie<-motor [PDF Tabel 3.1, p.10-11]
      sold 2700:11, genunchi 2160:11, glezna 100
  raport MOTOR->ENCODER [aceeasi coloana din Tabel 3.1]
      sold 1:1 (encoderul 103 e coaxial cu fulia de antrenare, PDF p.6-7)
      genunchi 19:25 (encoder ABSOLUT pe lantul fuliei CONDUSE, PDF p.8)
      glezna -- fara encoder pe articulatie; unghiul vine de la senzorul dedicat
               BWK216 [PDF Tabel 6.1 p.23], modelat separat la M4
  HOMING [PDF p.10]: encoderele sold si genunchi sunt ABSOLUTE pe RS485
      (REALWETECH RS485-RTU) si PASTREAZA unghiul la cadere de tensiune; la
      pornire unghiul se afla CITINDU-LE, nu printr-o cursa de referinta.

Ce NU modeleaza, si se spune:
  rezolutia encoderelor NU e in document (GAP 6). Aici nu se cuantizeaza nimic:
  citirea e continua. Un twin care ar cuantiza cu o rezolutie inventata ar produce
  zgomot cu aspect de masuratoare.

Ruleaza singur:  python3 scripts/transmisie_core.py --selftest
"""
import sys

RAPORT_TOTAL = {"sold": 2700.0 / 11.0, "genunchi": 2160.0 / 11.0, "glezna": 100.0}
# motor -> encoder, din ultima coloana a Tabelului 3.1
RAPORT_ENCODER = {"sold": 1.0, "genunchi": 25.0 / 19.0, "glezna": None}
ARE_ENCODER = {"sold": True, "genunchi": True, "glezna": False}

STARE_NECUNOSCUT = "necunoscut"
STARE_CITIT = "citit"
STARE_ESUAT = "esuat"


def familie(joint):
    return "sold" if "hip" in joint else ("genunchi" if "knee" in joint else "glezna")


def unghi_motor_rad(art, unghi_articulatie_rad):
    """Unghiul axului motor pentru un unghi de articulatie dat."""
    return unghi_articulatie_rad * RAPORT_TOTAL[art]


def unghi_encoder_rad(art, unghi_articulatie_rad):
    """Unghiul VAZUT de encoder. None pe articulatiile fara encoder propriu.
    La genunchi encoderul nu sta pe motor, ci pe fulia condusa (19:25), deci vede
    altceva decat axul motor -- distinctie reala, nu decorativa."""
    if not ARE_ENCODER[art]:
        return None
    return unghi_motor_rad(art, unghi_articulatie_rad) / RAPORT_ENCODER[art]


def unghi_articulatie_din_encoder(art, unghi_encoder):
    """Inversa: din citirea encoderului inapoi la unghiul articulatiei."""
    if not ARE_ENCODER[art]:
        return None
    return unghi_encoder * RAPORT_ENCODER[art] / RAPORT_TOTAL[art]


class Homing(object):
    """Secventa de pornire. NU e o cursa de referinta: encoderele fiind ABSOLUTE si
    pastrand unghiul la cadere de tensiune [PDF p.10], homing-ul inseamna A LE CITI.

    Regula tare: pana cand TOATE articulatiile cu encoder au fost citite, homing-ul NU
    e gata, iar controllerele de miscare nu au voie sa porneasca. O articulatie
    necitita inseamna pozitie necunoscuta, iar o comanda de traiectorie pe o pozitie
    necunoscuta e chiar clasa de defect pe care metodologia proiectului o refuza."""

    def __init__(self, articulatii):
        self.articulatii = list(articulatii)
        self.stare = {j: STARE_NECUNOSCUT for j in self.articulatii}
        self.unghi = {}

    def cere_encoder(self):
        """Articulatiile care TREBUIE citite ca sa fie homing gata."""
        return [j for j in self.articulatii if ARE_ENCODER[familie(j)]]

    def citeste(self, joint, unghi_encoder):
        art = familie(joint)
        if not ARE_ENCODER[art]:
            return False
        if unghi_encoder is None:
            self.stare[joint] = STARE_ESUAT
            return False
        self.unghi[joint] = unghi_articulatie_din_encoder(art, unghi_encoder)
        self.stare[joint] = STARE_CITIT
        return True

    def esueaza(self, joint):
        self.stare[joint] = STARE_ESUAT

    def gata(self):
        return all(self.stare[j] == STARE_CITIT for j in self.cere_encoder())

    def raport(self):
        lipsa = [j for j in self.cere_encoder() if self.stare[j] != STARE_CITIT]
        return {"gata": self.gata(), "citite": sorted(self.unghi),
                "lipsa": sorted(lipsa),
                "fara_encoder": sorted(j for j in self.articulatii
                                       if not ARE_ENCODER[familie(j)]),
                "stare": dict(self.stare)}


def _selftest():
    import math
    v = 0

    def ok(c, m):
        assert c, m
        return 1

    # 1. rapoartele sunt cele documentate
    v += ok(abs(RAPORT_ENCODER["genunchi"] - 25.0 / 19.0) < 1e-12, "19:25 la genunchi")
    v += ok(RAPORT_ENCODER["sold"] == 1.0, "1:1 la sold")
    v += ok(RAPORT_ENCODER["glezna"] is None and not ARE_ENCODER["glezna"],
            "glezna nu are encoder propriu")

    # 2. la SOLD, encoderul vede exact axul motor (1:1); la GENUNCHI, NU
    a = 0.5
    v += ok(abs(unghi_encoder_rad("sold", a) - unghi_motor_rad("sold", a)) < 1e-12,
            "sold 1:1")
    v += ok(abs(unghi_encoder_rad("genunchi", a) - unghi_motor_rad("genunchi", a)) > 1.0,
            "la genunchi encoderul NU vede axul motor: 19:25 pe fulia condusa")

    # 3. dus-intors exact, pe ambele articulatii cu encoder
    for art in ("sold", "genunchi"):
        for a in (-0.3, 0.0, 0.7, 1.9):
            e = unghi_encoder_rad(art, a)
            v += ok(abs(unghi_articulatie_din_encoder(art, e) - a) < 1e-12,
                    "%s: dus-intors %.4f" % (art, a))

    # 4. HOMING: nu e gata pana nu sunt citite TOATE cele cu encoder
    J = ["left_hip_joint", "left_knee_joint", "left_ankle_joint",
         "right_hip_joint", "right_knee_joint", "right_ankle_joint"]
    h = Homing(J)
    v += ok(len(h.cere_encoder()) == 4, "4 articulatii cu encoder, nu 6")
    v += ok(not h.gata(), "homing nu are voie sa fie gata la pornire")
    for j in h.cere_encoder()[:-1]:
        h.citeste(j, unghi_encoder_rad(familie(j), 0.4))
    v += ok(not h.gata(), "cu o articulatie necitita, homing NU e gata")
    v += ok(len(h.raport()["lipsa"]) == 1, "raportul trebuie sa spuna CARE lipseste")
    ultima = h.cere_encoder()[-1]
    h.citeste(ultima, unghi_encoder_rad(familie(ultima), 0.4))
    v += ok(h.gata(), "cu toate citite, homing e gata")
    v += ok(all(abs(x - 0.4) < 1e-12 for x in h.unghi.values()),
            "unghiurile recuperate trebuie sa fie cele reale")
    v += ok(len(h.raport()["fara_encoder"]) == 2, "gleznele apar ca fara encoder")

    # 5. CONTROL NEGATIV: o citire esuata tine homing-ul inchis, oricat de multe
    # altele au reusit. Fara asta, 'gata' ar putea fi doar 'am incercat'.
    h2 = Homing(J)
    for j in h2.cere_encoder():
        h2.citeste(j, unghi_encoder_rad(familie(j), 0.2))
    v += ok(h2.gata(), "premisa: toate citite")
    h2.esueaza(h2.cere_encoder()[0])
    v += ok(not h2.gata(), "o citire ESUATA trebuie sa inchida homing-ul la loc")
    v += ok(h2.cere_encoder()[0] in h2.raport()["lipsa"], "cea esuata apare in lipsa")
    # citire None = esec, nu zero
    h3 = Homing(J)
    v += ok(h3.citeste("left_hip_joint", None) is False, "citirea None e esec")
    v += ok(h3.stare["left_hip_joint"] == STARE_ESUAT, "starea devine esuat")

    # 6. NU se cuantizeaza nimic: rezolutia e GAP 6, deci nu se inventeaza
    e = unghi_encoder_rad("sold", 0.123456789)
    v += ok(abs(unghi_articulatie_din_encoder("sold", e) - 0.123456789) < 1e-12,
            "citirea e continua; nicio rezolutie inventata")

    print("SELFTEST transmisie_core OK (%d verificari)." % v)
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
