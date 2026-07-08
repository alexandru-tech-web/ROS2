# MANIFEST_DATE.md -- SURSA DE ADEVAR pentru datele campaniei C1

ACEST FISIER este sursa de adevar pentru datele C1 (inlocuieste referinta istorica la
SURSA_DATELOR_C1.md, care NU exista in sistem). Documentatia per-mediu: README_SIL.md si
README_HIL_WIFI.md din ~/DATE_CAMPANIE/. Fisiere canonice (read-only):
<env>/date/<rmw>/<cond>/rep<N>/transport_p<P>_summary.json (+ transport_p<P>.csv brute).
Generat prin scanarea ~/DATE_CAMPANIE/ (SHA256). Nu s-au modificat datele.

## Matrice de completitudine (rep prezente / asteptate; received=0 marcat)

| env | rmw | conditie | p64 | p4096 | p65536 | note received=0 |
|-----|-----|----------|-----|-------|--------|-----------------|
| SIL | cyclonedds | ideal | 10/10 | 10/10 | 10/10 | - |
| SIL | cyclonedds | loss_5 | 10/10 | 10/10 | 10/10 | - |
| SIL | cyclonedds | loss_15 | 10/10 | 10/10 | 10/10 | - |
| SIL | cyclonedds | loss_20 | 10/10 | 10/10 | 10/10 | - |
| SIL | cyclonedds | loss_25 | 10/10 | 10/10 | 10/10 | - |
| SIL | cyclonedds | loss_30 | 10/10 | 10/10 | 10/10 | - |
| SIL | cyclonedds | lat200_jit50 | 10/10 | 10/10 | 10/10 | - |
| SIL | cyclonedds | lat200_l15 | 10/10 | 10/10 | 10/10 | - |
| SIL | zenoh | ideal | 10/10 | 10/10 | 10/10 | - |
| SIL | zenoh | loss_5 | 10/10 | 10/10 | 10/10 | - |
| SIL | zenoh | loss_15 | 10/10 | 10/10 | 10/10 | - |
| SIL | zenoh | loss_20 | 10/10 | 10/10 | 10/10 | - |
| SIL | zenoh | loss_25 | 10/10 | 10/10 | 10/10 | - |
| SIL | zenoh | loss_30 | 10/10 | 10/10 | 10/10 | p4096:1, p65536:1 |
| SIL | zenoh | lat200_jit50 | 10/10 | 10/10 | 10/10 | - |
| SIL | zenoh | lat200_l15 | 10/10 | 10/10 | 10/10 | - |
| HIL_WIFI | cyclonedds | ideal | 5/5 | 5/5 | 5/5 | - |
| HIL_WIFI | cyclonedds | loss_5 | 5/5 | 5/5 | 5/5 | - |
| HIL_WIFI | cyclonedds | loss_15 | 5/5 | 5/5 | 5/5 | - |
| HIL_WIFI | cyclonedds | loss_20 | 5/5 | 5/5 | 5/5 | p65536:1 |
| HIL_WIFI | cyclonedds | loss_25 | 5/5 | 5/5 | 5/5 | p65536:1 |
| HIL_WIFI | cyclonedds | loss_30 | 5/5 | 5/5 | 5/5 | p65536:5 |
| HIL_WIFI | cyclonedds | lat200_jit50 | 5/5 | 5/5 | 5/5 | - |
| HIL_WIFI | cyclonedds | lat200_l15 | 5/5 | 5/5 | 5/5 | p65536:2 |
| HIL_WIFI | zenoh | ideal | 5/5 | 5/5 | 5/5 | - |
| HIL_WIFI | zenoh | loss_5 | 5/5 | 5/5 | 5/5 | - |
| HIL_WIFI | zenoh | loss_15 | 5/5 | 5/5 | 5/5 | p65536:1 |
| HIL_WIFI | zenoh | loss_20 | 5/5 | 5/5 | 5/5 | p64:3, p4096:3, p65536:2 |
| HIL_WIFI | zenoh | loss_25 | 5/5 | 5/5 | 5/5 | p64:4, p4096:3, p65536:5 |
| HIL_WIFI | zenoh | loss_30 | 5/5 | 5/5 | 5/5 | p64:2, p4096:4, p65536:5 |
| HIL_WIFI | zenoh | lat200_jit50 | 5/5 | 5/5 | 5/5 | p64:4, p4096:4, p65536:5 |
| HIL_WIFI | zenoh | lat200_l15 | 5/5 | 5/5 | 5/5 | p64:5, p4096:5, p65536:5 |

Total summary JSON canonice: 720 (asteptate 720, prezente 720).
received=0 = pierdere ~totala la loss/lat mare (Zenoh pe HIL); DATE prezente, fara RTT.

## SHA256 + dimensiune -- fisiere canonice summary (sortate)

