# Boîtier imprimé 3D pour la carte ayab-sr-esp32

Boîtier en deux pièces (fond + couvercle) pour la carte `ayab-sr-esp32` (placement du
commit d8073cd, avec **J2 décalé de 3,8 mm vers la gauche, à x = 128,78**, hors de la
zone d'exclusion de l'antenne ESP32).

![assemblé](renders/01_assembled.png)
![éclaté](renders/04_exploded.png)

| Fichier | Contenu |
|---|---|
| `ayab-sr-esp32-enclosure.scad` | Source OpenSCAD paramétrique (paramètres en tête de fichier) |
| `bottom.stl` | Fond, dans l'orientation d'impression (plancher sur le plateau) |
| `lid.stl` | Couvercle, dans l'orientation d'impression (à l'endroit, colonnes sur le plateau) |
| `renders/` | Vues fixes, coupes 2D, animations `turntable` et `exploded` (GIF et MP4, `quick_render.py --anim`) |
| `tools/` | Scripts Python (numpy/PIL) de la vérification d'ajustement, des coupes et des rendus (aperçu OpenGL d'OpenSCAD) |

Dimensions extérieures : **87,7 × 67,5 × 15,8 mm**, **30,3 mm** au sommet de la bosse de la DIN
(fond 13,65 mm ; couvercle : plaque de 2 mm, bosse de 16,5 mm au-dessus du joint).

## Choix de conception

- **Repère** : X = x KiCad, Y = −y KiCad, Z = 0 sous le PCB. Toutes les positions du `.scad`
  sont tapées en coordonnées KiCad (`kp()`, `krect()`), on peut donc les recopier
  directement depuis le PCB.
- **Dessus bas + bosse DIN** : le plafond est à 7,8 mm au-dessus du dessous du PCB, juste
  au-dessus du verre de l'OLED (6,75 mm, la pièce la plus haute après la DIN) ; dessus à
  9,8 mm. Seule la **DIN J3** (haut à 21,25 mm) dépasse : une bosse de 20 × 23 mm la
  recouvre (plafond 22,3 mm, sommet 24,3 mm), dans l'angle arrière droit.
- **J4 et J14 ne sont pas montés** (DNP dans le schéma et le PCB) : aucune ouverture
  pour eux, ils sont exclus des rendus et de la vérification d'ajustement.
- **Parois** 2 mm, jeu 0,3 mm autour du PCB, 0,5 mm côté USB/antenne (le module ESP32
  dépasse du bord de 0,16 mm). Le contour suit l'encoche haut-droite, où il s'arrête
  au ras de la face de la DIN (voir plus bas).
- **Fixation** : 3 vis **M3×12 tête fraisée (ISO 10642 / DIN 7991)** introduites par
  **dessous** : fraisure dans le fond → entretoise (4 mm) → trou du PCB → **insert
  laiton M3 à chaud** au bout d'une colonne du couvercle (Ø 6,6 mm). Le PCB est serré
  entre l'entretoise et la colonne ; le dessus du couvercle reste lisse. Les parois ont
  0,15 mm de jeu au joint, c'est le PCB qui encaisse le serrage.
  Variante sans insert : `use_inserts = false` → trou Ø 2,5 pour vis autotaraudeuse M3
  (ou vis plastique type 3×12). Aucun métal près de l'antenne (inserts en H1, H2, H3, loin).
