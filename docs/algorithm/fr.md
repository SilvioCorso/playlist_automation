# Comment le pourcentage de correspondance est calculé

Ce document explique **pas à pas** comment le logiciel attribue le
pourcentage (colonne **Valeur**) à chaque piste de la playlist lors de la comparaison
avec votre bibliothèque musicale. À la fin, vous trouverez plusieurs **exemples concrets** avec le
calcul détaillé.

> En bref : pour chaque piste demandée, le logiciel recherche le meilleur candidat dans la
> bibliothèque avec une **cascade de techniques de comparaison**. Ensuite, si le **titre
> demandé est entièrement présent** dans la piste trouvée, il calcule le score avec
> un **modèle comptable** : départ à **100%**, moins des pénalités précises.
> Si le titre n'est que partiellement présent, des **seuils stricts** entrent en jeu et
> limitent fortement le score.

---

## 1. Priorité absolue : les verrous (100% garanti)

Avant toute comparaison, le logiciel vérifie si la piste est **verrouillée**.
Si c'est le cas, le score est **fixé à 100%** et tout le reste est ignoré.

Il existe deux types de verrou :

1. **Composer lock** — la balise `[lock]` est écrite **dans les métadonnées du fichier
   audio** (champ compositeur). C'est le plus robuste : il survit aux déplacements de
   fichiers et aux changements d'ordinateur.
2. **Title lock** — une correspondance *titre → fichier* que vous avez confirmée,
   enregistrée dans le fichier `title_locks.json`.

Dans les deux cas, il suffit que le titre demandé soit **contenu** dans le titre de la
piste verrouillée. Pour retirer les 100%, cliquez sur le cadenas de la ligne pour la
déverrouiller : le score sera recalculé normalement.

---

## 2. La cascade de recherche

Si la piste **n'est pas** verrouillée, le logiciel recherche le meilleur candidat en essayant
ces techniques dans l'ordre. **Il s'arrête à la première qui donne un résultat valide.**

| # | Passe | Ce qu'elle fait |
|---|-------|-----------------|
| 1 | **Exact** | Artiste+titre *normalisés* identiques |
| 2 | **Word coverage** | Tous les mots de la demande sont présents dans la piste |
| 3 | **Composite** | Similarité pondérée : **artiste 30%** + **titre 70%** |
| 4 | **Fuzzy** | Similarité « floue » tolérante à l'ordre et aux variantes |
| 5 | **Title partial** | Similarité partielle sur le titre seul |
| 6 | **Filename** | Comparaison avec le **nom du fichier** (utile si les tags sont vides) |

### La structure « Artiste - Titre »

Si la demande utilise la structure **`Artiste - Titre`** (avec le tiret, ou
`:`, `|`, `/`), le logiciel sépare les deux éléments et les utilise distinctement : il sait
quel est l'artiste et quel est le titre. Cela rend le calcul plus précis (voir le
modèle comptable, §3).

### Qu'est-ce que la « normalisation »

Avant de comparer, les textes sont nettoyés pour que les différences non pertinentes
ne comptent pas :

- tout en **minuscules** ;
- **réparation de l'encodage (mojibake)** : les textes enregistrés avec un double encodage
  UTF-8 sont restaurés, donc `PreparÃ³` est lu comme `Preparó` ;
- **accents** supprimés (`Beyoncé` → `beyonce`, `Preparó` → `preparo`) ;
- **underscores traités comme des espaces** (`Bellini_Music_Official` →
  `bellini music official`) ;
- **ponctuation** convertie en espaces ;
- **contenu entre parenthèses rondes supprimé** aux fins de comparaison — p. ex.
  `Titanium (Extended Mix)` → `titanium` (mais les mots entre parenthèses sont ensuite
  évalués séparément, voir §4) ;
- articles initiaux (`the`, `a`, `an`) et **années à 4 chiffres** supprimés.

Grâce à la réparation mojibake et à la suppression des accents, `Preparó` et
`PreparÃ³` sont considérés comme **le même mot**.

### Tolérance pour textes corrompus (mojibake) + vérification sur le nom de fichier