```
9d23d50952da4cbd5890c6ea6873bfd1d0e42904d4cd7ac8f47007d8b50a086a       255  SIL/date/cyclonedds/ideal/rep1/transport_p4096_summary.json
cabba14baf44bdf9c1d2cbf123c4d949292548c7caf3189114d438aa2a7e94ff       253  SIL/date/cyclonedds/ideal/rep1/transport_p64_summary.json
b08b5d0c18c85f9d28186a733d6139f5cd131fd529bd2fcb55eeeddf6acc294b       256  SIL/date/cyclonedds/ideal/rep1/transport_p65536_summary.json
cd4dba8e0cceff4bec313f63b065d6b216ba6580058d811e8e199feb4dcb3b28       255  SIL/date/cyclonedds/ideal/rep10/transport_p4096_summary.json
f7485d3918c7f905bf7d932f5d21aef826d41af0266c4e2847609338f193e3eb       253  SIL/date/cyclonedds/ideal/rep10/transport_p64_summary.json
4897e042a8e598c31d1af6974f6fb8204a3cc79e7f0948c8a26932944349a135       255  SIL/date/cyclonedds/ideal/rep10/transport_p65536_summary.json
435c506f58b745248b6235c9c901ebc2a0baf859cb6aa5eee8b26fbdc2096080       254  SIL/date/cyclonedds/ideal/rep2/transport_p4096_summary.json
34ce6d72adb94a087ccfd26727a05956d73fe61be04029e0c8608d6eaecea8e1       252  SIL/date/cyclonedds/ideal/rep2/transport_p64_summary.json
4cf9f6ba3c700324f6bdf80fd79a653edd5d45e98d30da8cff685224308e5cef       256  SIL/date/cyclonedds/ideal/rep2/transport_p65536_summary.json
8705c478d6a22829438cef699be6c5f7a741687f22ee30cd8d9c7f5d49fa6a2b       255  SIL/date/cyclonedds/ideal/rep3/transport_p4096_summary.json
0c496d5a0d692aa7ec3b35d0100293d8fdba7e4f2f318c0878b264b955d578cd       252  SIL/date/cyclonedds/ideal/rep3/transport_p64_summary.json
22c5db7d5bbde31cb79d7a0487f66801ed4e86cb872787c5a2e12bad1d63aefe       256  SIL/date/cyclonedds/ideal/rep3/transport_p65536_summary.json
f6efa5f47bb186cf6494a31f2c7739c595ffde8170d67f1335ea0b079d28c331       254  SIL/date/cyclonedds/ideal/rep4/transport_p4096_summary.json
b5b6b61f0759dc74d94cf4d39966af133dcf65ae898f4235a3003dadb72b2d17       251  SIL/date/cyclonedds/ideal/rep4/transport_p64_summary.json
9038d08c1e81ba646dfcea1b8af2ea6eaf458743653e633aec46fb03ce5cbbeb       256  SIL/date/cyclonedds/ideal/rep4/transport_p65536_summary.json
e9810597389ba9aaccafc5c9621e7ccf48a045f39b2aeac7721939a34ae4844d       254  SIL/date/cyclonedds/ideal/rep5/transport_p4096_summary.json
305b5f9d4811723a4a7b8f9b603a1768f64649c42e09970cc52c2bcd06b3296a       253  SIL/date/cyclonedds/ideal/rep5/transport_p64_summary.json
76ecd5949172186c3181744133d206eb03a958af956a4557b6f714a3b089f16b       255  SIL/date/cyclonedds/ideal/rep5/transport_p65536_summary.json
e83b223bf1599c03b3e6deaa569b953360fb194b716fd2145be6285f549cc165       254  SIL/date/cyclonedds/ideal/rep6/transport_p4096_summary.json
734a5e4244fc029640ce37fe4cc56df95dba475d73ba9d849acca9dcb5d7f986       253  SIL/date/cyclonedds/ideal/rep6/transport_p64_summary.json
9167dd9d620dd5f85816d666e76ad4364f9a82c23d0752e51df2d8232ff69d96       256  SIL/date/cyclonedds/ideal/rep6/transport_p65536_summary.json
b17daa2171366aa84a56283223a1d994dd9a1bfafa64a053efca163461e2be8f       255  SIL/date/cyclonedds/ideal/rep7/transport_p4096_summary.json
c3d9a7ac4616154d2ba287a42a178f0b94e9f5479a11a1e343038a70f0e81467       253  SIL/date/cyclonedds/ideal/rep7/transport_p64_summary.json
b5f6fa7ac30a58713295223a896c3b0be7bf9a1829d72300a2fa26140d75d46d       253  SIL/date/cyclonedds/ideal/rep7/transport_p65536_summary.json
97faaa9dda00eb3aee29b5aa1481c71ab56160ce40ff179d62230603bc061369       253  SIL/date/cyclonedds/ideal/rep8/transport_p4096_summary.json
b82fefa322c0cc4bc6004725af90aa6639e405235240a17dbed10436151113b5       253  SIL/date/cyclonedds/ideal/rep8/transport_p64_summary.json
d5b0af130d2d729ccce27847f02bf3c55c0b0573fbef3f58e86e4e01ba707b89       255  SIL/date/cyclonedds/ideal/rep8/transport_p65536_summary.json
ce5a308a7de413feb8070a6fe42bc7249d6f5f114d6a14f2235288233d420992       255  SIL/date/cyclonedds/ideal/rep9/transport_p4096_summary.json
ac5573447605c6100893bd98054ded437d79242cf79063c4a98c478c481f1210       253  SIL/date/cyclonedds/ideal/rep9/transport_p64_summary.json
d3ec416b1c80d882b87e7757188a7b7c24f05f4393705a72f993910525bd5b66       255  SIL/date/cyclonedds/ideal/rep9/transport_p65536_summary.json
ccd3b472e427a6437e5a61f76dd23b36767b88633f96a09bbbdbd9f98761a9a5       270  SIL/date/cyclonedds/lat200_jit50/rep1/transport_p4096_summary.json
1f5d054551f46e3d23a7b872a13b2a8f78bf1e23bfc5d23dff0ed7ad917d33b4       268  SIL/date/cyclonedds/lat200_jit50/rep1/transport_p64_summary.json
dc5452ff0d8d9b44dbeb51e3921e35c0689dd0840b2eceb7410fc1c04e2be1e4       274  SIL/date/cyclonedds/lat200_jit50/rep1/transport_p65536_summary.json
b6c9689232e7cfd308474255f4f5c1470bd55957a38584ed9509c063c8f3e099       272  SIL/date/cyclonedds/lat200_jit50/rep10/transport_p4096_summary.json
55b1412490539d41f18ed5c756166793a681c8a16bfb35b8cb80310ecc29721a       264  SIL/date/cyclonedds/lat200_jit50/rep10/transport_p64_summary.json
281ae869b7dd6f718acbeae35242b859dd959cf48d436f96c458999c0b92dc08       274  SIL/date/cyclonedds/lat200_jit50/rep10/transport_p65536_summary.json
88578e94e88cd335477f187d8f8dcb3ed26e6f2f6fab0085c02cc59c25529498       272  SIL/date/cyclonedds/lat200_jit50/rep2/transport_p4096_summary.json
e73d69bb27fde9530f97f8e3731dbd7b1fc044a8fd2796151ecd5c46de5ee110       268  SIL/date/cyclonedds/lat200_jit50/rep2/transport_p64_summary.json
512a61865b471f4ba89fab96dd9a2b531dd9f6fe7dcf7464d6af1dd5fb4e55cb       275  SIL/date/cyclonedds/lat200_jit50/rep2/transport_p65536_summary.json
785d6575debc0e15fb6cc36fb9e82327624b3b5fc009fafafe7b0e2c1ca33d0c       270  SIL/date/cyclonedds/lat200_jit50/rep3/transport_p4096_summary.json
8099902d59b790a99b6601ca10444933ebc4c8473f1c9947d3d9a4e6c7abbffc       268  SIL/date/cyclonedds/lat200_jit50/rep3/transport_p64_summary.json
ff827e2a20b7716e19c3ade05f84fbd8110b415b041d968e2f181ad41e1e079e       272  SIL/date/cyclonedds/lat200_jit50/rep3/transport_p65536_summary.json
912add7abb33d4f2a2376c411bf7b6d56e26aaee9a2e137bf1d9a99ae935b7ca       270  SIL/date/cyclonedds/lat200_jit50/rep4/transport_p4096_summary.json
d761ff6fa00e5d376a8a274a0e55c593dacc41bf1392a818ff97cfe7017e527f       268  SIL/date/cyclonedds/lat200_jit50/rep4/transport_p64_summary.json
54b4b160624d74b9283c2a30c4e1f88245a1a6c24e8e2de96d1fbe463233e946       274  SIL/date/cyclonedds/lat200_jit50/rep4/transport_p65536_summary.json
8ddded8e1694d032b94512442339dcb08000a4626048e475e331b46d897b76c6       270  SIL/date/cyclonedds/lat200_jit50/rep5/transport_p4096_summary.json
93d3002ae055a72edb905bf33864d0270389ada90d828a1267b80c6361a96140       267  SIL/date/cyclonedds/lat200_jit50/rep5/transport_p64_summary.json
2423764faca59cfffb3b980761036153841c729a11ee08ac97ceaaf6e56546e7       276  SIL/date/cyclonedds/lat200_jit50/rep5/transport_p65536_summary.json
2efb5b4360ab691e6a3b5cb3312a83730899c84885e5c970ea65a85bd6f92be0       272  SIL/date/cyclonedds/lat200_jit50/rep6/transport_p4096_summary.json
7476246614a0944060021be44796db8121268be412869e43790410aa53156e3a       268  SIL/date/cyclonedds/lat200_jit50/rep6/transport_p64_summary.json
506508f7d795edaf2a0d48ad9cc9d538c4f057d26a65d5950d873bf69912c6a1       270  SIL/date/cyclonedds/lat200_jit50/rep6/transport_p65536_summary.json
619e2aa9fdb6e10f02b28ee5b0ee98ef0d117429813b15be8c9459c278513c64       272  SIL/date/cyclonedds/lat200_jit50/rep7/transport_p4096_summary.json
9976f0dca3d7d2449a1ace52116b47ac73c8c9869ee7a5fd4303035e93f863f2       265  SIL/date/cyclonedds/lat200_jit50/rep7/transport_p64_summary.json
d78666d0e35c32f33d921aa0738c384477382407e0609720a6a589c564e21e75       269  SIL/date/cyclonedds/lat200_jit50/rep7/transport_p65536_summary.json
30698e2a0fe0060a2a8a8ea782426f43bcc21e3dad3d916d784aac6854c5878b       272  SIL/date/cyclonedds/lat200_jit50/rep8/transport_p4096_summary.json
769f0eaf3e9177ed5d86dd8003cc21301878a6e23c9c71edab6763dfd55934a7       267  SIL/date/cyclonedds/lat200_jit50/rep8/transport_p64_summary.json
d23eeb0a6f1ec01b242aed667d3ec9b684161b0d741cac3727b60a2222f4d669       273  SIL/date/cyclonedds/lat200_jit50/rep8/transport_p65536_summary.json
cdb4f64969e88a78ddd25cb22bd1a9c2e4c0f61602a3fd8ce783ee3638980bf3       270  SIL/date/cyclonedds/lat200_jit50/rep9/transport_p4096_summary.json
070b7250ed85b16ea2bbb4d1156d7faf656039b2397b1f7975df6cab107f92df       268  SIL/date/cyclonedds/lat200_jit50/rep9/transport_p64_summary.json
3f280575f30da0ff3c569f262870a28532e3eb8d49ed7f81b270673cd25911a7       272  SIL/date/cyclonedds/lat200_jit50/rep9/transport_p65536_summary.json
ad79e6376c5d2aac05de0c29675e274a10714a3aa18d2d2b9d190bec379d2fe8       276  SIL/date/cyclonedds/lat200_l15/rep1/transport_p4096_summary.json
8ef8a23dd08b13863c3f150a4cee7e1510ffcd60e838d31f04d318682c8711c3       273  SIL/date/cyclonedds/lat200_l15/rep1/transport_p64_summary.json
e97df683e1bfef7fd8e0bfa1d3dcea774ce8ddd7af22318cc3ccdc2e7fdb310b       273  SIL/date/cyclonedds/lat200_l15/rep1/transport_p65536_summary.json
99e8c760a172ce2914102d66d1e89b870e09c7b57ba455f977228822c234d2e7       276  SIL/date/cyclonedds/lat200_l15/rep10/transport_p4096_summary.json
110f27ab8422c80d82af92a728672afb1a34da6338c7cdf8f8883d9d39a79435       273  SIL/date/cyclonedds/lat200_l15/rep10/transport_p64_summary.json
0df8f2b19bb95e95c53725724b06e7d2b3f8c74cc1c92730208422c1c770ba67       275  SIL/date/cyclonedds/lat200_l15/rep10/transport_p65536_summary.json
afdf59c72e4d6a84059371e18fcbfd33e273f39296bc86dc61faf0dbb3b963ab       274  SIL/date/cyclonedds/lat200_l15/rep2/transport_p4096_summary.json
72203967d1d1453a962b5a012cb62da29617dcebe25b4a8101a8ffc813415686       272  SIL/date/cyclonedds/lat200_l15/rep2/transport_p64_summary.json
c4acdb78cb76c632960a1bc3d4e8e6c7a34874a17a5ab39e2738ca06c0cd050a       274  SIL/date/cyclonedds/lat200_l15/rep2/transport_p65536_summary.json
a5743961f7352a10cc2c3ddcc3d9198394945bdbbf51c0683b20684bac99da70       275  SIL/date/cyclonedds/lat200_l15/rep3/transport_p4096_summary.json
20f2e6e5f4fc0e3a4c211deed8e1e05850cc3313a531a1cca98112367db13951       272  SIL/date/cyclonedds/lat200_l15/rep3/transport_p64_summary.json
c15580d203b80f65416954321a4ebb173b2eb856f1b5f2635f346022d0eebf5c       273  SIL/date/cyclonedds/lat200_l15/rep3/transport_p65536_summary.json
c7b9ab8baf156bc4dcdb0a7a13a97c473f1bca7cf0f8468fb48c3ae06b92d531       276  SIL/date/cyclonedds/lat200_l15/rep4/transport_p4096_summary.json
6a687cce2fd9b892afeb4f004f088a08c849c34667002654eda8264ee1fc23da       273  SIL/date/cyclonedds/lat200_l15/rep4/transport_p64_summary.json
2dd1142471d58ab88bde457e7178313593f5785bfd57aa230d6422297d545685       274  SIL/date/cyclonedds/lat200_l15/rep4/transport_p65536_summary.json
7f29e07063d50cc5117d196d133cf30641d6dc17a5317a0ce868ee93627d0790       276  SIL/date/cyclonedds/lat200_l15/rep5/transport_p4096_summary.json
47ee3901204c6d083c396029a25f00826da8daa620732703fb6371fe96c4249e       273  SIL/date/cyclonedds/lat200_l15/rep5/transport_p64_summary.json
f4c15ad3e1b254c124615c1f3f167347c09a40a4f86e79464b78ccd192a54bbf       275  SIL/date/cyclonedds/lat200_l15/rep5/transport_p65536_summary.json
d30d51788cc5ac0fa667fee38530330b46b3d0b68334e3f8c29063a017ba492c       272  SIL/date/cyclonedds/lat200_l15/rep6/transport_p4096_summary.json
ef1b5dbf0b7e1da506f4e697556059fdd7b84842c12e85bd23f9a52e1b30a48f       273  SIL/date/cyclonedds/lat200_l15/rep6/transport_p64_summary.json
65e94f0f2bc676bfdd760c2769a8e954c7b4927dd4847ba489c7df8423519557       274  SIL/date/cyclonedds/lat200_l15/rep6/transport_p65536_summary.json
f5da80ecde91a046a9bb61e4b2efb0e51cf09a7f912e20e6365ff9f93b997e12       274  SIL/date/cyclonedds/lat200_l15/rep7/transport_p4096_summary.json
49cc2aeb6b38e0b6ea1b5244740df71ee3d8c54adb53b6a456c09de1f6d01323       273  SIL/date/cyclonedds/lat200_l15/rep7/transport_p64_summary.json
7f9c5077180ad80682d61a188ef9be42639f437fce5161d8dae83330c0eb8473       272  SIL/date/cyclonedds/lat200_l15/rep7/transport_p65536_summary.json
0f9bb6e529a2b4abea5d43a3784bb4f84e008524d8fcc93dcb6e81eec895c5ef       273  SIL/date/cyclonedds/lat200_l15/rep8/transport_p4096_summary.json
1eddcdc4d03582810a75e2cb3a956d704595d7567746ff4838c4e41181b5fbbe       273  SIL/date/cyclonedds/lat200_l15/rep8/transport_p64_summary.json
a4fce1de79ea8a19f57441f2de9b76eef416f62c68a3d922f90e75b8f0695815       274  SIL/date/cyclonedds/lat200_l15/rep8/transport_p65536_summary.json
21c845cd94fe1f50cb2703bad6f05513685cc75c32552e3287863f6b5dcaabd8       274  SIL/date/cyclonedds/lat200_l15/rep9/transport_p4096_summary.json
1ab7cf296e962759d1f071f3969fecf5d495275d4ccdf8271e7822b46ba3319f       273  SIL/date/cyclonedds/lat200_l15/rep9/transport_p64_summary.json
6988358095da619f21bcb864948ac3a8bdb3e5642c9a1346ae616d37a05c70d6       275  SIL/date/cyclonedds/lat200_l15/rep9/transport_p65536_summary.json
f131e9d4a1ffba84f57dcd5fb95467ff78e30379aee3356c17e9facb95e96f99       265  SIL/date/cyclonedds/loss_15/rep1/transport_p4096_summary.json
dc2ddb85628600c1ffd10a772a72502c49049aca64d7593dd7965fb251b0ad89       259  SIL/date/cyclonedds/loss_15/rep1/transport_p64_summary.json
8460c151a22c24eecf1a48b1e96ae222551d6096f8a26125149e0cecf1ab18c1       276  SIL/date/cyclonedds/loss_15/rep1/transport_p65536_summary.json
086ab278fc12e6d2563ae0253376d8a3549727c4bf79a0e891eb939fe85c3065       271  SIL/date/cyclonedds/loss_15/rep10/transport_p4096_summary.json
fabab5058dfde32198419094e20d510ee31d8a6b64d070039b971a1c929fe2fc       260  SIL/date/cyclonedds/loss_15/rep10/transport_p64_summary.json
400ee691f5c737b42a064278c468a293f705cb17644fbb9834198ea834601acb       274  SIL/date/cyclonedds/loss_15/rep10/transport_p65536_summary.json
44b32f82963f8b146c9bfdc066b8ffcf0a909976e753bd9ad3b508468fd8f1db       272  SIL/date/cyclonedds/loss_15/rep2/transport_p4096_summary.json
6b5f220d1bbead3994f1a2a1f458d2926371b93187cc0f4a20ceae825b51c915       263  SIL/date/cyclonedds/loss_15/rep2/transport_p64_summary.json
ecb787394fe68f0c075ffa8b436b1fcf072c357a48a89d4251cc02fa3dd90c2d       275  SIL/date/cyclonedds/loss_15/rep2/transport_p65536_summary.json
9db19220b0ed264b49210eac1774974c7ee81e44dc308e0a82d739c10e21e911       268  SIL/date/cyclonedds/loss_15/rep3/transport_p4096_summary.json
4bce4baee7d8e75b97039f9dd478c4f4251b799aee40d559ff7ac866bf750bd5       260  SIL/date/cyclonedds/loss_15/rep3/transport_p64_summary.json
215500ae96d669b294dc3c2437ee2dd3b3f13eadb32a8dc263e3221db67849b9       274  SIL/date/cyclonedds/loss_15/rep3/transport_p65536_summary.json
7c5bddcbeed08ae8cbb06d7e664dc9dcd4edd49c6595699e95d03432a28a2700       271  SIL/date/cyclonedds/loss_15/rep4/transport_p4096_summary.json
9b34b5df8e1e309e6a792c41d9f578a389ea17a0c561d7fd6d255437f83639c6       258  SIL/date/cyclonedds/loss_15/rep4/transport_p64_summary.json
c3d2b71dd39b66ac48239bff5c1566eea6f67d0fd51091b7f12939f822185484       277  SIL/date/cyclonedds/loss_15/rep4/transport_p65536_summary.json
70a0189723ea87832d429b1d51f7310bcd258b49494410f54540b884e7aa5c26       271  SIL/date/cyclonedds/loss_15/rep5/transport_p4096_summary.json
e4da66264fc0106f686c8c10da7bde1d6230176088375d726f7bcb1841e5643d       263  SIL/date/cyclonedds/loss_15/rep5/transport_p64_summary.json
f9cf252488c158ace5a0672d9d8c7ef795e98ac31abb069c11030f18628e4bcd       275  SIL/date/cyclonedds/loss_15/rep5/transport_p65536_summary.json
0a0a8271de61e7f839ec6ab36be73c73dab3ae81a3862bb4d6d1441c65412139       271  SIL/date/cyclonedds/loss_15/rep6/transport_p4096_summary.json
25a21ccdb7055aecd799145b5c5f6d6022827394cb07fa1c00d4bf3af7e51815       261  SIL/date/cyclonedds/loss_15/rep6/transport_p64_summary.json
6db1fd91d1dc8c694d9442480c79ee2ca76529522382c4f7cd197a553ca93e86       275  SIL/date/cyclonedds/loss_15/rep6/transport_p65536_summary.json
3fa7194a26c9b8ae2f61ecfbf622122f3eb40fbb19bfd1ef78edffa203e6a134       269  SIL/date/cyclonedds/loss_15/rep7/transport_p4096_summary.json
37c43e57c7ee515a238790c63389960d5b774abc7d570e48fc6c1357693816b1       261  SIL/date/cyclonedds/loss_15/rep7/transport_p64_summary.json
a6e77f8d18d336f5ad674b3af0cb261c383f2b581807f0677cf88de8f5e4428e       276  SIL/date/cyclonedds/loss_15/rep7/transport_p65536_summary.json
3be621491a66397e9073300d1148df3a752ec7c0241c053e336a31002d4eb815       271  SIL/date/cyclonedds/loss_15/rep8/transport_p4096_summary.json
5bff2fed9f1ee91e5e5d2a6c9b5e61f0e1ec3b2b16f7beb05a812f3dc23a6a8b       258  SIL/date/cyclonedds/loss_15/rep8/transport_p64_summary.json
614d38eae13df18418c433851921703daf74076e1b0e69d886bc6ba10f7f8230       276  SIL/date/cyclonedds/loss_15/rep8/transport_p65536_summary.json
c91e2a85a3904fc8d2b2074e9b9a0fda2b88fddcab870557b9ce6f53e9b6318e       268  SIL/date/cyclonedds/loss_15/rep9/transport_p4096_summary.json
649bee485d7fdefea763586c364df3c847be4d3a9d80eaeb8757bfb108cf6d2b       261  SIL/date/cyclonedds/loss_15/rep9/transport_p64_summary.json
62ba65b73a69634ed2c4c6c990e0906d83b6b83111db22fc0d3549bdf4adec06       276  SIL/date/cyclonedds/loss_15/rep9/transport_p65536_summary.json
809677950c01ab3579af38c5da086c29f820b061fab9fc7ebcb010e1ed94d2c7       273  SIL/date/cyclonedds/loss_20/rep1/transport_p4096_summary.json
0f6027af77bbb64e450d93d8f456b0ece193835cfc5500178cac3d5ff20cb7b6       263  SIL/date/cyclonedds/loss_20/rep1/transport_p64_summary.json
2d41759a852691c6684444c44a2b41db50297bce1c9fc54eb5ece2da373534ab       276  SIL/date/cyclonedds/loss_20/rep1/transport_p65536_summary.json
a2c1807427fe5d99eef45fb88dc08383771b8b06cdd1ab9c62a4130a425cc497       272  SIL/date/cyclonedds/loss_20/rep10/transport_p4096_summary.json
e6cb5ac2eee0c5a05a34e483055b5ea58a147cfeb71933eb101635f790c69298       263  SIL/date/cyclonedds/loss_20/rep10/transport_p64_summary.json
3cd80d5c3fdf1da1732a94e6d1d8f464298cf7619b93f2e488497f86ddbae644       275  SIL/date/cyclonedds/loss_20/rep10/transport_p65536_summary.json
4c0fe3f52ac380156307f7fed1817d08e1dc9041cf4030ba65756cf836b6470d       275  SIL/date/cyclonedds/loss_20/rep2/transport_p4096_summary.json
50b47877a1f1cf1ce94f9dd8d58aa7e407499603fd5a792adaf9684381cdcfa1       262  SIL/date/cyclonedds/loss_20/rep2/transport_p64_summary.json
ecd23a8eb1c1b86e95621b991f61875fd29b1a14957496aaf934716fcf1b3bfb       276  SIL/date/cyclonedds/loss_20/rep2/transport_p65536_summary.json
494feb75ba46d702b2e25b7cb2624f69c02877f94633e5d02ef174e61b8eb11f       270  SIL/date/cyclonedds/loss_20/rep3/transport_p4096_summary.json
c71a0845ee0c59d943928ad3a050e95ef3656d6dcfc03a70c674ddea87f69a35       263  SIL/date/cyclonedds/loss_20/rep3/transport_p64_summary.json
f60b1e5f33931323bd9a26ecd674ee9c81774dc17b33cfac2985daa1a26adb75       275  SIL/date/cyclonedds/loss_20/rep3/transport_p65536_summary.json
ab59e2fd0eb60a715999136ebb36debcad25aa3be07e05a97078d98db2af6207       274  SIL/date/cyclonedds/loss_20/rep4/transport_p4096_summary.json
0b90efb617806e5def861d0a6081775fbb805cc5dff9f129acac0fc12b9b64b6       262  SIL/date/cyclonedds/loss_20/rep4/transport_p64_summary.json
0c0dcc36ef31db0762bfacfed02cb7c0653003a6fb176707d8c6fadb5d30e52e       276  SIL/date/cyclonedds/loss_20/rep4/transport_p65536_summary.json
9e2face29aafe29f0a9e888f04623f8f950f0549d3d309cd731cf90d78ef9146       273  SIL/date/cyclonedds/loss_20/rep5/transport_p4096_summary.json
01078ddb90f8209061e3ad15a129a9f8a11aac6634149bac7c501f5c394aaa87       265  SIL/date/cyclonedds/loss_20/rep5/transport_p64_summary.json
b98dc2b104a88224d8ce1d4ad2e0f1426c198d466f3fac35786af247207bdd90       275  SIL/date/cyclonedds/loss_20/rep5/transport_p65536_summary.json
7432041f3ebd6e8a7bb399c41ac534fa7296d0993a83815a0de2e4dceab6cd60       271  SIL/date/cyclonedds/loss_20/rep6/transport_p4096_summary.json
dad0dc4eef142db13a562f44a21f1c8bd7cfe43fb776fb1bef19490d2977659b       263  SIL/date/cyclonedds/loss_20/rep6/transport_p64_summary.json
35eb95c3fdd1ebeb2fce0105a873ca95ef039ec0f774d807fb4aec38a29dd3cd       276  SIL/date/cyclonedds/loss_20/rep6/transport_p65536_summary.json
b8c7035915bc2b9fb99f2fbeffb7247d21b98e1a144f4a37cc7a94a0cefbaeeb       274  SIL/date/cyclonedds/loss_20/rep7/transport_p4096_summary.json
9f44ca89e587293af7834bb0f2fbd3dab01aaeebd5f9b9b838f6d8c9d9c30b72       262  SIL/date/cyclonedds/loss_20/rep7/transport_p64_summary.json
556f9be6a64dbc6184e109a96d1ac2ce9398f61af55d51940de908ade08b0660       274  SIL/date/cyclonedds/loss_20/rep7/transport_p65536_summary.json
78569eda73d3ab5b98e00cc3541d6bb1cefe758d977d429ee89fe9abc3f2c273       274  SIL/date/cyclonedds/loss_20/rep8/transport_p4096_summary.json
6418cd9f8a795042f7c0c12ea2af7608f0f949e8db5619a98fe18a04c8a46056       263  SIL/date/cyclonedds/loss_20/rep8/transport_p64_summary.json
4665a9edf4b19877975de3daca47df26d87f262da305ed328fb9cfb883a083cd       275  SIL/date/cyclonedds/loss_20/rep8/transport_p65536_summary.json
1985a796f5bb137cab84c32b3216805be33f011c00ed6ee6e1dcfa3397665716       275  SIL/date/cyclonedds/loss_20/rep9/transport_p4096_summary.json
51069aff5afa66f80d1c7a6ccdc60a1c1331e0b8dd496d4b334ec9d26f72fdd3       263  SIL/date/cyclonedds/loss_20/rep9/transport_p64_summary.json
a35c14ddabbae7f08c55bb6e26ec757a36c7fcdd6b8f634e4c435b0f6d52d3c1       276  SIL/date/cyclonedds/loss_20/rep9/transport_p65536_summary.json
8ef379b1414e10ba256e58a8a7537c71e61980ea7f674f9dfb2184535fe876a3       272  SIL/date/cyclonedds/loss_25/rep1/transport_p4096_summary.json
175caa4b793aca0de05d2b05f82ad17eedfeacdfd45ea8e7fa3cacd27da5ad05       266  SIL/date/cyclonedds/loss_25/rep1/transport_p64_summary.json
13231974f1c02072ff9aa02b4e7b5515120f54e646e180a239c4810f9272804c       274  SIL/date/cyclonedds/loss_25/rep1/transport_p65536_summary.json
0f83cd7f5755929e554ecd67426d3090a2b48243fbe6d2eac5538bfbe71b549b       275  SIL/date/cyclonedds/loss_25/rep10/transport_p4096_summary.json
03072a7989d4713087fa3b41bc52793e0fd814bd674a66fb29c477c5b234ac3e       267  SIL/date/cyclonedds/loss_25/rep10/transport_p64_summary.json
b62be2b9a17179f99d771a4113e29b9a973fa4ea950028ee08ee174b524c9df0       272  SIL/date/cyclonedds/loss_25/rep10/transport_p65536_summary.json
3b7faa7fa38dfb10c35be53ae2fc5029b2f0089876df07fe3f2e39cbf2237474       274  SIL/date/cyclonedds/loss_25/rep2/transport_p4096_summary.json
ccfe4653782996abad628ec71806a5c7868d7b82cd98242a3a547038f78eef9f       266  SIL/date/cyclonedds/loss_25/rep2/transport_p64_summary.json
5028078827762ba9c5352f87289c416de9f83d83a9fe6fe973acaffc5de40c7a       271  SIL/date/cyclonedds/loss_25/rep2/transport_p65536_summary.json
2d07e7ef750bea3d283120ad165b36e27723bb6e4a7e1fb47d09b13847e2a13b       274  SIL/date/cyclonedds/loss_25/rep3/transport_p4096_summary.json
46602bfcd2b55a95a974b67e3052ad9f7a5ef5471de7ec8279f42dade1bda6c4       263  SIL/date/cyclonedds/loss_25/rep3/transport_p64_summary.json
b58af68a0cb627a6f9134614309325670bce020fd958f09556a1d645e3a54cf5       276  SIL/date/cyclonedds/loss_25/rep3/transport_p65536_summary.json
395889d7049844ea0e5430df73d88999aba74409ba12daebd669f610a6c0d04a       272  SIL/date/cyclonedds/loss_25/rep4/transport_p4096_summary.json
c8012f767e52fc8139691896f28c7092e6e319d770fde9033f6d71877d84ecf7       266  SIL/date/cyclonedds/loss_25/rep4/transport_p64_summary.json
25bc5dde65d08ddbaf68092ff30045eff6e333638bc1425d81e2dc043a37edb9       272  SIL/date/cyclonedds/loss_25/rep4/transport_p65536_summary.json
9e53c8544e6f45406a551384ab35847febb72db9d339181c7a21bf56b9c30536       273  SIL/date/cyclonedds/loss_25/rep5/transport_p4096_summary.json
33239124b6d047941c040eb7208da56e6cfc6f79320a06a17a338f279405a9bc       263  SIL/date/cyclonedds/loss_25/rep5/transport_p64_summary.json
dae80f9071a33663e79a26a18489596452c94cdc97f7d26972b4a0d7373e8dcb       273  SIL/date/cyclonedds/loss_25/rep5/transport_p65536_summary.json
13c3d738042f9934ac8760cf9ee6a7112a09bfe870126a5a294af827b5ec1457       273  SIL/date/cyclonedds/loss_25/rep6/transport_p4096_summary.json
6c44db2aeda34ba2ec556b1ed30cbf31fc99017924316f9dcc17616d68f099a9       267  SIL/date/cyclonedds/loss_25/rep6/transport_p64_summary.json
cb7c4cfb91472dcb087c172f90d0ac00a154b34ed7c41ee555230670668cbd2e       274  SIL/date/cyclonedds/loss_25/rep6/transport_p65536_summary.json
7f00c23e35513c35b4c526fa3ddb5407b323bb04a21ba86b0f523105d8399942       275  SIL/date/cyclonedds/loss_25/rep7/transport_p4096_summary.json
0679c8a1db4a6dcb739fb019d8e2a0f1bcda989586396c11c6f58560b6d98b00       263  SIL/date/cyclonedds/loss_25/rep7/transport_p64_summary.json
1c0394bf5cb86c520b870d3980863a34bd5f8d5453eff1cfa029a3afc67c7021       275  SIL/date/cyclonedds/loss_25/rep7/transport_p65536_summary.json
a13e8d3858e800f90dbb6c25cfa96c80ae9c1be65e8386397f976236d2d8b399       275  SIL/date/cyclonedds/loss_25/rep8/transport_p4096_summary.json
1f8ef6cb63e4a3dc471e9d431836603fb275172e59a3d6ddd5bd550b30e5a3ba       267  SIL/date/cyclonedds/loss_25/rep8/transport_p64_summary.json
6cf4e241fe591772f29ec559f080a261cc831257ad326eb07cb369ade9efd92f       275  SIL/date/cyclonedds/loss_25/rep8/transport_p65536_summary.json
aa271f8c2b56d1c318247cd2506cee9fa997ed924af89cad10b6aeec3e6f02e5       275  SIL/date/cyclonedds/loss_25/rep9/transport_p4096_summary.json
1491b070f1e22a65662d676187097041f72d7394e0c3756e8c4950bd9f2ce120       266  SIL/date/cyclonedds/loss_25/rep9/transport_p64_summary.json
3d5f719b0688b157f9e74f58cd04473f10f11daed7901b91e5c73ac57cae6dc2       274  SIL/date/cyclonedds/loss_25/rep9/transport_p65536_summary.json
8be125c095dab4001101acc5e3ebdc9453301a82e50d8205232e2a385c255742       275  SIL/date/cyclonedds/loss_30/rep1/transport_p4096_summary.json
5298a6c4d882fd36371e873112dcbaf96fa3e960460fe0a0fa72e5c12fa28706       266  SIL/date/cyclonedds/loss_30/rep1/transport_p64_summary.json
1a494108312b65554d529219f1c6404760de3339577697f7dd2be44826bc34cc       275  SIL/date/cyclonedds/loss_30/rep1/transport_p65536_summary.json
bdb1aa0315f14c0976fe90a21c8728c4e01a6f1db3fa066ecabe3d9f1927d56d       274  SIL/date/cyclonedds/loss_30/rep10/transport_p4096_summary.json
da6c737f532ae2df39dfbcaf912e1bde7636ce30ae593af4ccb5d976353a5c71       267  SIL/date/cyclonedds/loss_30/rep10/transport_p64_summary.json
677a6ddb92ff68160342d68ebe8a28cc7399ab5755b42ddb04485eadc92f4494       270  SIL/date/cyclonedds/loss_30/rep10/transport_p65536_summary.json
84d8181c62f79dab7281cc9839070ceee811ccff26db070610b4da23b8e59ea6       269  SIL/date/cyclonedds/loss_30/rep2/transport_p4096_summary.json
42e153f778c8a32057abea1391917b1886ea467df401f1c219196415b3d7fda5       266  SIL/date/cyclonedds/loss_30/rep2/transport_p64_summary.json
4b404dcd7cc51a40f42b8d8fa50a6545fcfb85790a3e0d2c2b640cdfe9a190cd       273  SIL/date/cyclonedds/loss_30/rep2/transport_p65536_summary.json
7c06eb00c095ea1bb14c0c2573cb6773e3f9fe681f3af40b14e7a19b1ca98f70       276  SIL/date/cyclonedds/loss_30/rep3/transport_p4096_summary.json
1691d8d37eeb0962e418440433f080734d3bb63d2cf8f6c8463f0ceeab24966a       267  SIL/date/cyclonedds/loss_30/rep3/transport_p64_summary.json
da054ec2b1698a311919d81403cd612639f2da7230640aabc87158054207f79c       275  SIL/date/cyclonedds/loss_30/rep3/transport_p65536_summary.json
97ce44b3174f4bc169b0b7a4cca62078234b6559096221417c99378314ce8063       275  SIL/date/cyclonedds/loss_30/rep4/transport_p4096_summary.json
88081350e86b627f2e2c5386364248c05dd6259224c01776647f04a6b8439305       267  SIL/date/cyclonedds/loss_30/rep4/transport_p64_summary.json
16dedcc0fd1a1b485534989ba27b3044246f90e32dd5885b684a2d51c493743a       275  SIL/date/cyclonedds/loss_30/rep4/transport_p65536_summary.json
28debd17555ca80f5302452c311042538ade72168d14cf4e170574116e6dfa7b       273  SIL/date/cyclonedds/loss_30/rep5/transport_p4096_summary.json
ad82f8b5da27b7484f1299906f150ab428d76b27be700a282db316bddddade2c       264  SIL/date/cyclonedds/loss_30/rep5/transport_p64_summary.json
8390fc5cf4f74d647c5281cd1229f3d41c0afd77bf09ad9c346f2ab2712377be       274  SIL/date/cyclonedds/loss_30/rep5/transport_p65536_summary.json
afe0183d6191331d53c28e43115d831f5c0a25e5c2d18d20f780d3045f9c2aee       273  SIL/date/cyclonedds/loss_30/rep6/transport_p4096_summary.json
d43622a05342cfdaca57dbe755ca7e77642df002d497b698365b721149e8d68c       269  SIL/date/cyclonedds/loss_30/rep6/transport_p64_summary.json
58a32bb34068bb1322fc14f3a46f167e2ca8334d8f364b5c645e7ca0004f8ec4       274  SIL/date/cyclonedds/loss_30/rep6/transport_p65536_summary.json
408fe62713c6ada3c2c7a7dbd61229fc81c87ccbd0446d0843ea53e013de34c4       274  SIL/date/cyclonedds/loss_30/rep7/transport_p4096_summary.json
a11ae23ca8568f9b2dd49de8841ba4b635e8488cbaffdedae0ec2b98af832b30       264  SIL/date/cyclonedds/loss_30/rep7/transport_p64_summary.json
bda246fdcc4e947c1d2e3d9ba87f6d4fee45dc06bbefb2b37d0374cb5ad79ea2       275  SIL/date/cyclonedds/loss_30/rep7/transport_p65536_summary.json
3c264c4c68e496b86014a7f91f38504285346d10ab8312e92ae26fdc91f62fb0       273  SIL/date/cyclonedds/loss_30/rep8/transport_p4096_summary.json
645075efb93ce993aa7073ecfb7eb2855a2666942f05802b2f936256d44b2486       269  SIL/date/cyclonedds/loss_30/rep8/transport_p64_summary.json
c6ae74af3e600d1c9dc5a5e4c835c21d6cd832ed8d921752c26e8ba2d4c9cf85       275  SIL/date/cyclonedds/loss_30/rep8/transport_p65536_summary.json
a2281be65281dde104ec88540272af4156e24b699df2d5be499a4f49fb187db8       274  SIL/date/cyclonedds/loss_30/rep9/transport_p4096_summary.json
8c4f53a8d065ff0086a35abc0a20f9e31d472901ec35b4c3a4abc64c3d71b977       268  SIL/date/cyclonedds/loss_30/rep9/transport_p64_summary.json
e6853821b6d6851b40b1169606f2ce1d737b1adad7cecbad71cda85abd323d72       274  SIL/date/cyclonedds/loss_30/rep9/transport_p65536_summary.json
571b9855ae58d046504862a05ac761ebfbbbabd58c2eddae91759600b2da1ee4       262  SIL/date/cyclonedds/loss_5/rep1/transport_p4096_summary.json
19d20be687a950e45f1ed0e3a007dfcb01fe98e99c9d265c17dfecee94e3109a       259  SIL/date/cyclonedds/loss_5/rep1/transport_p64_summary.json
173385cfcdc33fb05e62b26d61a260b36bec5af5339ceda37b71024d29343492       264  SIL/date/cyclonedds/loss_5/rep1/transport_p65536_summary.json
9e39e80213808af38dfedecb3cffcab24f176ddd9a8dba443bc58ba5a9dac740       261  SIL/date/cyclonedds/loss_5/rep10/transport_p4096_summary.json
9ce171d3ccdec69131e46b4a42152ec5ea6745c3a0cf85e3b566d83048025aad       258  SIL/date/cyclonedds/loss_5/rep10/transport_p64_summary.json
1052fd09bcff6d335d810caac53209d05f8c0f64e66d9c8a41abbb02ef677a1e       262  SIL/date/cyclonedds/loss_5/rep10/transport_p65536_summary.json
fe4ca68a3686ba276645f35fecd1deb2b51b45f310564f426eb04f12553c6dd8       261  SIL/date/cyclonedds/loss_5/rep2/transport_p4096_summary.json
238d60f0cadb59353cbef455b1e1a1ac804933ea354ad3ca5b38e392ea643f28       258  SIL/date/cyclonedds/loss_5/rep2/transport_p64_summary.json
3f1b511c545102d777514442e3243f9538839a45f8d73f6213863717c1531617       263  SIL/date/cyclonedds/loss_5/rep2/transport_p65536_summary.json
635b1b54309678e500f9f310d76ee08c2ebb4a4903db9f2d8a5cb5101502b621       262  SIL/date/cyclonedds/loss_5/rep3/transport_p4096_summary.json
a2f6c0161ef91c2341735c5d04c7bd9e69103d7a2deb91d489f871449adca74a       258  SIL/date/cyclonedds/loss_5/rep3/transport_p64_summary.json
7e1d74b6a0c338e451f262352b15f62018a30aa57565a1a1c9801708354995e4       262  SIL/date/cyclonedds/loss_5/rep3/transport_p65536_summary.json
42545f8936b107f4c41dddc72fb98e1284effa3c94db2b3fa8d9eafa4ff51596       261  SIL/date/cyclonedds/loss_5/rep4/transport_p4096_summary.json
4b5346306fd8826e954d6dcf61b641aab85823ad0794021f089f619ae85d4be5       258  SIL/date/cyclonedds/loss_5/rep4/transport_p64_summary.json
b672fee8c9510d157601b2518e9d0a15aecb0ca6f0ccb7b78507ac9af6fe51db       262  SIL/date/cyclonedds/loss_5/rep4/transport_p65536_summary.json
ad16da36a64dc0aabd00b61400bcf76ddceb41fc11df1663c621909c9455d827       260  SIL/date/cyclonedds/loss_5/rep5/transport_p4096_summary.json
65c83710adb08455c604e6adb21eb64f8550da16bca8d7b30a7a50dc0c5ccf39       258  SIL/date/cyclonedds/loss_5/rep5/transport_p64_summary.json
23d522e1c58a4fb31e860286e228d130538ca9128dfdca5c66e0584d5124a29b       263  SIL/date/cyclonedds/loss_5/rep5/transport_p65536_summary.json
1e4f25ddbf67d93723e32743d8b09b28ed26e6c43ae1cce5ee66d2e27a623670       262  SIL/date/cyclonedds/loss_5/rep6/transport_p4096_summary.json
17a1002ac565a917cbbc3874f9be1d38adc75ac59523c86cdac2e60e9a273686       258  SIL/date/cyclonedds/loss_5/rep6/transport_p64_summary.json
d476381887d2f005af0d668f622af70a72a2a0fb30202031d9e2874bd704d5c3       264  SIL/date/cyclonedds/loss_5/rep6/transport_p65536_summary.json
602eb3d2484a03f7f2c9dc91aa80da799146674d6955667cbcaa1d34bd4c6769       260  SIL/date/cyclonedds/loss_5/rep7/transport_p4096_summary.json
f770aa1fa391dfd2f20af10947d58971c068aca8e707c9f747ad30095fd46f2c       257  SIL/date/cyclonedds/loss_5/rep7/transport_p64_summary.json
45c7b1f7e2a2a25454df7dfb0484201f0aaa3541a0fb9780de63bb075751c59d       262  SIL/date/cyclonedds/loss_5/rep7/transport_p65536_summary.json
c17ca038722ca3c05b9c0a8f688fb31965aa449e5c7d5f4dded61ceeca564655       260  SIL/date/cyclonedds/loss_5/rep8/transport_p4096_summary.json
efca56581a308c9846b5c5c04bd3b38ccd85c751b840e234ea488d039c89ba1f       260  SIL/date/cyclonedds/loss_5/rep8/transport_p64_summary.json
58589d23b68eed41d2723bcbf1b492cf8aa74781c5f0e24f213a81f458fa0754       263  SIL/date/cyclonedds/loss_5/rep8/transport_p65536_summary.json
7fb9dd9a93e84601268ba322afc2980f22b2989846faec76034ee816f3119e49       262  SIL/date/cyclonedds/loss_5/rep9/transport_p4096_summary.json
0eb202d25ba0cbfd335303d9efba397051b66c99b04cda936e829422cb6695d7       258  SIL/date/cyclonedds/loss_5/rep9/transport_p64_summary.json
30355520bbc41d6a19e831ce5e7bf27d5f42dbec5cb0a07d9486108a9d9df339       262  SIL/date/cyclonedds/loss_5/rep9/transport_p65536_summary.json
5a329055cb1ffb6760b35bbfb16c53d8f11ffca1190df500d787d2a5821574a3       249  SIL/date/zenoh/ideal/rep1/transport_p4096_summary.json
c79fa90f7230d530ecfce82355a33d58e8f0021d22d50ff70478107719c6f663       248  SIL/date/zenoh/ideal/rep1/transport_p64_summary.json
ab54cbf3e54da32d41a3cd03ea24ccfed8bd97dd98831b5f5f0705649d3b0522       248  SIL/date/zenoh/ideal/rep1/transport_p65536_summary.json
c137b2c56e48e4c1c6b304b75212f249909a9c58d8235b0a3fe1a723fe3199fd       249  SIL/date/zenoh/ideal/rep10/transport_p4096_summary.json
ef441d4ed9d43e5469ad9b6fe00ae8811332d4513f2bf72656c8f71fac098ce8       248  SIL/date/zenoh/ideal/rep10/transport_p64_summary.json
1725e525e9b3686816579b88aa6a6b4d17b5961c1721220e01b510f71c9ffc33       251  SIL/date/zenoh/ideal/rep10/transport_p65536_summary.json
60ef11df4f412f61c52940611dae7d51583c2f7d494eb07d99525a66193b1b58       250  SIL/date/zenoh/ideal/rep2/transport_p4096_summary.json
9fe1495351f8304f1e273ddb1de28e3fbf09034d59ab1df8ad8f96a29317361e       247  SIL/date/zenoh/ideal/rep2/transport_p64_summary.json
269eb4a90dc3c8b591987be622c0f2b13b55db7523f51c330c772b07ca3382c9       250  SIL/date/zenoh/ideal/rep2/transport_p65536_summary.json
cdbbf572fbfc3255019b61a391c31c9dfc178cff9fdb4928e57c3263e22476a3       250  SIL/date/zenoh/ideal/rep3/transport_p4096_summary.json
7417ab8771ab8200fa1580313be18b7479dccb132bc957a4a2e7f50f1defa492       246  SIL/date/zenoh/ideal/rep3/transport_p64_summary.json
5de1c92abb7a35516654e448c924f60ac7be8dba15f135b719cc360ad5729d3a       251  SIL/date/zenoh/ideal/rep3/transport_p65536_summary.json
58f0116f164d064e541c7fae6d4fba9b28f0c4e145dda6a8f5c8aba13cace5fc       250  SIL/date/zenoh/ideal/rep4/transport_p4096_summary.json
3771c858e263ec0f734b9bf4d1821547dd396567c15be4c94b91c746eac63a88       245  SIL/date/zenoh/ideal/rep4/transport_p64_summary.json
0ef073749a0ab6047dc1d001b1de67f72fc2fe7313770f850c2fb78ec57b6b2c       251  SIL/date/zenoh/ideal/rep4/transport_p65536_summary.json
69358839e055a2ca6151a8af478b8f32b0ad6a769fffbb596b82949e06adfb3f       250  SIL/date/zenoh/ideal/rep5/transport_p4096_summary.json
ac267fd8faf5eafa9ec52710ef8eabdc2c2ab2630b2854bf12a74f3d0564c1e0       248  SIL/date/zenoh/ideal/rep5/transport_p64_summary.json
436950f599816ee33079668377e7a05883c5ecd21dcfb5fc64ecf20656f86ce9       249  SIL/date/zenoh/ideal/rep5/transport_p65536_summary.json
46449d587fb58b680235431f1b118974cc283677c8715ffacbfef44de4b4df02       248  SIL/date/zenoh/ideal/rep6/transport_p4096_summary.json
e36b4e0b60d6840bf00bc9e5a0094eb92dc277191a57198f96e9e36f5bfc9ec7       248  SIL/date/zenoh/ideal/rep6/transport_p64_summary.json
9217a33016c80f8b4cbf5c00189ecb80c45cb449236fdd1d93c2661c165cd11d       250  SIL/date/zenoh/ideal/rep6/transport_p65536_summary.json
29cc2e4ff6bd374f97dbda2968ed08f76525671880f81b593643aa7fd2e7450c       248  SIL/date/zenoh/ideal/rep7/transport_p4096_summary.json
c5be33cfebae1f83b539c5dda3e37b4f83f0eb4b09c1bf000e06a9d014aa9c33       247  SIL/date/zenoh/ideal/rep7/transport_p64_summary.json
9ce1efee353ac0c1d3cd8e633e2d8ef46410ae19c73278f5ae7501e7c0098962       251  SIL/date/zenoh/ideal/rep7/transport_p65536_summary.json
de90b8d79d3e05f9d5e31dc22cd9eea3fb6a630b2429bbc972fa8f18b409cfe1       250  SIL/date/zenoh/ideal/rep8/transport_p4096_summary.json
faed88e3ff1ce4a345bd807daf16d92ceedadd3cda89997c46a2f8e6389c69e0       248  SIL/date/zenoh/ideal/rep8/transport_p64_summary.json
49c733631b0b150695f8b8383f8fb8a3ca87e08a2932ae6329f2283352710c2c       251  SIL/date/zenoh/ideal/rep8/transport_p65536_summary.json
f49e80f14d2a667ddf2de69cf2b18c63c486be1edefea184be42375b28a41318       250  SIL/date/zenoh/ideal/rep9/transport_p4096_summary.json
0dcc77618b62abeae144a44d74a2a031485c3bbe9cf0349b6ee76e0759cb0981       246  SIL/date/zenoh/ideal/rep9/transport_p64_summary.json
b78539475e3af3a592cbaee53756f3006be9849c60c1c9c402ffb7e530f0f281       250  SIL/date/zenoh/ideal/rep9/transport_p65536_summary.json
2a84ca16b4183efeb919b4d0a77ef0296a8bf2c23585e24472c505fe46ae80fc       263  SIL/date/zenoh/lat200_jit50/rep1/transport_p4096_summary.json
9bb8f1050efd735845b1b54bcfcd9ebdaba3c638430ed3e0dc3ce936008d3e6d       262  SIL/date/zenoh/lat200_jit50/rep1/transport_p64_summary.json
708aedf292c4d006fed1ba9c72b20447f1d37afa6de0b29e98ad5ad621bff11e       268  SIL/date/zenoh/lat200_jit50/rep1/transport_p65536_summary.json
f152eb0b6c87fc720f3be34bb764fefd49789745c82cdcecef5b7e0b98de2879       262  SIL/date/zenoh/lat200_jit50/rep10/transport_p4096_summary.json
e7478c1f90bdf3f9559cd8478f4099e37db5d6ac4468f5b2daef7017f9cd2db4       261  SIL/date/zenoh/lat200_jit50/rep10/transport_p64_summary.json
f79d8799bd8d95637485486cea90273a4d0b83ae416307ad5a3529ac3f71e709       269  SIL/date/zenoh/lat200_jit50/rep10/transport_p65536_summary.json
22b8308c30d8bb4fb30871435d15539b1409f613fcad0f4c7981088cfc47a7dc       263  SIL/date/zenoh/lat200_jit50/rep2/transport_p4096_summary.json
87a1b2f5b4e6bfbbf00db52e0424d1cda2012ea43869ceb8fa5519d45fe7fb08       262  SIL/date/zenoh/lat200_jit50/rep2/transport_p64_summary.json
c1995d9277abb7cc5ef6a9a55b4f6d8ad77a23fde25ddee247c1372869baed02       268  SIL/date/zenoh/lat200_jit50/rep2/transport_p65536_summary.json
98258f061e0531f85b00a4129d7d4446565c7c04d31cdf09b0ef0fb728a642c1       265  SIL/date/zenoh/lat200_jit50/rep3/transport_p4096_summary.json
b4ebe0d71fa5b5d9a06e817a45b916694941d42a2383febfcd08b76892bc945a       262  SIL/date/zenoh/lat200_jit50/rep3/transport_p64_summary.json
8a2d09cd2d1d3f9ffbf629b4fff4685e95c37aa4407f1d4e7d3263e5ab9f17db       268  SIL/date/zenoh/lat200_jit50/rep3/transport_p65536_summary.json
8c4f679b1c2e0fd0d0f518cb268134d47092bfea7554dd58fd5f687cf5692a99       265  SIL/date/zenoh/lat200_jit50/rep4/transport_p4096_summary.json
b049f0d2052f2511172248a673bb04c116e1f335f5e43ee5ffef2cb5f1b3f58f       261  SIL/date/zenoh/lat200_jit50/rep4/transport_p64_summary.json
a9aeb4ed0c99f46a3968f97a0f4c11093314d6e2b32126b06fa799455b120bde       268  SIL/date/zenoh/lat200_jit50/rep4/transport_p65536_summary.json
50a942e1fce0d5038e69467d75a20558879dd929d947944161854f56b9f1b14e       265  SIL/date/zenoh/lat200_jit50/rep5/transport_p4096_summary.json
fbecf25d25abbad6c15a0892bb8d1c946536f04038e9671cb8ba9f2fd84517ea       261  SIL/date/zenoh/lat200_jit50/rep5/transport_p64_summary.json
4c43a4fed667c0bd8239d69f48449fcdd403b623d2fa120505ea490e72ed190f       269  SIL/date/zenoh/lat200_jit50/rep5/transport_p65536_summary.json
195cff4602c8f1b9434ee4994412bc09cfd79bfa4a2febd8dc40193a1ddbf7cc       264  SIL/date/zenoh/lat200_jit50/rep6/transport_p4096_summary.json
16fca57e49e1b7940c54bf52e066569427b57f41c20a50a975b51488b5959b5b       263  SIL/date/zenoh/lat200_jit50/rep6/transport_p64_summary.json
4c00e66fff25977eb904a449d3f2a1f140e0a7755efaa10bd81c2b9bc0eed1fc       269  SIL/date/zenoh/lat200_jit50/rep6/transport_p65536_summary.json
b83cf8bde95c355bf0b0b89cffa15368e7e4ce2fbe99c806b34813e5efb75421       265  SIL/date/zenoh/lat200_jit50/rep7/transport_p4096_summary.json
fcea53c1c8a1082257db8d87dbab2c031de43555541920d3c8e9a239e18e9436       263  SIL/date/zenoh/lat200_jit50/rep7/transport_p64_summary.json
629c812e11e294431b3964cb0fa0a7b4616dd7d0f4a9bb123ffabecd4bdf13cc       268  SIL/date/zenoh/lat200_jit50/rep7/transport_p65536_summary.json
7eb1d5d01b2de9e166faee745b5d3a546c5eee8cfcdd10f02a4fa96226bfa860       264  SIL/date/zenoh/lat200_jit50/rep8/transport_p4096_summary.json
79cd887de6534e92f3751a448e35a672f9baf71b63c5563777fe0d45f5d0efb6       263  SIL/date/zenoh/lat200_jit50/rep8/transport_p64_summary.json
aedee05fcaf3b334fb9d33a5119a7b76827bffde562246dc345f2ec6dd7d724b       268  SIL/date/zenoh/lat200_jit50/rep8/transport_p65536_summary.json
5d0c99c3c6d9c7095e72fb50e264314f8714b488392220c0cfe244870c75e01d       263  SIL/date/zenoh/lat200_jit50/rep9/transport_p4096_summary.json
2f4775ec437a095f613d20a8caea940c3745aac8be7e6781a721889b598b5564       263  SIL/date/zenoh/lat200_jit50/rep9/transport_p64_summary.json
25511b009326f1e3163b1f3d13279059ec49d4ed04bac0f9c54b313c8bbb8520       272  SIL/date/zenoh/lat200_jit50/rep9/transport_p65536_summary.json
ac72ce6878b16670252e1154f70ec0545598f1323dcf11e87568935b967709ae       269  SIL/date/zenoh/lat200_l15/rep1/transport_p4096_summary.json
d9dd5631d19ef7913d1e559c9108d27755e8463b44d24c429390415e59579b65       267  SIL/date/zenoh/lat200_l15/rep1/transport_p64_summary.json
31387449eaa813ec97d449f629000b4068d1184f0d745139a8327ed2d9debd0b       272  SIL/date/zenoh/lat200_l15/rep1/transport_p65536_summary.json
f7c4c76a917841ac3c709ec359d428124047d388c3ff070c944dc3445a31c73a       270  SIL/date/zenoh/lat200_l15/rep10/transport_p4096_summary.json
574a8a7a66cccec20b06b45192d4b9388479bd56fccedc5376dced1f451a8058       266  SIL/date/zenoh/lat200_l15/rep10/transport_p64_summary.json
9f052e63d66296c16a381a3ee4eedf3a37de983ad89b075796467424686b9eca       275  SIL/date/zenoh/lat200_l15/rep10/transport_p65536_summary.json
2acaab3b7291290468a8dfb52f4efee4d815bce375467d427aaba59a182c43ab       270  SIL/date/zenoh/lat200_l15/rep2/transport_p4096_summary.json
c1a0607580a32a9053b46809bf5a6f66d7a80223b9fde2c9731958a7f562d38a       268  SIL/date/zenoh/lat200_l15/rep2/transport_p64_summary.json
3ee2b25ec4d6dba737a21ce4cc9dd2aa6556a00ea7c341f5fe0dfb29794eb78e       274  SIL/date/zenoh/lat200_l15/rep2/transport_p65536_summary.json
984ff5de5a4408435d89b81152d7a179d8b1b568e94fe16af923e833f86175ec       270  SIL/date/zenoh/lat200_l15/rep3/transport_p4096_summary.json
e1269bce91a575f9eb09fe9a20823c765f05a5c001971bbe3b85be0ed23cfc68       268  SIL/date/zenoh/lat200_l15/rep3/transport_p64_summary.json
eb0410ded34024ae034d730342110baea0bcea68eac44cd96c4e5f01494fa4c7       273  SIL/date/zenoh/lat200_l15/rep3/transport_p65536_summary.json
7f3d97975cd63d1b9eb0cb5013f38a1d6520f780139b7d276b45579972406695       270  SIL/date/zenoh/lat200_l15/rep4/transport_p4096_summary.json
00e4c5ace9e62f9c850e55bff49a359cd340493d8473d9e3111a9e0fa91bc425       268  SIL/date/zenoh/lat200_l15/rep4/transport_p64_summary.json
a6d110416861b7702598b6afb7ed9102f79b3dcdd3af5c54f0599e06696de637       271  SIL/date/zenoh/lat200_l15/rep4/transport_p65536_summary.json
bc9bb13c3bbee313330bef7c3fcf661fb2b2f53b9c92d09b0679ba9d30e28799       267  SIL/date/zenoh/lat200_l15/rep5/transport_p4096_summary.json
8fb3298cae5037c427a482b9858981e08d1240c1fd44bd1e93e6dd532ae713be       268  SIL/date/zenoh/lat200_l15/rep5/transport_p64_summary.json
072c58c1827a0b35c3f74f8f0b2ee1d9927fcaf3020f977d863073b68acece0f       272  SIL/date/zenoh/lat200_l15/rep5/transport_p65536_summary.json
31e79062df341ab7ec9a2ed7509a846d6ec2f7f9befc2554ac9e1fef7094522c       269  SIL/date/zenoh/lat200_l15/rep6/transport_p4096_summary.json
d6a712a3f27826e92282706b5717900053c02c2f66a0a99ace491609e7e81dbb       266  SIL/date/zenoh/lat200_l15/rep6/transport_p64_summary.json
682dda65ab8075b64cb4a08a2f07fb8f07f2ce001101c20ba63bc1047dd3cfc9       275  SIL/date/zenoh/lat200_l15/rep6/transport_p65536_summary.json
8e5b5d672c25925cb71a91163d34953e3abeab21c45b68ba36715f2711fffb1d       270  SIL/date/zenoh/lat200_l15/rep7/transport_p4096_summary.json
8ecc6456ce34bf832ab6c5a181f03f6a99a2e5253d6b0d5e8c51b670eca04f50       267  SIL/date/zenoh/lat200_l15/rep7/transport_p64_summary.json
55f9162d512f839657327b9ebe896f93cc29eaa16b33d3439c81b38ee5360972       275  SIL/date/zenoh/lat200_l15/rep7/transport_p65536_summary.json
0ab7890233ae5d8627298fd047c60c750cfd966cca2843571d4feb2799c3a7f5       268  SIL/date/zenoh/lat200_l15/rep8/transport_p4096_summary.json
7af12415b720d8bd2663ec07f1fdfc2c0e779177ce0d9924750e04f599929e4a       266  SIL/date/zenoh/lat200_l15/rep8/transport_p64_summary.json
582a1a5c20ba790c4c8ce634729d3836fea96a770267b58b0996a8d5961b4fd6       275  SIL/date/zenoh/lat200_l15/rep8/transport_p65536_summary.json
00b571ecb67d561d7016f77acc5906acaa6c138b28c5777675cc60ac79e875f5       271  SIL/date/zenoh/lat200_l15/rep9/transport_p4096_summary.json
833247a6b96ec65f0608f7ba73c9c4279d388b32e4697b915d4a05e336f7a11c       268  SIL/date/zenoh/lat200_l15/rep9/transport_p64_summary.json
c0ff926f37dd1db68f724e0e09d0433019bd70980f5714acb93e4e2bd4e82097       273  SIL/date/zenoh/lat200_l15/rep9/transport_p65536_summary.json
a20e5a49444c90bbffccbfe89b6a2a11a92fb8d685389ca058a6552665c73919       259  SIL/date/zenoh/loss_15/rep1/transport_p4096_summary.json
4cbd39ee9e83996df8e5f79840815c68310fd796f2f82f0c6f2a7f13a8d54209       262  SIL/date/zenoh/loss_15/rep1/transport_p64_summary.json
3214785122d3e6b723559649684ea546b1c56a3b0449ac1c021c208885548cd9       266  SIL/date/zenoh/loss_15/rep1/transport_p65536_summary.json
19fcbd7e882f4adf98004a29b7712fdf1579c3fd1ef4e25cafa94e9ee217554e       264  SIL/date/zenoh/loss_15/rep10/transport_p4096_summary.json
67973baf531db91823df05655f6603c227007fe1408d09d6ad7bd48bd3cbd480       261  SIL/date/zenoh/loss_15/rep10/transport_p64_summary.json
b88246b2751e84f3851dfca64afaed63f9f068876bd03a4c17f2e886a2f9f298       267  SIL/date/zenoh/loss_15/rep10/transport_p65536_summary.json
7e40c7390a3102f71615a1531963b40b381f2a84dcf1e1ab3a6fcf89772f228e       262  SIL/date/zenoh/loss_15/rep2/transport_p4096_summary.json
2ee2d6784222022071f15d7b2e6454f7483f747f900ad11215fa9ed098d48e73       257  SIL/date/zenoh/loss_15/rep2/transport_p64_summary.json
bcf0820aa00185243385c5509f46b2cc776e1e120b829010b0c907058697aae5       267  SIL/date/zenoh/loss_15/rep2/transport_p65536_summary.json
295cb6c46811ff2aeb08c9a6266514206cb3b130686f85d37324591af6e18ffc       262  SIL/date/zenoh/loss_15/rep3/transport_p4096_summary.json
2c0060e6a7e1a681a5cb665bc2c6b3c740ac8fbd207405ce66a6054af79d6c27       259  SIL/date/zenoh/loss_15/rep3/transport_p64_summary.json
02eb74b8c665caa890d9807f98afeaf47ff88f48ad7dc1782ee693e2a2d70bc4       263  SIL/date/zenoh/loss_15/rep3/transport_p65536_summary.json
4995071d39aa35a198838f1d75bc06b393fcb61110f7111c8b0699115841955a       264  SIL/date/zenoh/loss_15/rep4/transport_p4096_summary.json
c2f1a2723e344d4cc41579dd296c747cd407b31da7e8b5146607a9b65f582e19       257  SIL/date/zenoh/loss_15/rep4/transport_p64_summary.json
aaca80901b3c26635a8139b949f5374ec767dcf124ea0c88616ae5645b24ca53       268  SIL/date/zenoh/loss_15/rep4/transport_p65536_summary.json
274ae3cdc3bd03b11934e79e47141e299988971948da737e017ef817cdef68d9       261  SIL/date/zenoh/loss_15/rep5/transport_p4096_summary.json
d7732cbd247ae27ec77ddf3bcdbab2a24b38ea8dc37a215d31a374984a97805a       256  SIL/date/zenoh/loss_15/rep5/transport_p64_summary.json
6099d78dbb213a7dd7f623eac77d8011dda089e7e70c94e13cff10b00cea02e6       267  SIL/date/zenoh/loss_15/rep5/transport_p65536_summary.json
a29f948fcdc9c4cb36e37e8c19a674f0bc5816b7670d3b1a83c126da445e6a72       260  SIL/date/zenoh/loss_15/rep6/transport_p4096_summary.json
8b2c9e2adf8b34b3a49a91c6486313c878e96da1a4b182b7eee812b33554ea67       258  SIL/date/zenoh/loss_15/rep6/transport_p64_summary.json
e8b5a9349d2cc4c8f8bfe1890a0f027335fa069bee1f3ef4bb0a69d49266ca38       260  SIL/date/zenoh/loss_15/rep6/transport_p65536_summary.json
d3b2d8a4caa5572a1c6c5863dd3645e5d8dd33b6b70882715e378aa5c3cc615b       257  SIL/date/zenoh/loss_15/rep7/transport_p4096_summary.json
c4d393e73f7fc494415e0f1b1de02637837cb0d50c7529338f38048c4c141353       258  SIL/date/zenoh/loss_15/rep7/transport_p64_summary.json
873b3ae9e56ad2689f5c39ece5c09ca30a50a50135898a55fa8b13983e57d1a2       265  SIL/date/zenoh/loss_15/rep7/transport_p65536_summary.json
e8c85b0d0545cf34df45fd1e0658f2f0876e9f9b53df8ec42cecd32068ad1d16       263  SIL/date/zenoh/loss_15/rep8/transport_p4096_summary.json
c8b88457f4e1e8d44a4a527b873325070d1a7bc0c13bd6bfababb106b6bb7782       261  SIL/date/zenoh/loss_15/rep8/transport_p64_summary.json
d5a2e7a0c30509060e135412f6cfff847eab3f0f1335cb2bc02a9a9e4a7c44f0       266  SIL/date/zenoh/loss_15/rep8/transport_p65536_summary.json
603703e828570bfd11dacd50d142703788b51b553a57de8d6caf1ebcc67ca193       263  SIL/date/zenoh/loss_15/rep9/transport_p4096_summary.json
31063da207cb57b417a1ce467f61c70ff492edd8088855bf20459e82c814e5d5       259  SIL/date/zenoh/loss_15/rep9/transport_p64_summary.json
909742c5b61c5bc9ba7930cb33458ab6c2d7034b8eff55312c2d64d4bf591528       267  SIL/date/zenoh/loss_15/rep9/transport_p65536_summary.json
651be7d61d271ab413368de9566fd02b1fded2787d9741652cc4a7cfd5456b85       264  SIL/date/zenoh/loss_20/rep1/transport_p4096_summary.json
494206f35302fbcae695f5bc8ec54e2fd35538e359af3d845e5ff2c145edd8b9       264  SIL/date/zenoh/loss_20/rep1/transport_p64_summary.json
ffc1096fe7747e58938e71958f108fca6d094208101534f0d150151bf5e16a13       269  SIL/date/zenoh/loss_20/rep1/transport_p65536_summary.json
7c48c6dbac1312d89f8c427a993553db88601597be5631df1039ce4de7a1829c       265  SIL/date/zenoh/loss_20/rep10/transport_p4096_summary.json
ae5f5c88e3b6fe54cebccc0ea49bf87ddce110e548b919ceb9712e6df04edf24       262  SIL/date/zenoh/loss_20/rep10/transport_p64_summary.json
852d15523ee5c712f821e04c5067389b11f8d88a2a4721a75421737b9635c5d3       266  SIL/date/zenoh/loss_20/rep10/transport_p65536_summary.json
b061b5eb3cf9b39b6a073dfec13d07b06123a8f6b47d20464c539e5866498bcc       260  SIL/date/zenoh/loss_20/rep2/transport_p4096_summary.json
8a3b40780bc41050ed7962a7073e9683300ddfbe5e838163cf095b8af5bc58e4       264  SIL/date/zenoh/loss_20/rep2/transport_p64_summary.json
ba65e83f2d166c6e9903e95784c6f8a733b9aa168478628e004357ae7fdcb2e9       269  SIL/date/zenoh/loss_20/rep2/transport_p65536_summary.json
144e5ee22e264eddf3eacb772587762429a972abb7a60ee8f3cd1c4aeed90b90       264  SIL/date/zenoh/loss_20/rep3/transport_p4096_summary.json
4b647e540cb75e3fff061147064bbb8d77d996932f501f46f741dd4110d2598f       263  SIL/date/zenoh/loss_20/rep3/transport_p64_summary.json
4779a04397234dd3960f9143f4c586f68b38016560f538ad0aeef6eaa26712e1       268  SIL/date/zenoh/loss_20/rep3/transport_p65536_summary.json
c685c08940aca85ab97e8c75cba0d5ae3e8f4cba630cb1940f21ed3aa555756f       264  SIL/date/zenoh/loss_20/rep4/transport_p4096_summary.json
22055a6161bcd6a23bc5511f279fc09b6743030bdfef36301c11ecd1c76b00de       263  SIL/date/zenoh/loss_20/rep4/transport_p64_summary.json
9ad38f2c8193748e4c7c0846c0ce5bccd8e488c5318b41559941310cb9dc5051       266  SIL/date/zenoh/loss_20/rep4/transport_p65536_summary.json
b1f4ac8fd6422e2439a890154cd0b7eba0d72ce14cd388c447ebb738a75634e7       262  SIL/date/zenoh/loss_20/rep5/transport_p4096_summary.json
5434453edc7c1f4a7575ec7370aa6fd55f335758092c79a4fa77d03ced649e07       263  SIL/date/zenoh/loss_20/rep5/transport_p64_summary.json
13e50bad2309bbaf1196b35e36211227fc978625bbff288e294c29092505a135       269  SIL/date/zenoh/loss_20/rep5/transport_p65536_summary.json
f0a768b36edb958cd259245122b288e5959305c8d7feb2b9b6dd00bd6b36a53f       264  SIL/date/zenoh/loss_20/rep6/transport_p4096_summary.json
aca93a149009df1a0fe0f4fd83bfb88a83237b55b72457893ad2ed4460f01b70       263  SIL/date/zenoh/loss_20/rep6/transport_p64_summary.json
f6ecbb7c07debed4e95b8c5bce4419b4cd3a16b3c5ef1f89f7b8a4aa19262451       269  SIL/date/zenoh/loss_20/rep6/transport_p65536_summary.json
2393933bb87d14188a22a1703c7923a08104c876b1afc2be2dbc261e75cd9ad7       263  SIL/date/zenoh/loss_20/rep7/transport_p4096_summary.json
02838057f1a96d2f4f8aa02830fc5769dcd51b31292113bf1889899fd993897a       263  SIL/date/zenoh/loss_20/rep7/transport_p64_summary.json
a535496be7a124d6e2d48e6f24c5472ee78214ba239f4805668b74ab99ffd4f1       268  SIL/date/zenoh/loss_20/rep7/transport_p65536_summary.json
e3eed158e9ce6dededdcfe3c876bf160e1d441f9e5a8aefaba527b1742c4fd61       266  SIL/date/zenoh/loss_20/rep8/transport_p4096_summary.json
b3ce143a4868555f879fec3fbaec4d3223ff8bb74ecb1818768d42a27f5c9e41       264  SIL/date/zenoh/loss_20/rep8/transport_p64_summary.json
eb0fcf9a3c54cb1127ed846eb70118e478d3600abab75ab5ca8e98c86a0e7a5e       268  SIL/date/zenoh/loss_20/rep8/transport_p65536_summary.json
60dbd3d73c7bc7b7c3ebd042b97b94357a27aa16e36f5a0f6c8dca1ee4ee6a57       266  SIL/date/zenoh/loss_20/rep9/transport_p4096_summary.json
22d4385880e0ce15eaba1ba7746deadb61461d5e746db8462ed19d49a1e663e5       263  SIL/date/zenoh/loss_20/rep9/transport_p64_summary.json
97903e8d6480916a1717b83d46eaf459fd360778477a579bf105324d700bddb6       268  SIL/date/zenoh/loss_20/rep9/transport_p65536_summary.json
55a8d065cb9f607871d0b22ff14ebd966dfacd5041ebd81ad9a431dfc7397799       272  SIL/date/zenoh/loss_25/rep1/transport_p4096_summary.json
4a610f2c91680daa6f64ffb92809f06ba26678b10db95bfeba7a36b051258de1       262  SIL/date/zenoh/loss_25/rep1/transport_p64_summary.json
2d563fc6fa2926360a64b93e0a9a29afcd7d835c1054ac68b0d5f409e903cc0a       271  SIL/date/zenoh/loss_25/rep1/transport_p65536_summary.json
1b9307018d57fab7d71e40a9dd5d01386b6d67a02ef8a103bb01e309afeba977       267  SIL/date/zenoh/loss_25/rep10/transport_p4096_summary.json
e2c9f87140c6a90206e12e9a7bdf388ffc8f5e0459f87a41f2330ca59ee74d81       263  SIL/date/zenoh/loss_25/rep10/transport_p64_summary.json
d0d3275b10da99a6c4e2595f24f2c73c470030879ab8ba1c8500d40b166a02cc       275  SIL/date/zenoh/loss_25/rep10/transport_p65536_summary.json
2ac935b9f6cc2cd688285226aada129b211189e8242a5f3a176641739a774613       266  SIL/date/zenoh/loss_25/rep2/transport_p4096_summary.json
455d83fa8f98946f4ee2c8c385802128705654f4b9c9aaa411eb9bd12805714e       263  SIL/date/zenoh/loss_25/rep2/transport_p64_summary.json
a428213c43f36396acab81d2f185cfd4b8d45bb8a0348edd67e5e7be421b0d1b       268  SIL/date/zenoh/loss_25/rep2/transport_p65536_summary.json
05f004ccf75e18c6ae269d0fb141c890686fde14188809a766622e4dd5141b64       264  SIL/date/zenoh/loss_25/rep3/transport_p4096_summary.json
4d0fe691a633a95e5b5217dba8273284f5995e4c5aa513099d70b225447cb4f4       264  SIL/date/zenoh/loss_25/rep3/transport_p64_summary.json
55f909d8a381f7838e65ed37b7702c8dc5868bfa3bef9bc2b812f9d7874f1840       270  SIL/date/zenoh/loss_25/rep3/transport_p65536_summary.json
bc61b75335e8de00984c9bd156601d06ca820e64ecc0385e7cce710f0769e8bc       262  SIL/date/zenoh/loss_25/rep4/transport_p4096_summary.json
089fb7a02e6d3e83c3612835b1ed8f45b63d647d46d3ce51fe09e6ed0daf2065       261  SIL/date/zenoh/loss_25/rep4/transport_p64_summary.json
ee6630fce00a2ce3cc6ff4ee8f35964a03a89ffb139e4b945c88e655dc405ac5       267  SIL/date/zenoh/loss_25/rep4/transport_p65536_summary.json
baeee2aee1244f125907dee7d5a7e1c686723cc2c8a6a79071ae486e170f2111       270  SIL/date/zenoh/loss_25/rep5/transport_p4096_summary.json
4b9060c6476993a0e0480c52597885e6e4444d475432fff8e785309797fc4fde       263  SIL/date/zenoh/loss_25/rep5/transport_p64_summary.json
1707b1471cfd73295e211613811b61a6562b940aeeafca25e76da54fdb206063       268  SIL/date/zenoh/loss_25/rep5/transport_p65536_summary.json
3a01865fbcc2f4fad8cf41cf677a8b1a5adbee19b0c8a1e7050de4540bb6a44f       265  SIL/date/zenoh/loss_25/rep6/transport_p4096_summary.json
a5676f64b45a19596c4e3300d3b613ca758fd530941a77fdb231a38615bcb9da       262  SIL/date/zenoh/loss_25/rep6/transport_p64_summary.json
329bf116a60b3c79c4d96b26f3c0f63bc0e29fdc53f0d4ae3e4d952aeeabf7c5       275  SIL/date/zenoh/loss_25/rep6/transport_p65536_summary.json
468a73ee0d4e4fd21c4ae1f8838bcc6caa57c211ba7232df16700c10726678bb       266  SIL/date/zenoh/loss_25/rep7/transport_p4096_summary.json
14e05e1fb1848e58a84234655c9053bb123f1ed9c23f85210213b3dd531fc490       264  SIL/date/zenoh/loss_25/rep7/transport_p64_summary.json
243c30ab89c9fae48c60dad1155b47bc11927c58a2a2f899e3394a9880a2cb29       270  SIL/date/zenoh/loss_25/rep7/transport_p65536_summary.json
c61cdf8cb3c842826a1882b7c0e99b0971f98dfddcaf3df498270d088793267c       266  SIL/date/zenoh/loss_25/rep8/transport_p4096_summary.json
a4f46ed143e15415a7762e6c53b11f69d303b31f1e3f154dc511195a6e9e4f4a       263  SIL/date/zenoh/loss_25/rep8/transport_p64_summary.json
abdf96e696a5f13974ac6676f98b1faa2924c49331a739a4b4351670b3df40e7       271  SIL/date/zenoh/loss_25/rep8/transport_p65536_summary.json
ceae6dd54325b1518b376dde9ec814290b81df053d9af6becc70b9be272de3a4       272  SIL/date/zenoh/loss_25/rep9/transport_p4096_summary.json
f337f88c02da9e35f7abcd050cc0708c6ef8ce4d3e798c783cd3422d708959c8       264  SIL/date/zenoh/loss_25/rep9/transport_p64_summary.json
395c8a24269f749e8e610a7c42d920fee17ae644071faba21831717ef4b73396       270  SIL/date/zenoh/loss_25/rep9/transport_p65536_summary.json
2b0eef71f680398d07f0d472b6fa2c1b0931487a0509fb4d6a90f186f2a5e746       271  SIL/date/zenoh/loss_30/rep1/transport_p4096_summary.json
3ba860b3cb589bef4e6186c829d7de90ef2addfea614f594905f20880359df78       251  SIL/date/zenoh/loss_30/rep1/transport_p64_summary.json
728d34f56f081b5bf07fe2e23f21c7905b8c32cff863525c549c1b03c56c9c25       269  SIL/date/zenoh/loss_30/rep1/transport_p65536_summary.json
0921548d0dc1b04ac348cad8061f4261ec1a68db8fcd41952832ec3b7004db28       265  SIL/date/zenoh/loss_30/rep10/transport_p4096_summary.json
542c967f71d4aac9013c6cfebcb3d41d3594edffa8192d61c191c7086c94cb51       261  SIL/date/zenoh/loss_30/rep10/transport_p64_summary.json
97449111e43cff177d06a80381b52b2940bddd04a85a918e0b00b9a6f8203ad8       270  SIL/date/zenoh/loss_30/rep10/transport_p65536_summary.json
a04b161d852487f8494b8612634a6bc82c1830dce37427957a325bc1cf209023       267  SIL/date/zenoh/loss_30/rep2/transport_p4096_summary.json
7744c4871b6e20d728d5e0a1eae86357d1af8b58ec899024c1738554046660af       263  SIL/date/zenoh/loss_30/rep2/transport_p64_summary.json
b1c51cf3573f8cd1bb32763d4de8930be7e3d1be42320960200dfe451ef2e6c2       273  SIL/date/zenoh/loss_30/rep2/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  SIL/date/zenoh/loss_30/rep3/transport_p4096_summary.json
8719fe0b10d45348db1a87c5d5e8b19eb491226e4d547f5081aee1b3c85e187e       264  SIL/date/zenoh/loss_30/rep3/transport_p64_summary.json
f908ee7f039f7200402f0fd8ea95dabcc2e991509adadf2795d8461405d69b16       271  SIL/date/zenoh/loss_30/rep3/transport_p65536_summary.json
e69120b7f576c79e2f2895e6eaeefed05d2b1654f8173ac8afb641e38fb99f82       274  SIL/date/zenoh/loss_30/rep4/transport_p4096_summary.json
f52ba7c014eedb6758d15b485b52558046f8f912d09ef9bbabb201db09d572b0       264  SIL/date/zenoh/loss_30/rep4/transport_p64_summary.json
df793d6deed95c29a9a615606a4c4e2a8a0394846c674aa05c3c9cf3a021deae       269  SIL/date/zenoh/loss_30/rep4/transport_p65536_summary.json
559409db03b5ee4b0271083ce14a9cd5cddfe111604d3d8491ee7b353893d3cf       275  SIL/date/zenoh/loss_30/rep5/transport_p4096_summary.json
33f08ead87e25df83d6144b91e06f407975303c2baa4d35d3362858332167be0       264  SIL/date/zenoh/loss_30/rep5/transport_p64_summary.json
3405de208e60230eafe252f82301fe75ba5f4d58a6901cc74d2cc4ced779421b       270  SIL/date/zenoh/loss_30/rep5/transport_p65536_summary.json
0f8d32b53c42e51df341b22ac77e69def6e7212760977e75168270625cff8bf0       269  SIL/date/zenoh/loss_30/rep6/transport_p4096_summary.json
26ec58b2bec2623c3f3d0325fe54420fe7e92c412dab7d0a1b69a2caa1dc62fa       270  SIL/date/zenoh/loss_30/rep6/transport_p64_summary.json
20be93c9ce38dd09eb04f612bd9d6d979df367329f59702973a6ad52956ca997       272  SIL/date/zenoh/loss_30/rep6/transport_p65536_summary.json
a087782ba196550117e31a6e693523fbb8de6b85e6ac724c44990544cefeb585       267  SIL/date/zenoh/loss_30/rep7/transport_p4096_summary.json
11cd7de18b202b7a1324febb7c6427e23b547cda0fb20ac5b6a865d390672418       263  SIL/date/zenoh/loss_30/rep7/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  SIL/date/zenoh/loss_30/rep7/transport_p65536_summary.json
18471fb18cb6f76b84173aa32cdf08d6826e959c86709668ca5f20f9ab79523e       267  SIL/date/zenoh/loss_30/rep8/transport_p4096_summary.json
a902b2cc05ccdd491dcd2db84b16aa86178108b699803f481d400a15bea20f58       266  SIL/date/zenoh/loss_30/rep8/transport_p64_summary.json
688221f50f43f27806b907559ae847fa9985d13b8b69c560233af10a4edf0dc8       273  SIL/date/zenoh/loss_30/rep8/transport_p65536_summary.json
08c35d196d2c94697626c9787a7c9b9aced1fc7e1bb3d2e8181c1d51fb2aca8e       266  SIL/date/zenoh/loss_30/rep9/transport_p4096_summary.json
2a4a486898c4db83d87181cdec6204fc9ab140c1db6eecc4ce445fb5fc1fe1e9       269  SIL/date/zenoh/loss_30/rep9/transport_p64_summary.json
fa903054d10fb1d1ad3eedd48ef7e124b6a23e88b0838bfd6e67d9c8907a17fd       269  SIL/date/zenoh/loss_30/rep9/transport_p65536_summary.json
f48ad39841e1c6282d2caac91874ed6a80f077464e9bd05963d8e4c069ad5e05       255  SIL/date/zenoh/loss_5/rep1/transport_p4096_summary.json
324f1b674c531c9f61c875afd6679103d5e1196dd203c184c756e2e594e3c760       254  SIL/date/zenoh/loss_5/rep1/transport_p64_summary.json
e870e836d648ae46690d7dfa1785469576d7056afb0597b9b77eff33789e4e40       253  SIL/date/zenoh/loss_5/rep1/transport_p65536_summary.json
3cb758b48345fd53f86baec5ee8cf2ddc4b877208ed73659a9761d29c9a3715e       255  SIL/date/zenoh/loss_5/rep10/transport_p4096_summary.json
f0684c92dac6980f7c796557931e1931201f6dee968775d8a61c3ad4cf3bcc3d       253  SIL/date/zenoh/loss_5/rep10/transport_p64_summary.json
6673b3394ccd69702181553791cea128513168fcddff4f8284ba0315dbae462f       257  SIL/date/zenoh/loss_5/rep10/transport_p65536_summary.json
12ce6fb8fc173cde3317d1485b8dd2cc28ef211fa38a1cfd9afe9691dc7a3491       254  SIL/date/zenoh/loss_5/rep2/transport_p4096_summary.json
6788a0cdd258d52e12e9b857a1a7a515a3d5bf3c9c4f6994b3c25cb143158253       253  SIL/date/zenoh/loss_5/rep2/transport_p64_summary.json
c32866b2a83ac9cb1bc094d22db51025e34f6672992393d34360300338abadea       257  SIL/date/zenoh/loss_5/rep2/transport_p65536_summary.json
5cf288abc98d423267c3ffedc65530b3923eb35ecea1c292c544fa4741197c6f       257  SIL/date/zenoh/loss_5/rep3/transport_p4096_summary.json
c42c01436e0ad4dd99b3ebc7d99b1a7330989fe0732f0e325a8e28c55d0230d6       255  SIL/date/zenoh/loss_5/rep3/transport_p64_summary.json
1cec4e52f102aeb2b14d29f4423d173006ba552d2f4032e3f362051cd5adc448       254  SIL/date/zenoh/loss_5/rep3/transport_p65536_summary.json
35e6494065cfc57e36a094935291ae549e45f4376bb697459dc2ffc7cc6c72b1       256  SIL/date/zenoh/loss_5/rep4/transport_p4096_summary.json
ff2d3b9d384a3cf78d6284584d476d87d13cdac58223763ed08b39703bde5d0a       255  SIL/date/zenoh/loss_5/rep4/transport_p64_summary.json
bda0a1347def7202e61f88c79eb82824dbcdf32cd28123409ddfe998a190ed4c       256  SIL/date/zenoh/loss_5/rep4/transport_p65536_summary.json
112f09dedf325f60c16c1164293f3a3579ac7605f95a19a63f64e7d782108537       256  SIL/date/zenoh/loss_5/rep5/transport_p4096_summary.json
5c1fa2affccfe21ae742871700afeeabf0d13ed39c776f833f010a7ff2f6108a       254  SIL/date/zenoh/loss_5/rep5/transport_p64_summary.json
f29a43b095fe18cea0db07c27ebac86cb2a98825412e31722b04db33f42456b5       256  SIL/date/zenoh/loss_5/rep5/transport_p65536_summary.json
486bf1feb87821143b7b8e253133ff0c7f08a58c875c383edd803fbd93c3c66e       255  SIL/date/zenoh/loss_5/rep6/transport_p4096_summary.json
0f9f1d269fdf6a588b58ba11613cd3e56dba2338d02a9ee4286b4e6eacddfa28       253  SIL/date/zenoh/loss_5/rep6/transport_p64_summary.json
4c01106678d9a3740bedf772bdaff6a58b17b20b2bb7a34aea5252090ed78e11       254  SIL/date/zenoh/loss_5/rep6/transport_p65536_summary.json
9f9947eb39f24e7dd998a82b48da81d3fc1fa27b25d45f1082cf7b453c49e8dc       254  SIL/date/zenoh/loss_5/rep7/transport_p4096_summary.json
87e3159c4656aa710c5fd50c76be6c88e053c9646fa3595663cc56ca69fc042f       252  SIL/date/zenoh/loss_5/rep7/transport_p64_summary.json
74dba534ba2b3c7d141853bf8c367e5c7d4415ddc67840da193e8585cd30a9a4       256  SIL/date/zenoh/loss_5/rep7/transport_p65536_summary.json
69fabde3a6499f287b721bb54f4cf126fdedf9bef96e8cde93edfe42611320c3       254  SIL/date/zenoh/loss_5/rep8/transport_p4096_summary.json
4cc56109c66a1bdadc1a6343e4f8afc5c8353ad34c032201b195eeab168d889a       255  SIL/date/zenoh/loss_5/rep8/transport_p64_summary.json
93f626e66355752d78a6de7bc34a95ce35fef935e46350ee12b33ffdfdd6e546       255  SIL/date/zenoh/loss_5/rep8/transport_p65536_summary.json
adf72b07a3e86e383de81077504115b62976058e6829f10af745c75221e81b1e       257  SIL/date/zenoh/loss_5/rep9/transport_p4096_summary.json
228e5fc352303c6f3172fd0ef1af072bf8b6f899751f943ce334943676e390c5       257  SIL/date/zenoh/loss_5/rep9/transport_p64_summary.json
1482fc2cb08459c63a7dac675441c423adf277268410ee3fe8dfbe78253413c7       256  SIL/date/zenoh/loss_5/rep9/transport_p65536_summary.json
474d479a41e35503682327f840023313e57883182040c32a9ecd2e7f82f64d70       259  HIL_WIFI/date/cyclonedds/ideal/rep1/transport_p4096_summary.json
269d718268cfb00f304bba79dcee9561145457b4f943494e8f32d358784faecb       253  HIL_WIFI/date/cyclonedds/ideal/rep1/transport_p64_summary.json
2ed88a18535a511e59ec3b908661c94352e758bf7e0f02c25ef402c35344c05a       271  HIL_WIFI/date/cyclonedds/ideal/rep1/transport_p65536_summary.json
ee9bc4b23093d29e123ad58e078da81ed1d55d1e25eeac30a101a9a1807565d6       260  HIL_WIFI/date/cyclonedds/ideal/rep2/transport_p4096_summary.json
97feb824b1f935166a02da4d8eca6cb2a60b370e9477514a0ee229c534901be3       252  HIL_WIFI/date/cyclonedds/ideal/rep2/transport_p64_summary.json
529309bd687a01b9f4bf5f65a98c1bd87a7637927537e5e9d790319567c10437       266  HIL_WIFI/date/cyclonedds/ideal/rep2/transport_p65536_summary.json
3796ec22e945d16a072859ca499dad7f5fc0b06374f7af7e73b3136ad2584446       259  HIL_WIFI/date/cyclonedds/ideal/rep3/transport_p4096_summary.json
d63cbf663f240174f65f3ec12bf3f52adadbf5b2028a4951821b88d0320c108f       255  HIL_WIFI/date/cyclonedds/ideal/rep3/transport_p64_summary.json
ec45c69960f7e68dd7546e34c84918aed50bf21fc0062a851c3599a4277923cb       269  HIL_WIFI/date/cyclonedds/ideal/rep3/transport_p65536_summary.json
8c7e1862ed0551901339aced261547228b3851cde0629a96d2612acd16e082b3       260  HIL_WIFI/date/cyclonedds/ideal/rep4/transport_p4096_summary.json
d8cbb405ebb24a8235139bbf4db091adf2621979229b2ad28a89727c617df095       254  HIL_WIFI/date/cyclonedds/ideal/rep4/transport_p64_summary.json
1d866740f847dcea76a789ebd135212364a559b4ddf6836c2c660b60abaaa0c1       270  HIL_WIFI/date/cyclonedds/ideal/rep4/transport_p65536_summary.json
a50e0647efdc9433e0eb9da22391ef7b7c035fe5fc7fb98117e94f7bc53dddc3       260  HIL_WIFI/date/cyclonedds/ideal/rep5/transport_p4096_summary.json
0467e5d3a14361db8093db0f8ebfbe75be3ed391af40d2ecfcd2b8ea849503c1       254  HIL_WIFI/date/cyclonedds/ideal/rep5/transport_p64_summary.json
28a063340f4b2de95a038ba5c69395a1e5dbf8cdcf9a4ab729778e8c7b81065e       271  HIL_WIFI/date/cyclonedds/ideal/rep5/transport_p65536_summary.json
800504c9081977d5616d9812b62a6437eb88adb82393b1e638d9563330c4a214       269  HIL_WIFI/date/cyclonedds/lat200_jit50/rep1/transport_p4096_summary.json
998477aebd2ff4cd2c6bc9a52a93f66a8cfeb4983a074b8776b4d2d964e2bac4       265  HIL_WIFI/date/cyclonedds/lat200_jit50/rep1/transport_p64_summary.json
76ca70e52535f5f7b569d805e97528cb652386798d681fcb8d1b1af5ffe0f376       272  HIL_WIFI/date/cyclonedds/lat200_jit50/rep1/transport_p65536_summary.json
4a3321c37fe4cb6f4e2a193cbd89774542e41f213c0ef8b2e6ee9c8a5050f3a9       273  HIL_WIFI/date/cyclonedds/lat200_jit50/rep2/transport_p4096_summary.json
084e97254bbca9390446455511fc9d328bd1d09d42ae89d65e012e23767d7097       266  HIL_WIFI/date/cyclonedds/lat200_jit50/rep2/transport_p64_summary.json
8cf1789f7d75f2b700aa032302efe7965a909deeda756af43d3db68addcb4d05       271  HIL_WIFI/date/cyclonedds/lat200_jit50/rep2/transport_p65536_summary.json
8ad4804ec8fc296232df97383dc2f1cb4fdb7ead2bec9f76910e242974a95082       269  HIL_WIFI/date/cyclonedds/lat200_jit50/rep3/transport_p4096_summary.json
c334d4533066eddceea15bb887b57da427f8345f0548210471041a2f6773d15d       266  HIL_WIFI/date/cyclonedds/lat200_jit50/rep3/transport_p64_summary.json
ecf7870300b1e5f1e01f5e4b0e1c1f5d49fdf2653b053713e5120693371f95e6       273  HIL_WIFI/date/cyclonedds/lat200_jit50/rep3/transport_p65536_summary.json
8fea74381ab57c66894b276ffe0db02252b8f4c90fc1826e6883bc7e27fdeef8       268  HIL_WIFI/date/cyclonedds/lat200_jit50/rep4/transport_p4096_summary.json
59ce24b98b16a3c40ddb0725c84dfab9d17577b067cf7dba0b907a4642484140       268  HIL_WIFI/date/cyclonedds/lat200_jit50/rep4/transport_p64_summary.json
7e008385ef22905a1f18b7fa848b99203541878155a80074c1c2380502932b79       270  HIL_WIFI/date/cyclonedds/lat200_jit50/rep4/transport_p65536_summary.json
f326679ac63974a655ea0899558fc31eaa784303fe2b93073bf59de9ce50aa7d       269  HIL_WIFI/date/cyclonedds/lat200_jit50/rep5/transport_p4096_summary.json
9008a044f4e462bc274ea0a3c677cd8df6036b23bf10e1b4963ad9f9a34195b8       268  HIL_WIFI/date/cyclonedds/lat200_jit50/rep5/transport_p64_summary.json
56f08b457281ca5fb9d87ffb67f22835ed8a074b3925454cf79515c2058ec482       269  HIL_WIFI/date/cyclonedds/lat200_jit50/rep5/transport_p65536_summary.json
0a9f1c594820273f3bd94dc92be1619f1d10eaeb7136ec72a373a16c34f4ac23       273  HIL_WIFI/date/cyclonedds/lat200_l15/rep1/transport_p4096_summary.json
99589949e30e34c3f05decf6f7094743d96a9bf956dc5934bac6507c7d13d2fe       272  HIL_WIFI/date/cyclonedds/lat200_l15/rep1/transport_p64_summary.json
a9251fbf718c854b7e82509a543cf1c1c390074d4494c4584ddb6d46157c20f0       272  HIL_WIFI/date/cyclonedds/lat200_l15/rep1/transport_p65536_summary.json
3d55eda0f3d55300fe1a8846cd4194f27f0efbe992fd0f5fd09748e459fe014f       276  HIL_WIFI/date/cyclonedds/lat200_l15/rep2/transport_p4096_summary.json
228b6f20969d1cf560f5c3dac019f907a9ee2e7dae0ee8f87f646e6d1a2e3240       272  HIL_WIFI/date/cyclonedds/lat200_l15/rep2/transport_p64_summary.json
d549e0067d7e9c59e9e2d7568ab0d6e2f80ce493591fc51651b1d8c14c183aa8       143  HIL_WIFI/date/cyclonedds/lat200_l15/rep2/transport_p65536_summary.json
eb85868a10194678131ca08b9590357e14ab569b51bc1dd2bfdec24818290d48       274  HIL_WIFI/date/cyclonedds/lat200_l15/rep3/transport_p4096_summary.json
0272ccdc78083bc324f124a4fb531bdf7be2faabcd2781e98625de1aa619d133       269  HIL_WIFI/date/cyclonedds/lat200_l15/rep3/transport_p64_summary.json
e52385ad74d3987c90803df7b483f3e4ea860a4e9836e5d5179499de90b1a11b       272  HIL_WIFI/date/cyclonedds/lat200_l15/rep3/transport_p65536_summary.json
ef02ec12258064aa8475ac55bcda7f691a7f371617fba3069a813c1d03af73d7       274  HIL_WIFI/date/cyclonedds/lat200_l15/rep4/transport_p4096_summary.json
f08ab8bd2f06170d832e25e2c2af1b00fdf48b3f360c25557a61746783f36e12       273  HIL_WIFI/date/cyclonedds/lat200_l15/rep4/transport_p64_summary.json
fe288051f4c7cb2c59e04bbcc840cc7b1933a6cf5087b8c003d25baec365beca       272  HIL_WIFI/date/cyclonedds/lat200_l15/rep4/transport_p65536_summary.json
f3e36e5e708c55cd82779d85003787f720f67beca3de38d9686b11140ffb0e19       276  HIL_WIFI/date/cyclonedds/lat200_l15/rep5/transport_p4096_summary.json
3f238e45b9dc9833bdffd9f5c73fbebb874b0729cfa5349a1a52060f3a02e0c6       273  HIL_WIFI/date/cyclonedds/lat200_l15/rep5/transport_p64_summary.json
d549e0067d7e9c59e9e2d7568ab0d6e2f80ce493591fc51651b1d8c14c183aa8       143  HIL_WIFI/date/cyclonedds/lat200_l15/rep5/transport_p65536_summary.json
7b71f6cb58e0169827a5e4da374660de2df71adaae0e5c529d9c5a0c7b259ab2       274  HIL_WIFI/date/cyclonedds/loss_15/rep1/transport_p4096_summary.json
ea80bee081f8ea6a0ffa4832339a898dd9a933dd27c40b54352179e97a786266       260  HIL_WIFI/date/cyclonedds/loss_15/rep1/transport_p64_summary.json
26e57dfc730485a4b9cfe7828432b5ebc08dc35853a2ebcb88ee817a05ba4663       271  HIL_WIFI/date/cyclonedds/loss_15/rep1/transport_p65536_summary.json
4d31d618fd0e57d982cdf2ccbe1de2ebe5229046784a5a7ab2b87f8d188d5bab       273  HIL_WIFI/date/cyclonedds/loss_15/rep2/transport_p4096_summary.json
79b4dd1310e7276bf638387844e6081b109e9a89e11601cdd6ceb3a22880448d       258  HIL_WIFI/date/cyclonedds/loss_15/rep2/transport_p64_summary.json
c7a904bb38b0099a3d81e5a270f7eb5cdc34a7ed77a515d2dc05205ac2d8d58b       271  HIL_WIFI/date/cyclonedds/loss_15/rep2/transport_p65536_summary.json
f5940d90e0459da3a2ca2b64626deeda3d69aa6139e996b5946c4e0ffa1cb993       275  HIL_WIFI/date/cyclonedds/loss_15/rep3/transport_p4096_summary.json
10a1b04652a052a6bdb01c7a2643dea1f725503e75a8acb0ce11471a5b50d8ae       261  HIL_WIFI/date/cyclonedds/loss_15/rep3/transport_p64_summary.json
cda7f0892bea3a4899fd4dd859819d210f5b7fac2e0b725318e1b5e3733ee88e       273  HIL_WIFI/date/cyclonedds/loss_15/rep3/transport_p65536_summary.json
a73d53f9436110904e80ce1b7dfdd0a9054e2faef2f6e5c316e2701ec0df9f93       275  HIL_WIFI/date/cyclonedds/loss_15/rep4/transport_p4096_summary.json
23eeff3b8e5299bd4eb53b506d4610edda3de8221a7795819f7e98dd6b9e4287       261  HIL_WIFI/date/cyclonedds/loss_15/rep4/transport_p64_summary.json
e1effd17c3080f15bc58cd7b5caec5f4a1731faed2d79db9adbc727012d7b67e       273  HIL_WIFI/date/cyclonedds/loss_15/rep4/transport_p65536_summary.json
1adeba45073e5d2df0971e1b4b761e38102ac5e9fabc238e444ff2732a0b0db2       275  HIL_WIFI/date/cyclonedds/loss_15/rep5/transport_p4096_summary.json
5bbdf2ff42fd91e8061daab3c331c8e6a401a7bc9ac840d9725647944a307280       261  HIL_WIFI/date/cyclonedds/loss_15/rep5/transport_p64_summary.json
5c598fd42a1e8ad5735b0c42eedd953ec75aa245975ac9a9b4a200ef0df809ad       270  HIL_WIFI/date/cyclonedds/loss_15/rep5/transport_p65536_summary.json
e7f5da9c4d051b9f64c0e7d50b07504685e04f9c50608fd716208277bfe7dafb       273  HIL_WIFI/date/cyclonedds/loss_20/rep1/transport_p4096_summary.json
17be91669f1e77bfd3820e5fba7f20f354005b35b4e61063715c279a8e6ec873       262  HIL_WIFI/date/cyclonedds/loss_20/rep1/transport_p64_summary.json
facad65afe7942ceb54945a5d823c1d1ba5063cd1b4f0ad69f69b95c68733159       272  HIL_WIFI/date/cyclonedds/loss_20/rep1/transport_p65536_summary.json
b1242a31140384010e888de0f31a619952dddcd32127272becf497a04b131c25       275  HIL_WIFI/date/cyclonedds/loss_20/rep2/transport_p4096_summary.json
996cf0332e2208a0ad97a2d75fb02a18efc41fd53b65b1a2cd2d96995d87fc5c       262  HIL_WIFI/date/cyclonedds/loss_20/rep2/transport_p64_summary.json
8ed21db45be7c99584082b6750d37dbba4b5dbfa5aa55f57493f2b0e589d5123       272  HIL_WIFI/date/cyclonedds/loss_20/rep2/transport_p65536_summary.json
b2cb0d15eafbbaf25245a3c462b53f8681153ae4587551452f0813ff6f0c02e0       276  HIL_WIFI/date/cyclonedds/loss_20/rep3/transport_p4096_summary.json
d9c6fa1d2a8f06b460c8ba461cadb4f223977e123d3b4efdf7796cee6e808b52       264  HIL_WIFI/date/cyclonedds/loss_20/rep3/transport_p64_summary.json
6c2eafdf1409d6b4ace63f147f2477b44114f029eee2024fff245330a3ac8398       273  HIL_WIFI/date/cyclonedds/loss_20/rep3/transport_p65536_summary.json
97330dd03663a72363a36f19ed4821fede94d7a5af40dba9a599d3f32ba0f9df       274  HIL_WIFI/date/cyclonedds/loss_20/rep4/transport_p4096_summary.json
a6a262d3538dc276ab6345b8560bcb498402a5c8768d64010e63fdee15c59be8       263  HIL_WIFI/date/cyclonedds/loss_20/rep4/transport_p64_summary.json
caf29c65776964223707b115ebc5bc6e70e93cbb6a2f535e8ee419f5aceabc83       271  HIL_WIFI/date/cyclonedds/loss_20/rep4/transport_p65536_summary.json
cec6cf24b4545080496be114bd344e1e72662b08ad0a3efe542dd2fbb120009b       271  HIL_WIFI/date/cyclonedds/loss_20/rep5/transport_p4096_summary.json
0e5d3a024ea50ca95efeae41dbfb2ed116e293aa80b8880721e63dca06189bba       265  HIL_WIFI/date/cyclonedds/loss_20/rep5/transport_p64_summary.json
d549e0067d7e9c59e9e2d7568ab0d6e2f80ce493591fc51651b1d8c14c183aa8       143  HIL_WIFI/date/cyclonedds/loss_20/rep5/transport_p65536_summary.json
7334e518428f767d1ac327767cbe7eb3b92f3cee6c1850cf75c18d4f2d41eccd       275  HIL_WIFI/date/cyclonedds/loss_25/rep1/transport_p4096_summary.json
bed00874d26268cc427a891997c0c4c414e076b1cf9110e820ed3d465dc2e323       265  HIL_WIFI/date/cyclonedds/loss_25/rep1/transport_p64_summary.json
bb5edcac8d705f933092859efbce5ebbbb484b23e7ce66098ab989b940cb8889       272  HIL_WIFI/date/cyclonedds/loss_25/rep1/transport_p65536_summary.json
d77eb4d5b3d2a2e55f3d65fdea97c28ebe90eea6e780821a04fc845daa3c9a24       273  HIL_WIFI/date/cyclonedds/loss_25/rep2/transport_p4096_summary.json
b634ac4412bfb1f9a553d7b760245c0b07b1f7f13f71328fed11bfb062a28934       263  HIL_WIFI/date/cyclonedds/loss_25/rep2/transport_p64_summary.json
3004b5caee36f460c4125083bf68df664f0e9860368fa7b4e03bdbad7963fe0e       143  HIL_WIFI/date/cyclonedds/loss_25/rep2/transport_p65536_summary.json
9a221471c3ca1b6b32ff34cdf0ed01c6211aa23574f031b48ac767d41e122007       274  HIL_WIFI/date/cyclonedds/loss_25/rep3/transport_p4096_summary.json
15d7b28686ecaa8b6b4a70c23919a483c2c0e5dd389979b2498ebbf532f436fc       266  HIL_WIFI/date/cyclonedds/loss_25/rep3/transport_p64_summary.json
2ed9553d290052fb62f5d030332801a12a1b1450d20f42c3755b2d855e269f5f       272  HIL_WIFI/date/cyclonedds/loss_25/rep3/transport_p65536_summary.json
fe90fe82a1063f4ede254cacdc89b7af220b220b7cd89bf9da1e067df35e9b2a       276  HIL_WIFI/date/cyclonedds/loss_25/rep4/transport_p4096_summary.json
28b3e59dc22c26ec4a6bf924ef590355a9d518f64983fd1f5a055d912dfac7f7       268  HIL_WIFI/date/cyclonedds/loss_25/rep4/transport_p64_summary.json
25c239da67283bbeb801fb32320fc7f9e3002b0fb07195f9983e3b0652e74fb0       273  HIL_WIFI/date/cyclonedds/loss_25/rep4/transport_p65536_summary.json
397222c661ff4a9e081f1871d0df182a6ec2dbd6b42762fe09c38fc5fb1663aa       276  HIL_WIFI/date/cyclonedds/loss_25/rep5/transport_p4096_summary.json
35282c4c563533994a061cdb57d2246681262afaa6870a928303fd1ac1fc977d       266  HIL_WIFI/date/cyclonedds/loss_25/rep5/transport_p64_summary.json
eb684b318156a7cbd469ee2db9dd172bb017bcf2664daf47772580d737cf9213       268  HIL_WIFI/date/cyclonedds/loss_25/rep5/transport_p65536_summary.json
4d52bcadaaa56bb438efb660d1f9c87d21620bb636ec92b58aa9981200358967       275  HIL_WIFI/date/cyclonedds/loss_30/rep1/transport_p4096_summary.json
515ac699072f2d0462f1f17f6572fdd821d5529753737e542a742a57e76237e8       270  HIL_WIFI/date/cyclonedds/loss_30/rep1/transport_p64_summary.json
8a518ce176461af00e4ac2d1ce7c702397c0ef430d686b6bba8d3d8653bd32cf       143  HIL_WIFI/date/cyclonedds/loss_30/rep1/transport_p65536_summary.json
0cec20986a19b6f04119257bc4278f8f49b63a34b51295e02cdc08726ae9cf5a       275  HIL_WIFI/date/cyclonedds/loss_30/rep2/transport_p4096_summary.json
293d23ba70388e778c13f65254595143255da595312fa708d66cb66433a25fa1       266  HIL_WIFI/date/cyclonedds/loss_30/rep2/transport_p64_summary.json
8a518ce176461af00e4ac2d1ce7c702397c0ef430d686b6bba8d3d8653bd32cf       143  HIL_WIFI/date/cyclonedds/loss_30/rep2/transport_p65536_summary.json
e8298395628f98b61d7261bb5b7221c220f16239f44b533202c663338a3d9635       275  HIL_WIFI/date/cyclonedds/loss_30/rep3/transport_p4096_summary.json
d67f70db0e3a2d319336ace2e284b298aac20bf0bea5a743fc2b8c7a40187309       267  HIL_WIFI/date/cyclonedds/loss_30/rep3/transport_p64_summary.json
c47ce57dc73c8698bf1bc24802912b698e3b5efc2748aa8722f39f7707b25dba       143  HIL_WIFI/date/cyclonedds/loss_30/rep3/transport_p65536_summary.json
a4d402b0f644ed82f1b2ba51b2ca09634ccd65e0443774659df3710458468514       276  HIL_WIFI/date/cyclonedds/loss_30/rep4/transport_p4096_summary.json
b949101bf256bf3f1b7dbf2058f2979e8f3de821ec046dc13f89f949cc67a6aa       268  HIL_WIFI/date/cyclonedds/loss_30/rep4/transport_p64_summary.json
92f10530fc2d52a1b8bde282704696028e0e889b707554456fe61ea5feeb3e8b       143  HIL_WIFI/date/cyclonedds/loss_30/rep4/transport_p65536_summary.json
0b4331410e65c3d29bf9ecc30f97484feaef59b19ca9c01a8fcfcdae95234006       275  HIL_WIFI/date/cyclonedds/loss_30/rep5/transport_p4096_summary.json
9a64be8f749bb091b0dd2a54d80be2040436ed3dcf2cce52d9f209cca5fb0ab3       268  HIL_WIFI/date/cyclonedds/loss_30/rep5/transport_p64_summary.json
f592ed36dee47e0cca6cc1662a4af42c92f807a19bb3294b11275df699d2ce11       143  HIL_WIFI/date/cyclonedds/loss_30/rep5/transport_p65536_summary.json
53221d3d0f22ab28715246249df6f748ecc4825ab87c397c4681d49151833ba4       263  HIL_WIFI/date/cyclonedds/loss_5/rep1/transport_p4096_summary.json
91aae9b7dec6c0a1d279f442ff225fdce5bebe9cb6dbe4f6645c462509332087       260  HIL_WIFI/date/cyclonedds/loss_5/rep1/transport_p64_summary.json
84718b06b9622791d9e7b8c6f88257589b12954b071a0d0c0732f16ef1b2fc0d       270  HIL_WIFI/date/cyclonedds/loss_5/rep1/transport_p65536_summary.json
cd9852e0b29b6cdf670b3bef73deffb30915ad2496bdb283942da5838250ad4b       264  HIL_WIFI/date/cyclonedds/loss_5/rep2/transport_p4096_summary.json
0069b61daf2945716234457355d6719add52ef94a5fb0be835c41ac2cf3ec53c       262  HIL_WIFI/date/cyclonedds/loss_5/rep2/transport_p64_summary.json
229282914c25fc3901556e3bd2ed47222f315ee046b891dfee4da3b659d66ec9       275  HIL_WIFI/date/cyclonedds/loss_5/rep2/transport_p65536_summary.json
dc13be76bec64df64aef15f9e94f53f15f34d2930009fe668e2a1349a10bfdd2       263  HIL_WIFI/date/cyclonedds/loss_5/rep3/transport_p4096_summary.json
29c269e1ad04d6112bd61c0a6eb820fb0abe04af0c385aee4e6c47c0a8611207       257  HIL_WIFI/date/cyclonedds/loss_5/rep3/transport_p64_summary.json
7e4da5c76f6d43b84d785b91b4919d4824b11b95046838167f1cdeca0608f136       275  HIL_WIFI/date/cyclonedds/loss_5/rep3/transport_p65536_summary.json
f7410b7d81ce55cfbe7fe7b84a5d0c151593a263e9aba924fadd453781da7693       263  HIL_WIFI/date/cyclonedds/loss_5/rep4/transport_p4096_summary.json
2142bd96b2bf31784c39563049f9200ad285b88edb061c41cc33209f4253794c       261  HIL_WIFI/date/cyclonedds/loss_5/rep4/transport_p64_summary.json
6c19ec63ce9d18ecac397490d761170465b31afcd2a9b75c37f662db07538775       273  HIL_WIFI/date/cyclonedds/loss_5/rep4/transport_p65536_summary.json
beb9dac61a964a2ac6be63f674a79a024209932c8cc49ec691bde06870093e44       264  HIL_WIFI/date/cyclonedds/loss_5/rep5/transport_p4096_summary.json
fa7a8edb85af6a27f8ff89c7888ea4686a44ac30b3c210a688ac9e234c13e85d       262  HIL_WIFI/date/cyclonedds/loss_5/rep5/transport_p64_summary.json
a55a63a6362770cbbc45a43cf15acb8cb739d44d0a59d020af7e0cc579ede98b       274  HIL_WIFI/date/cyclonedds/loss_5/rep5/transport_p65536_summary.json
e77ff15ae225973cc2df45f460432941bb94dcffeabe9a23178a6f958215a858       256  HIL_WIFI/date/zenoh/ideal/rep1/transport_p4096_summary.json
a13921f4bf1070edcf59148bdceafa16d001deb1ec3fd8a54c3f2285aad3b680       250  HIL_WIFI/date/zenoh/ideal/rep1/transport_p64_summary.json
48a5fe51547a7eecbe3d902f3aa70dd721a7c8123aa6d53dee9770eb7d900a00       271  HIL_WIFI/date/zenoh/ideal/rep1/transport_p65536_summary.json
ff51e5c8fccffe8bac2d40de2b825b4566156354ba2f21f7cf69d5497687cf5d       253  HIL_WIFI/date/zenoh/ideal/rep2/transport_p4096_summary.json
5d32e7658630c46f9a19c10517b0345722a3c1a4687c887b5ad7128fc4c50914       254  HIL_WIFI/date/zenoh/ideal/rep2/transport_p64_summary.json
c48084ea334ad6666a12f10e7648444aea48db6d999ffbc798b9d3d041867051       271  HIL_WIFI/date/zenoh/ideal/rep2/transport_p65536_summary.json
887ebb9166d4901ac21e0b51c892a03ad468987cefbba5b6459908532cc82f01       254  HIL_WIFI/date/zenoh/ideal/rep3/transport_p4096_summary.json
e763427127040970e7ae74e79dd5f4156004bd493593f77b02bf73d58fc0b5bc       253  HIL_WIFI/date/zenoh/ideal/rep3/transport_p64_summary.json
b006501450e3f9323ef408f26b601ac92d63e0ea76a40aa231aada310d9937a9       269  HIL_WIFI/date/zenoh/ideal/rep3/transport_p65536_summary.json
be5686a86d23fd140bef7efdceddbba7a9ae766f9fcc1262295532d3d16f890a       254  HIL_WIFI/date/zenoh/ideal/rep4/transport_p4096_summary.json
82c0675bbe9db744d662fe661cf8e7298a5e0c8a772da0bfdd014f5f570b69b4       254  HIL_WIFI/date/zenoh/ideal/rep4/transport_p64_summary.json
5182fb79209e450141162bab72974374935d117ece00f0cb67fbf3c542b211f5       271  HIL_WIFI/date/zenoh/ideal/rep4/transport_p65536_summary.json
8d1fce758151491abce3b060e87eab43dcb44bb1870211d425a60b2b9f3c4a94       255  HIL_WIFI/date/zenoh/ideal/rep5/transport_p4096_summary.json
a1ba2e43fda693d20516c5fa35b24ebe54e7c7c30207eaab073e868499f78324       251  HIL_WIFI/date/zenoh/ideal/rep5/transport_p64_summary.json
a00d3f25c8d240ecee52d087d903296f6352a909fb809faa6086df327adcd177       270  HIL_WIFI/date/zenoh/ideal/rep5/transport_p65536_summary.json
51b6a810f43bdf208e4e54143234810940de1cb54d009db8620176351ffc0ef9       270  HIL_WIFI/date/zenoh/lat200_jit50/rep1/transport_p4096_summary.json
ee8283dfa1237e9f4d7bb25c41e3518de8f92d09f0e303d52370244d2e3b90a6       261  HIL_WIFI/date/zenoh/lat200_jit50/rep1/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/lat200_jit50/rep1/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/lat200_jit50/rep2/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/lat200_jit50/rep2/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/lat200_jit50/rep2/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/lat200_jit50/rep3/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/lat200_jit50/rep3/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/lat200_jit50/rep3/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/lat200_jit50/rep4/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/lat200_jit50/rep4/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/lat200_jit50/rep4/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/lat200_jit50/rep5/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/lat200_jit50/rep5/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/lat200_jit50/rep5/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/lat200_l15/rep1/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/lat200_l15/rep1/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/lat200_l15/rep1/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/lat200_l15/rep2/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/lat200_l15/rep2/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/lat200_l15/rep2/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/lat200_l15/rep3/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/lat200_l15/rep3/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/lat200_l15/rep3/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/lat200_l15/rep4/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/lat200_l15/rep4/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/lat200_l15/rep4/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/lat200_l15/rep5/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/lat200_l15/rep5/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/lat200_l15/rep5/transport_p65536_summary.json
5b24b013c1c315730e5e6aec3555637bd70872c5a27c702802171618c447f0a7       273  HIL_WIFI/date/zenoh/loss_15/rep1/transport_p4096_summary.json
eb0700bd7f12756a8b6c86dc116d36598387edc4e421a6e3c4c3e2b02df86158       256  HIL_WIFI/date/zenoh/loss_15/rep1/transport_p64_summary.json
e0e57c5334f5264ac963b583099861220103f41bbd3f141d25bed9f6a0b67495       264  HIL_WIFI/date/zenoh/loss_15/rep1/transport_p65536_summary.json
9116bcdd8d8641272e1b18fb30493835d92639125099283ec368bbd883876a34       270  HIL_WIFI/date/zenoh/loss_15/rep2/transport_p4096_summary.json
2b64f17e69bc6ca1e10a7f13c4ae4b9f7665e86bbbdb776363a80845b05e50d8       272  HIL_WIFI/date/zenoh/loss_15/rep2/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/loss_15/rep2/transport_p65536_summary.json
2c38e8c0b3e5c892e7379dcfede4365dc63fdf2d2aaebdee8c10e1491370b54a       263  HIL_WIFI/date/zenoh/loss_15/rep3/transport_p4096_summary.json
f7151bdc94719265b7ea9495201cce2a6695e629553f958bd2f422f34b6a63b3       270  HIL_WIFI/date/zenoh/loss_15/rep3/transport_p64_summary.json
a6724b0a4b49f9d84423de48c7eff813e647c509dd43347efc29d694ff255058       265  HIL_WIFI/date/zenoh/loss_15/rep3/transport_p65536_summary.json
96b910f02f55b468a94533425fb5677f7eb521797d5192287ba0912f2c263417       270  HIL_WIFI/date/zenoh/loss_15/rep4/transport_p4096_summary.json
d42b6a02f62b7f7e885802ef15256c6229fb0c1fd74e7162c481d9b1e7277576       263  HIL_WIFI/date/zenoh/loss_15/rep4/transport_p64_summary.json
47fa6fe34b5d998509ae2630a2ff6a416568792b9a0789da3eed460a1927eca4       269  HIL_WIFI/date/zenoh/loss_15/rep4/transport_p65536_summary.json
5bf1e417afd34f277ebda543364d0f4aeb9605500f46863adc653c75460fed2d       269  HIL_WIFI/date/zenoh/loss_15/rep5/transport_p4096_summary.json
bd484ec63c805c46c91c3b91254325d55e8e7cce60374793d9e8a91e76d3662f       262  HIL_WIFI/date/zenoh/loss_15/rep5/transport_p64_summary.json
57296a96b77fe87b84ef3d52ae2c182944949f7601ce7ea00f194d43f942f1c3       269  HIL_WIFI/date/zenoh/loss_15/rep5/transport_p65536_summary.json
8a5381a2d42bc34581a9dee0312e8a031abad7a946de10431a12d9ad6414be56       271  HIL_WIFI/date/zenoh/loss_20/rep1/transport_p4096_summary.json
68b184a89c250a050a4721d8d93703e9225a7fd74b7d1e16d9b523466eddb473       264  HIL_WIFI/date/zenoh/loss_20/rep1/transport_p64_summary.json
632db49214411d9d9db94491ac8a70ef8147cc8c8b27242e96b5e9888deb5d89       270  HIL_WIFI/date/zenoh/loss_20/rep1/transport_p65536_summary.json
eef839a3eb5d99ae872bbc6ff5e5298449ac641d0dbd71d15a11daf9ee77fcfd       271  HIL_WIFI/date/zenoh/loss_20/rep2/transport_p4096_summary.json
b98ad0192b710d3aa7780f1767135e4fbf9b5d5fce13cadb4303b90c7da1507d       263  HIL_WIFI/date/zenoh/loss_20/rep2/transport_p64_summary.json
afd2237a671c933bad9f23f9fb5429a021c005154f4653f973fe7ad489c83cbf       267  HIL_WIFI/date/zenoh/loss_20/rep2/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/loss_20/rep3/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/loss_20/rep3/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/loss_20/rep3/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/loss_20/rep4/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/loss_20/rep4/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/loss_20/rep4/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/loss_20/rep5/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/loss_20/rep5/transport_p64_summary.json
d26b788fca99afd8e82a383d64c1663fa6736e45a420fb07ba44a2b7fb96799b       267  HIL_WIFI/date/zenoh/loss_20/rep5/transport_p65536_summary.json
d3ba56407c62542a151ccfbcb16e60558188eda5775e4c247b9d9d45fe0c0051       275  HIL_WIFI/date/zenoh/loss_25/rep1/transport_p4096_summary.json
ff5acc7a1caf6ed9090913a27cf7bc281c80813aad7c0e5cc43efa319d781603       262  HIL_WIFI/date/zenoh/loss_25/rep1/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/loss_25/rep1/transport_p65536_summary.json
4f02393533f556ff7653ab3edfa42bc4622f6d360d0cb2bc8cbfd742bfddc53c       267  HIL_WIFI/date/zenoh/loss_25/rep2/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/loss_25/rep2/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/loss_25/rep2/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/loss_25/rep3/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/loss_25/rep3/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/loss_25/rep3/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/loss_25/rep4/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/loss_25/rep4/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/loss_25/rep4/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/loss_25/rep5/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/loss_25/rep5/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/loss_25/rep5/transport_p65536_summary.json
128efe4d13b624a30fb9d078f07cba1907d77e2d9ca1f188054828c731d589d4       266  HIL_WIFI/date/zenoh/loss_30/rep1/transport_p4096_summary.json
572206e7c200b1f19ea0a47a7f055ef294f6409cba1c8c75c94d4d492f5d1958       271  HIL_WIFI/date/zenoh/loss_30/rep1/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/loss_30/rep1/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/loss_30/rep2/transport_p4096_summary.json
3c5cda5d76027ff40c77b2619cab82c4d80c9256ee2d9bceb86d0fd961dd55a9       264  HIL_WIFI/date/zenoh/loss_30/rep2/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/loss_30/rep2/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/loss_30/rep3/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/loss_30/rep3/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/loss_30/rep3/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/loss_30/rep4/transport_p4096_summary.json
04c993392c189a7f9017a5de338ef6b8f718a2edba1fe8da04942cfc18725f32       135  HIL_WIFI/date/zenoh/loss_30/rep4/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/loss_30/rep4/transport_p65536_summary.json
9537685c61e1ad6d18e31d4f8d4649b5513716d930134c2a0eaf58e1b2939bb6       137  HIL_WIFI/date/zenoh/loss_30/rep5/transport_p4096_summary.json
780f89846dabb91dbeef8483796f46969bddc97b16469bd90eb7b88e99654979       265  HIL_WIFI/date/zenoh/loss_30/rep5/transport_p64_summary.json
9df937d20061615d4f71b66095793a3054bf7ce943c990df0ce2fa659fe3f6ec       138  HIL_WIFI/date/zenoh/loss_30/rep5/transport_p65536_summary.json
a75084f8e60d6745614660e76c78674ac31c7fb54196cb12585f9e548a424390       258  HIL_WIFI/date/zenoh/loss_5/rep1/transport_p4096_summary.json
2cdacd4ad7ced5b9b7e055413d1e6be1cc00ad5057157677cffeb58d0304bbbb       254  HIL_WIFI/date/zenoh/loss_5/rep1/transport_p64_summary.json
0f77d37f6a86cc2aab3d1947bb665971efae94ddc47d8f43032640a97eadaf7f       272  HIL_WIFI/date/zenoh/loss_5/rep1/transport_p65536_summary.json
c8281c2adfae4f275e78cdd107fc6a46f9f16a53131d0e5f26ca60eaead9ea68       258  HIL_WIFI/date/zenoh/loss_5/rep2/transport_p4096_summary.json
db88798d33582fa01130647082ed97e69ac1ec73cbc8dfded08ebc823b808de2       260  HIL_WIFI/date/zenoh/loss_5/rep2/transport_p64_summary.json
ab58283157f7a2e5b23cd4b1b310b6c7258e05ff8d5fcdfdddf7be54cc09e778       271  HIL_WIFI/date/zenoh/loss_5/rep2/transport_p65536_summary.json
e023a13d159eec16799fa5b54bf162c4b8745c17b9ed3feb5b493adb9eea80fe       258  HIL_WIFI/date/zenoh/loss_5/rep3/transport_p4096_summary.json
8ec19a779782f8c8579494f2c629d908c7ad3fbd23690705eababb7eaac5525f       260  HIL_WIFI/date/zenoh/loss_5/rep3/transport_p64_summary.json
f9a19158565c5eb7d3e07c19be4c2de5279b668da23dbe6266de24c5bed37e8f       271  HIL_WIFI/date/zenoh/loss_5/rep3/transport_p65536_summary.json
b14ae3ca4788953719a40c8fed117df6457950ce319d5653d6709e1fd702222e       261  HIL_WIFI/date/zenoh/loss_5/rep4/transport_p4096_summary.json
d957efc2e1c6f06138ac3499ebf19a09be9b6e01a1e0ad34b3bd8945215cf249       260  HIL_WIFI/date/zenoh/loss_5/rep4/transport_p64_summary.json
6b4a7755141d8b2ecb2aba5e2ff055ec9f386b19ac492c461ff7fe3e4afd5df6       270  HIL_WIFI/date/zenoh/loss_5/rep4/transport_p65536_summary.json
15f67fbe79403f9d298bb83c112d585695e4ab5cf2e81f17b2112c68452ceae1       258  HIL_WIFI/date/zenoh/loss_5/rep5/transport_p4096_summary.json
5aaba0a448cd3a9cbbf0b9b6a10579b6eefbf8ccc6c069cd24a7fa7599614509       258  HIL_WIFI/date/zenoh/loss_5/rep5/transport_p64_summary.json
a6e0d26cedfde638718ae7df54b273f9138e5f08d07336ce5230f68d799da749       272  HIL_WIFI/date/zenoh/loss_5/rep5/transport_p65536_summary.json
```
Nr fisiere hashuite: 720. (CSV-urile brute transport_p<P>.csv exista alaturi, acelasi layout.)

