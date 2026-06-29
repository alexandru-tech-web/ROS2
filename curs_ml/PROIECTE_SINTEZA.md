# PROIECTE_SINTEZA.md -- proiecte integratoare pe datele tezei

Patru proiecte care leaga mai multe module pe datele mele (`date_sar`). Fiecare
are un livrabil (script tip notebook + figura + interpretare scrisa scurta). Se
completeaza DUPA ce exista modulele necesare (vezi coloana 'Cere').

ONESTITATE: datele sunt sintetice, semanate din C1/M. Proiectele demonstreaza
metodologia; cifrele finale cer datele reale de campanie.

## P1 -- Pipeline de predictie a latentei

- Cere: M04 + M05 + M06 + M07 + M18.
- Sarcina: de la date brute (`make_latency_dataset`) la un model regularizat,
  validat corect, care prezice `rtt_ms`. Raporteaza RMSE + interval, comparat cu
  o linie de baza (media per conditie).
- Livrabil: scriptul proiectului, o figura predictie vs real, o interpretare.
- Stare: TODO (dupa M18).

## P2 -- Clasificator de link 'usable' calibrat si explicat

- Cere: M04 + M08 + M09 + M14.
- Sarcina: pe `make_link_usability_dataset` (clase dezechilibrate), antreneaza un
  clasificator, alege pragul pe recall-ul clasei rare, calibreaza probabilitatile
  si explica feature-urile (importanta prin permutare / SHAP).
- Livrabil: curba PR + diagrama de calibrare + top feature-uri, cu interpretare.
- Stare: TODO (dupa M14).

## P3 -- Predictia deznodamantului misiunii

- Cere: M04 + M12 + M13 + M14.
- Sarcina: pe `make_mission_outcome_dataset`, un ensemblu (Random Forest /
  gradient boosting) pentru `mission_complete`, cu importanta de feature si reguli
  interpretabile (ce conditii prabusesc misiunea).
- Livrabil: comparatie arbore-vs-ensemblu + importanta feature, cu interpretare.
- Stare: TODO (dupa M14).

## P4 (capstone) -- Politica adaptiva vs statica

- Cere: M17 / M19 + M21 + M22.
- Sarcina: un predictor de link cu incertitudine -> o politica RL de comutare
  (DDS/Zenoh/QoS) -> impachetat ca nod ROS 2 (`link_predictor_node`). Compara
  politica adaptiva cu comutarea statica si scoate o figura comparativa pentru un
  articol A2.
- Livrabil: nodul ROS + figura adaptiv-vs-static + interpretare. Inchide cursul
  inapoi in teza (contributia C3).
- Stare: TODO (dupa M22).