Parfois un tag est corrompu de façon **non reconstructible** automatiquement (par
exemple `PreparÃ3`, avec un chiffre à la place de l'accent). Dans ces cas, le
logiciel ne compte **pas** immédiatement ce mot comme « différent » : si le **titre
Serato** contient des symboles suspects (`Ã`/`Â`), il effectue une **comparaison sur le nom
de fichier**. Si le mot correct et « propre » est présent dans le filename (p. ex. `preparo`), le
logiciel comprend que le token corrompu est en réalité le même mot et **n'applique
aucune pénalité**. Le nom de fichier sert donc de « source de vérité ».

---

## 3. Les deux régimes de notation

Après avoir choisi le candidat, le logiciel vérifie si **tous les mots du
titre demandé** apparaissent **dans le même ordre** (comme sous-séquence) dans le
**titre Serato** ou dans le **nom de fichier**.

- **Titre entièrement présent** → le **modèle comptable** est utilisé (§4) :
  base **100%** moins des pénalités précises.
- **Titre seulement partiel** → des **seuils stricts** sont utilisés (§5) : le score
  est limité à des valeurs basses (0%, 44% ou 50%).

---

## 4. Le modèle comptable (titre entièrement trouvé)

On part de **100%** et on soustrait les pénalités ci-dessous. **Toutes les pénalités
s'additionnent.**

| Situation | Effet |
|-----------|-------|
| L'**artiste** est dans la demande mais **n'apparaît dans aucune colonne** de la piste trouvée (Artist, Song, Filename) | **plafond 70%** |
| **Mot de TITRE en plus** dans la piste trouvée (mot réel, non demandé, pas de faible pertinence) | **−20% chacun** |
| **Mot d'ARTISTE en plus** dans la piste trouvée (mot réel, non demandé) | **−5% total** |
| **Mot de faible pertinence** hors parenthèses (remix, official, video, music…) non demandé | **−5% total** |
| Tout mot **entre parenthèses rondes** (descripteur ou mot non demandé) | **−1% total** |
| Un mot du **titre demandé** trouvé **uniquement dans le nom de fichier** (pas dans Song ni Artist) | **−1%** |

Notes importantes :

- Un **mot de titre en plus** (p. ex. la demande est *« Everything »* mais la piste
  trouvée est *« Everything **she wants** »*) indique que le titre est en fait différent :
  c'est pourquoi cela pèse lourd (**−20% par mot**).
- Un **mot d'artiste en plus** pèse peu (**−5% total**), car c'est souvent simplement
  le nom de celui qui a mis en ligne la piste ou une variante (p. ex. `ImagineDragons` écrit
  collé, ou une chaîne comme `After Party82`).
- Les mots **entre parenthèses rondes** ont une pertinence encore plus faible : quoi qu'il
  y ait dedans coûte au maximum **−1% total**.
- La vérification de la **présence de l'artiste** est « tolérante » (`ImagineDragons`
  satisfait `imagine`), tandis que le comptage des **mots en plus** est « exact »
  (donc `ImagineDragons` collé compte quand même comme un mot d'artiste en plus).

---

## 5. Seuils stricts (titre seulement partiel)

Lorsque le titre demandé **n'est pas** entièrement présent dans l'ordre, la correspondance est
peu fiable et ces limites s'appliquent :

- **Mots manquants** : si un mot significatif de la demande n'apparaît pas dans la
  piste → **max 50%**.
- **Présence du titre** : si les mots du titre n'apparaissent dans aucun champ →
  **max 45%**.
- **Titre dans l'ordre** : les mots du titre doivent apparaître dans le même ordre
  dans le nom de fichier ou le titre Serato :
  - aucun mot trouvé → **0%** (ligne traitée comme *manquante*) ;
  - trouvés mais partiels / mauvais ordre → **max 44%**.
- **Bonus de containment** : si le titre demandé est néanmoins contenu dans celui
  trouvé, le score monte à au moins **62%**.
- L'**ajustement PSYTRANCE** et la **pénalité BPM** (cette dernière optionnelle) peuvent
  intervenir comme affinements.

---

## 6. Mots de « faible pertinence »

Ce sont des descripteurs de version/format/média qui **ne changent pas vraiment la piste**.
Lorsqu'ils apparaissent dans la piste trouvée mais pas dans la demande, ils ne font pas
s'effondrer le score : ils coûtent seulement **−5% total** (hors parenthèses) ou **−1% total** (s'ils
sont entre parenthèses) :

`remix`, `mashup`, `dub`, `vip`, `flip`, `bootleg`, `rework`, `discomix`,
`mashboot`, `remake`, `revibe`, `reloaded`, `original`, `extended`, `edit`,
`mix`, `version`, `radio`, `club`, `clean`, `dirty`, `official`, `oficial`,
`ufficiale`, `music`, `video`, `audio`, `mv`, `clip`, `lyric`, `lyrics`,
`visualizer`, et sigles de bitrate comme `128kbit_AAC`, `320 kbps`.

---

## 7. Exemples commentés (avec calcul)