## Mapare reproductibilitate (campanie -> cod)

| campanie | data (README) | cod / invocare | ancora git | cele 8 conditii |
|----------|---------------|----------------|-----------|-----------------|
| SIL N=10 | 2026-06-24 | run_campaign.py --reps 10 (metoda fair in working-tree; codificata ulterior ca run_campaign_fair.sh) | working-tree 06-24, hash neinregistrat -- NU c61c1e2 (fair postdateaza c61c1e2) | byte-identice |
| HIL N=5  | 2026-07-01 | run_campaign.py --mode hil | 426bd77 (2026-06-26) | byte-identice |

Diff-ul c61c1e2..426bd77 NU afecteaza cele 8 conditii studiate: reconstructie duala a
netem_cmd -> comenzi byte-identice; rtt_stats, bench_client.py, bench_echo_server.py
identice (dovada completa in AUDIT_CIFRE_ARTICOL.md, sec. 1e).
CAVEAT (onestitate): commit-ul per rulare NU a fost inregistrat; maparea presupune
working tree curat la rulare -- neverificabil retroactiv. Arhiva SIL
(sil_N10_fair_20260624) a fost recuperata din Trash 2026-07-01.
Aceasta mapare intra si in descrierea Zenodo (campul Description / Method).

## Structura de arhiva propusa pentru Zenodo (NU creata, NU incarcata)

```
c1-benchmark-data-v2/
  README.md                 # din README_SIL.md + README_HIL_WIFI.md
  MANIFEST_DATE.md          # acest fisier (checksums)
  SIL/date/<rmw>/<cond>/rep<1..10>/transport_p{64,4096,65536}{.csv,_summary.json}
  HIL_WIFI/date/<rmw>/<cond>/rep<1..5>/transport_p{64,4096,65536}{.csv,_summary.json}
  aggregates/campaign_summary.csv   # p4096, media pe rep (make_tables)
  code/  -> link catre repo (bench_core.py, make_tables.py, make_figures_c1_en.py)
```
Licenta date: de ales (CC-BY-4.0 recomandat). DOI: rezervat la publicare.