- **Joint fond / couvercle à z = 7,8 mm** (le plafond) : les USB-C sont entièrement dans le fond
  (trous 9,6 × 3,9 mm, centrés sur les coques mesurées dans l'export 3D, ~0,35 mm de
  marge), avec une **poche extérieure commune** de 1,2 mm (paroi restante 0,8 mm) pour
  les surmoulages des câbles (les deux prises sont à 14,8 mm d'entraxe, comme les ports d'un MacBook : les doubles fiches USB-C pour MacBook s'y branchent).
  Gravures « PWR » (J1, USB-PD) et « ESP32 » (J2) sous les prises.
- **DIN J3** : **rien devant la prise**. Le boîtier s'arrête au ras de sa face avant
  (x = 181,7) sur toute la largeur de l'encoche du PCB (y < 48,0) : pas de paroi, et le
  fond, la bosse et la paroi arrière s'arrêtent au même plan. Le compartiment OLED /
  molette, qui dépasse sur le côté, est refermé le long du bord de l'encoche : sous le
  PCB par une paroi de 2 mm (**couper les broches du module OLED au ras sous la carte**
  après soudure), au-dessus par une jupe de 0,45 mm du couvercle (une fente
  laisse passer le bord du circuit du module OLED, à 0,13 mm du bord de l'encoche).
- **Molette S1** : elle dépasse jusqu'à x = 193,7, au-delà de la paroi : la fente du fond
  est **ouverte vers le haut** (on descend la carte verticalement, la molette passe dans
  la fente) et une **languette du couvercle** la referme au-dessus (z ≥ 4,6, molette ≤ 4,0).
  Une poche de 1 mm sur la face extérieure (y 55,5..77,8) dégage la molette : elle
  dépasse de 2,4 mm du fond de la poche. Fente 0,8 mm plus large que la molette de chaque côté.
- **OLED U5** : le verre est 1 mm sous la plaque du couvercle ; fenêtre 7,1 × 23,9 mm
  (zone active + 0,75 mm) à travers la plaque, chanfreinée à 45° vers l'extérieur.
- **Trimmers RV1/RV2** : pas d'accès dans le couvercle (réglage boîtier ouvert).
- **Antenne ESP32** : pas d'insert ni de vis à proximité.
- **Lèvre de centrage** de 2 mm sous le couvercle (côtés gauche, haut et bas), absente le
  long du côté droit (OLED, molette) et autour de la DIN.

## Impression

- Matériau : PETG conseillé (PLA possible, éviter alors un usage prolongé au soleil/chaleur).
- Buse 0,4 mm, couches 0,2 mm, 3 périmètres, 20 % de remplissage.
- `bottom.stl` : plancher sur le plateau. Les fraisures à 90° et les trous USB (petit pont
  de 9,6 mm) s'impriment sans support.
- `lid.stl` : **à l'endroit**, les 3 colonnes posées sur le plateau, **avec supports
  (« sur le plateau uniquement », supports arborescents conseillés)** sous la plaque, la
  lèvre et la languette de la molette. La bosse empêche de
  l'imprimer dessus sur le plateau ; à l'endroit, la face visible (dessus, gravure
  « AYAB Silver Reed », bosse) sort propre et les supports restent à l'intérieur. Le
  plafond de la bosse est un pont de 20 mm.
- Inserts : à poser au fer (≈ 220 °C pour PETG) dans les colonnes avant l'assemblage.

## Matériel

- 3 × vis M3×12 tête fraisée (ISO 10642 / DIN 7991) — M3×14 passe aussi.
- 3 × inserts laiton M3 à chaud (Ø ext. 4,6–5,0 mm, longueur ≤ 5,7 mm, trou Ø 4,0).
- Optionnel : 4 patins adhésifs sous le fond.

## Assemblage

1. Poser les 3 inserts dans les colonnes du couvercle.
2. Descendre la carte verticalement dans le fond : la molette passe dans la fente ouverte,
   les USB-C se présentent derrière leurs trous, la DIN derrière son demi-trou.
3. Poser le couvercle (la languette referme la fente de la molette, la lèvre centre).
4. Retourner l'ensemble en le tenant, visser les 3 vis M3 par-dessous sans forcer.

## Vérifications faites (numériques)

- Export 3D de la carte via `kicad-cli` (STEP, GLB, STL par composant) ; S1 (modèle X3D)
  et RV1/RV2 (modèle absent) ajoutés à la main.
- `tools/fitcheck.py` : aucun point des composants montés ni du PCB à l'intérieur des pièces ;
  sorties à moins de 0,3 mm seulement là où c'est voulu (face DIN / paroi 0,2 mm ;
  module OLED / colonne H2 0,4 mm ; antenne ESP32 / paroi 0,34 mm).
- `tools/openings_check.py` : coques USB-C dans leurs trous avec 0,33 mm (x) et
  0,36 mm (z) de marge ; molette y 60,6..72,7 dans une fente y 58,4..74,9 ; OLED à 6,75,
  plafond à 7,8 ; DIN : aucune pièce du boîtier devant la face.
- Coupes 2D : `renders/11..14_section_*.png`.

## Limites / à vérifier au premier tirage

- **Supports du couvercle** : inévitables avec la bosse en une seule pièce. Variante
  possible sans support : bosse en 3e pièce collée ou vissée.
- Colonnes plus courtes (6,2 mm) : trou d'insert de 6,5 mm, la pointe d'une vis M3×12
  arrive à 6,0 mm ; ne pas prendre plus long que M3×12.
- Le modèle de la DIN (DIN-704-M10) et du module OLED sont ceux de la bibliothèque : vérifier
  sur les vraies pièces la hauteur de la DIN, la hauteur réelle de l'OLED sur son
  entretoise de 2,5 mm et sa position latérale (0,4 mm de la colonne H2).
- Une fiche DIN à gros surmoulage peut toucher le côté du compartiment OLED (à 11 mm
  de l'axe de la prise) ; la jupe de 0,45 mm qui ferme ce compartiment est fragile, à
  vérifier au premier tirage.
- USB-C : surmoulages > 13 × 7,6 mm non prévus ; deux câbles très épais côte à côte
  peuvent se gêner (prises à 14,8 mm d'entraxe).
- Molette S1 : modèle X3D de la bibliothèque ayab ; vérifier la saillie réelle et la
  hauteur de la molette (languette du couvercle à z = 4,6).
- Ventilation non prévue (régulateurs à découpage + ESP32 : à surveiller en usage long).
- Le boîtier ne dépend que du placement, des trous H1, H2, H3 et du contour ; à revalider si
  un de ces éléments bouge.

## Régénérer

```sh
openscad -D 'part="tray_print"' -o bottom.stl ayab-sr-esp32-enclosure.scad
openscad -D 'part="lid_print"'  -o lid.stl    ayab-sr-esp32-enclosure.scad
# part = "assembly" | "exploded" | "tray" | "lid" pour visualiser dans OpenSCAD
```

Le script qui enchaîne tout (STL, exports KiCad, vérification d'ajustement, rendus) est sur la
branche `tooling`. Les scripts de `tools/` (Python 3 + numpy + PIL) travaillent dans un dossier
contenant `board.glb`, `pcb_only.stl`, `comp/<REF>.stl`, `tray_asm.stl` et `lid_asm.stl`.