Tous les exemples ci-dessous relèvent du **modèle comptable** (le titre
demandé est entièrement présent dans la piste trouvée).

| Demande | Piste trouvée (Song / Artist) | Valeur | Calcul |
|---------|-------------------------------|--------|--------|
| `Michael Bublé - Everything` | *Everything she wants (…Bootleg Remix)* / Wham | **~29%** | Artiste « Michael Bublé » **absent partout** → plafond **70%** ; *« she »* et *« wants »* sont 2 mots de titre en plus → **−40%** (−20% chacun) ; contenu entre parenthèses → **−1%** |
| `Bellini - Carnaval (Original Version)` | *Bellini - Carnaval (Original Version)* / After Party82 | **94%** | Artiste « bellini » présent dans Song ; artiste en plus « After Party82 » → **−5%** ; `(Original Version)` entre parenthèses → **−1%** |
| `Bellini - Samba De Janeiro` | *Bellini - Samba De Janeiro* / Bellini_Music_Official | **95%** | Titre identique ; `music`/`official` sont de faible pertinence hors parenthèses → **−5%** |
| `Imagine Dragons - On Top Of The World` | *…On Top Of The World (Official Music Video)* / ImagineDragons | **94%** | Artiste « ImagineDragons » (collé) compte comme artiste en plus → **−5%** ; `(Official Music Video)` entre parenthèses → **−1%** |
| `KING ÁFRICA "EL CAMALEÓN"` | *KING ÁFRICA "EL CAMALEÓN"* / YouMoreTv - Espectáculo | **95%** | Titre identique ; artiste en plus « YouMoreTv Espectáculo » → **−5%** |
| `Ozuna - Se Preparó (Video Oficial) \| Odisea` | Song : *Ozuna - Se PreparÃ3…* (corrompu) · Filename : *Ozuna - Se Preparó…* (propre) | **99%** | Le titre Serato est corrompu (`PreparÃ3`), mais le mot propre `preparo` est dans le nom de fichier → le token corrompu est reconnu et **non pénalisé** ; il reste seulement `(Video Oficial)` entre parenthèses → **−1%** |
| `Ricky Martin - La Mordidita ft. Yotuel` | *Ricky Martin - La Mordidita* / Ricky Martin | **99%** | Tous les mots du titre sont présents ; *« yotuel »* est présent **uniquement dans le nom de fichier** → **−1%** |

---

## 8. Du score à la couleur et à l'étiquette

Le score final détermine la **couleur** de la ligne et le niveau de confiance :

| Score | Confiance | Couleur de ligne (thème clair) |
|-------|-----------|--------------------------------|
| 95–100% | Exact | vert plein |
| 75–94% | Élevée | vert |
| 55–74% | Moyenne | orange/jaune |
| 1–54% | Faible | rouge clair |
| 0% | Manquant | rose/rouge (traité comme non trouvé) |

Couleurs spéciales :

- **Cyan/bleu clair** : deux lignes ou plus de la playlist pointent vers le **même fichier**
  (doublon possible dans la demande). Si vous changez de version depuis le menu de la colonne
  **Trouvés** et que les doublons disparaissent, la couleur redevient normale.
- **▼ avec numéro** dans la colonne **Trouvés** : il y a plusieurs candidats au-dessus du
  seuil — cliquez pour choisir la bonne version.

---

## 9. Résumé du flux

```
Piste demandée
   │
   ├─ Verrouillée (composer/title lock) ? ── oui ─▶ 100%
   │                                    non
   ▼
Cascade : Exact ▶ Word coverage ▶ Composite ▶ Fuzzy ▶ Title partial ▶ Filename
   │
   ▼
Le titre demandé est-il entièrement présent (dans l'ordre) dans Song ou Filename ?
   │
   ├─ OUI ─▶ Modèle comptable : 100%
   │          − plafond 30% si artiste absent (base descend à 70%)
   │          − 20% pour chaque mot de TITRE en plus
   │          − 5%  s'il y a un mot d'ARTISTE en plus
   │          − 5%  mot de faible pertinence hors parenthèses
   │          − 1%  quelque chose entre parenthèses rondes
   │          − 1%  mot de titre trouvé uniquement dans le nom de fichier
   │
   └─ NON ─▶ Seuils stricts :
              mots manquants → max 50%
              présence du titre → max 45%
              titre dans l'ordre → 0% ou max 44%
              (+ bonus containment, PSYTRANCE, BPM)
   ▼
Score final (0–100%) ▶ couleur + étiquette de confiance
```

---

*Document généré pour Serato Playlist Automation. Les seuils et les listes de
mots se trouvent dans `serato_automation/track_matcher.py`.*
