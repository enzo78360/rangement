# Rangement

**Ton dossier Téléchargements, enfin rangé.** En une commande, chaque fichier part dans le bon dossier : Images, Vidéos, Audio, Documents, Archives, Installeurs, Code, Polices, Autres.

```
$ python3 rangement.py

38 fichiers à ranger dans /Users/toi/Downloads

  Images       (14)
     IMG_2041.HEIC
     capture.png
     …
  Documents    (9)
  Installeurs  (6)
  …

Ranger maintenant ? [o/N]
```

- **Rien ne bouge sans ton accord** : la liste s'affiche d'abord, tu confirmes ensuite.
- **Annulable** : `python3 rangement.py --annuler` remet chaque fichier exactement à sa place (les 20 derniers rangements sont mémorisés).
- **Prudent** : ne touche ni aux dossiers, ni aux fichiers cachés, ni aux téléchargements en cours (`.crdownload`, `.download`, `.part`…), ni aux fichiers modifiés il y a moins de 2 minutes. Jamais d'écrasement : un doublon devient `photo (2).jpg`.
- **Automatique** si tu veux : `--auto on` range chaque nouveau téléchargement en arrière-plan.
- Fonctionne avec n'importe quel dossier : `--dossier ~/Desktop` pour le Bureau.
- Un seul fichier Python, aucune dépendance.

## Utilisation

```bash
python3 rangement.py                  # aperçu puis confirmation
python3 rangement.py --oui            # sans confirmation
python3 rangement.py --annuler        # annule le dernier rangement
python3 rangement.py --dossier ~/Desktop
python3 rangement.py --auto on        # rangement automatique (--auto off pour arrêter)
```

## Rangement automatique

`--auto on` installe un petit agent `launchd` (`~/Library/LaunchAgents/io.github.enzo78360.rangement.plist`) qui se réveille quand le dossier change, et au moins une fois par heure. Il ne consomme rien le reste du temps.

macOS protège le dossier Téléchargements : si les fichiers ne se rangent pas tout seuls, ajoute `python3` dans *Réglages Système → Confidentialité et sécurité → Accès complet au disque*. Le chemin exact de Python utilisé est la première valeur de `ProgramArguments` dans le fichier `.plist` ci-dessus, et les erreurs éventuelles sont dans `~/Library/Application Support/Rangement/erreurs.log`.

## Licence

MIT
