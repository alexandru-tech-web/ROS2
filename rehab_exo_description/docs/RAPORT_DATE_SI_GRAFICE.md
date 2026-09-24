# Date, grafice si nivelul validarii — twin LLR

## Verdict scurt

Graficele curente sunt relevante pentru validarea **software si cinematica** a
simularii. Nu sunt suficiente pentru validare mecanica sau clinica. Diferenta
este pastrata in titluri si in raport, astfel incat o curba sintetica sa nu poata
fi confundata cu o masurare de pe robotul fizic.

## Legatura dintre PDF, model si export

| Marime | Element documentat | Coloana CSV | Figura/Raport | Statut curent |
|---|---|---|---|---|
| unghi sold/genunchi | encoder absolut RS485-RTU | `*.pos` | referinta vs feedback, ROM | feedback Gazebo |
| viteza articulara | derivata/stare axa | `*.vel` | viteze si varfuri | feedback Gazebo |
| referinta controler | comanda de pozitie | `*.cmd` | urmarire si eroare | comanda software |
| efort articulatie | stare Gazebo | `*.effort_sim` | efort simulat | NU cuplu fizic |
| cuplu sold/genunchi | M2210B | `cuplu.*` | cuplu sintetic | model declarat |
| unghi glezna | BWK216 | `unghi_glezna.*` | unghi dedicat | model declarat |
| forta/moment talpa | TR69-1500 | `f6d.*` | Ff, FN, MC | model declarat |
| lungime gamba | rigla 406 | `rigla.*` | reglaj masurat | model declarat |

Componentele 6D care nu sunt definite de document sunt exportate ca `NaN`, nu
ca zero. Astfel, absenta masurarii nu capata aspectul unei masurari nule.

## Grafice recomandate pentru fiecare sesiune

1. referinta si feedback pentru sold, genunchi si glezna, separat stanga/dreapta;
2. eroarea de urmarire in timp si RMSE pe intervalul activ;
3. viteza articulara si apropierea de limite;
4. efortul Gazebo, intotdeauna etichetat `SIMULATED`;
5. M2210B sintetic pentru verificarea lantului de date;
6. Ff, FN si MC la ambele talpi;
7. unghiul BWK216 fata de unghiul articular si offsetul de montaj;
8. rigla 406 fata de comanda reglajului de gamba;
9. diferenta stanga-dreapta si indicatorii de simetrie;
10. rata de esantionare, jitter, pierderi/NaN si durata simulat/perete.

Curbele live sunt instrument de operare si depanare. Figurile offline si
raportul PDF sunt rezultatul reproductibil, deoarece poarta exercitiul, data,
commit-ul si conventia cinematica din acelasi CSV.

## Ce poate fi afirmat acum

- controlerul urmareste traiectoriile in simulare;
- limitele de pozitie si viteza pot fi verificate;
- achizitia celor sase axe si a canalelor de senzori poate fi testata end-to-end;
- simetria numerica stanga-dreapta poate fi analizata;
- fiecare rezultat poate fi legat de versiunea de cod si de exercitiu.

Nu se poate afirma inca fidelitatea cuplului, exactitatea senzorilor, siguranta
pentru pacient sau eficienta terapeutica. Acestea cer calibrare, masurari fizice
independente si protocol aprobat.

## Geometria vizuala

Modelul distinge pacientul, cele doua lanturi mecanice si reglajele, dar ramane
o anvelopa functionala, nu CAD. Au fost adaugate repere vizuale schematice pentru
M2210B, BWK216, TR69-1500 si rigla 406. Urmatoarea crestere de fidelitate trebuie
facuta numai dupa masurarea/capturarea geometriei reale:

- axe si plane ale articulatiilor;
- distante sold-genunchi-glezna si cursele reglajelor;
- puncte de prindere, curele si opritoare;
- volumele motoarelor, reductoarelor si carcaselor;
- pozitia reala a senzorilor si cablajului;
- mase, centre de masa si inertii.

Pana atunci, nu se adauga dimensiuni „plauzibile” la coliziuni sau inertii.
