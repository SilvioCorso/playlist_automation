# Serato Playlist Automation — Guide rapide

*Outil professionnel pour DJ — by SirvioDJ*

---

## À quoi ça sert

Transforme une **playlist client** (texte, fichier, URL YouTube/Spotify) en **crate Serato** prête pour l'événement, en indiquant immédiatement quels morceaux sont dans la bibliothèque et lesquels manquent.

**Gain typique :** des heures de recherche manuelle à quelques minutes de révision guidée.

---

## Parcours en 4 étapes

### ① Configurer la bibliothèque

1. Définir le **dossier musique** (ex. `F:/`)
2. Cliquer **Scanner la bibliothèque** — le premier scan peut prendre quelques minutes ; les suivants utilisent le cache
3. Vérifier le statut vert : *« Bibliothèque : N pistes »*

### ② Charger la playlist client

Onglet **Playlist client** :

- **Importer depuis URL** — YouTube ou Spotify
- **Charger un fichier** — `.txt`, `.csv`, `.m3u`
- Ou **coller les titres** directement

Format recommandé : `Artiste - Titre` (un par ligne).

### ③ Comparer et réviser

**Comparer avec la bibliothèque** → onglet **Résultats** :

| Colonne | Utilité |
|---------|---------|
| **Score %** | Qualité de la correspondance |
| **Trouvé** | Menu avec candidats alternatifs |
| **🔒 Lock** | Verrouille un match à 100 % |
| **Player** | Écouter sans quitter l'app |
| **Cocher** | Sélectionner les pistes pour la crate |

Utilisez **Tout cocher ≥ X %** pour ne sélectionner que les matches au-dessus du seuil.

### ④ Exporter

- **Créer crate Serato** — génère le `.crate` (redémarrer Serato)
- **Enregistrer manquants...** — liste `.txt` des pistes à acheter ou vérifier

---

## Outils avancés

### Maintenance (onglet Édition)

| Fonction | Quand l'utiliser |
|----------|------------------|
| **Nettoyer bibliothèque** | Mots dans les métadonnées ou mojibake (`PreparÃ3`) |
| **Trouver différences** | Pistes sur disque mais pas dans Serato |
| **Doublons** | Même titre+artiste en plusieurs copies |
| **Mettre à jour Serato** | Synchroniser les métadonnées (Serato fermé) |

### Bouton Guide rapide

**Guide rapide** ouvre toujours ce document.

### Algorithme des pourcentages

Le bouton du pied de page explique le calcul du score en détail.

---

## Conseils pro

- **Score ≥ 50 %** comme point de départ ; montez à 70–80 % pour les événements formels
- Utilisez **Lock** sur les matches sûrs avant de changer de candidat
- Lignes **dupliquées** (même fichier) en cyan
- **Plein écran** dans Résultats/Édition pour les longues playlists
- Après **Supprimer** des doublons : fermez puis rouvrez Serato

---

## Support

Feedback et licence Pro : [sirviodj.it](https://sirviodj.it/blog/serato-playlist-automation-risparmia-tempo#formContato)
