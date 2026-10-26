#!/usr/bin/env python3
"""Rangement : trie ton dossier Téléchargements en un instant, et peut tout annuler.

Usage :
  python3 rangement.py                 montre ce qui va être rangé puis demande confirmation
  python3 rangement.py --oui           range sans demander
  python3 rangement.py --annuler       remet les fichiers du dernier rangement à leur place
  python3 rangement.py --auto on|off   range automatiquement à chaque nouveau téléchargement
  python3 rangement.py --dossier ~/Bureau   range un autre dossier
"""

import argparse
import json
import os
import plistlib
import subprocess
import sys
import time

CATEGORIES = {
    'Images': 'jpg jpeg png heic heif gif webp tif tiff bmp svg raw cr2 cr3 nef arw dng psd ai ico avif',
    'Vidéos': 'mp4 mov m4v mkv avi webm wmv flv mts 3gp',
    'Audio': 'mp3 wav flac aac m4a aiff aif ogg opus mid midi',
    'Documents': 'pdf doc docx pages odt rtf txt md epub xls xlsx numbers ods csv ppt pptx key odp',
    'Archives': 'zip rar 7z tar gz tgz bz2 xz',
    'Installeurs': 'dmg pkg mpkg xip iso app',
    'Code': 'py js ts html css json xml yml yaml sh swift java c cpp h rb go rs php ipynb sql',
    'Polices': 'ttf otf woff woff2',
}
EXT_CAT = {e: c for c, exts in CATEGORIES.items() for e in exts.split()}
OTHER = 'Autres'
FOLDERS = set(CATEGORIES) | {OTHER}
PARTIAL = {'crdownload', 'download', 'part', 'partial', 'tmp', 'opdownload'}

DATA = os.path.expanduser('~/Library/Application Support/Rangement')
JOURNAL = os.path.join(DATA, 'journal.json')
LABEL = 'io.github.enzo78360.rangement'
AGENT = os.path.expanduser('~/Library/LaunchAgents/%s.plist' % LABEL)

TTY = sys.stdout.isatty()
def color(code, s): return '\033[%sm%s\033[0m' % (code, s) if TTY else s
bold = lambda s: color('1', s)
dim = lambda s: color('2', s)
green = lambda s: color('32', s)
plural = lambda n: 's' if n > 1 else ''


def category(name):
    ext = os.path.splitext(name)[1][1:].lower()
    return EXT_CAT.get(ext, OTHER)


def free_name(folder, name):
    """« photo.jpg » devient « photo (2).jpg » si le nom est déjà pris."""
    base, ext = os.path.splitext(name)
    candidate, n = name, 2
    while os.path.lexists(os.path.join(folder, candidate)):
        candidate = '%s (%d)%s' % (base, n, ext)
        n += 1
    return candidate


def plan(folder, min_age):
    moves = []
    now = time.time()
    for entry in sorted(os.scandir(folder), key=lambda e: e.name.lower()):
        name = entry.name
        if name.startswith('.') or name in FOLDERS:
            continue
        ext = os.path.splitext(name)[1][1:].lower()
        if ext in PARTIAL:
            continue  # téléchargement en cours
        is_app = ext == 'app'
        if entry.is_dir(follow_symlinks=False) and not is_app:
            continue  # on ne touche pas aux dossiers
        try:
            if now - entry.stat(follow_symlinks=False).st_mtime < min_age:
                continue  # trop récent : peut-être encore en cours d'écriture
        except OSError:
            continue
        moves.append((name, category(name)))
    return moves


def load_journal():
    try:
        with open(JOURNAL, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def save_journal(runs):
    os.makedirs(DATA, exist_ok=True)
    with open(JOURNAL, 'w', encoding='utf-8') as f:
        json.dump(runs[-20:], f, ensure_ascii=False, indent=1)


def tidy(folder, yes, quiet, min_age):
    moves = plan(folder, min_age)
    if not moves:
        if not quiet:
            print(green('✓ Rien à ranger, tout est déjà en ordre.'))
        return
    if not quiet:
        by_cat = {}
        for name, cat in moves:
            by_cat.setdefault(cat, []).append(name)
        print(bold('%d fichier%s à ranger dans %s\n' % (len(moves), plural(len(moves)), folder)))
        for cat in sorted(by_cat, key=lambda c: -len(by_cat[c])):
            names = by_cat[cat]
            print('  %s %s' % (bold(cat.ljust(12)), dim('(%d)' % len(names))))
            for n in names[:4]:
                print('     ' + n)
            if len(names) > 4:
                print(dim('     … et %d autres' % (len(names) - 4)))
        print()
    if not yes:
        try:
            if input('Ranger maintenant ? [o/N] ').strip().lower() not in ('o', 'oui', 'y', 'yes'):
                print('Rien n\'a été déplacé.')
                return
        except EOFError:
            return

    done = []
    for name, cat in moves:
        dest_dir = os.path.join(folder, cat)
        os.makedirs(dest_dir, exist_ok=True)
        src = os.path.join(folder, name)
        dst = os.path.join(dest_dir, free_name(dest_dir, name))
        try:
            os.rename(src, dst)
            done.append([src, dst])
        except OSError as err:
            print('⚠️  %s : %s' % (name, err.strerror), file=sys.stderr)
    if done:
        runs = load_journal()
        runs.append({'date': time.strftime('%Y-%m-%d %H:%M:%S'), 'moves': done})
        save_journal(runs)
    if not quiet:
        n = len(done)
        print(green('✓ %d fichier%s rangé%s.' % (n, plural(n), plural(n))))
        print(dim('  Changé d\'avis ? python3 rangement.py --annuler'))


def undo():
    runs = load_journal()
    if not runs:
        print('Aucun rangement à annuler.')
        return
    run = runs.pop()
    restored = skipped = 0
    for src, dst in reversed(run['moves']):
        if os.path.lexists(dst) and not os.path.lexists(src):
            os.rename(dst, src)
            restored += 1
        else:
            skipped += 1
    # Supprime les dossiers de catégorie devenus vides.
    for folder in {os.path.dirname(d) for _, d in run['moves']}:
        try:
            os.rmdir(folder)
        except OSError:
            pass
    save_journal(runs)
    print(green('✓ %d fichier%s remis en place' % (restored, plural(restored)))
          + (' (%d déjà déplacé%s ou supprimé%s depuis)' % (skipped, plural(skipped), plural(skipped)) if skipped else '')
          + dim(' — rangement du %s annulé.' % run['date']))


def auto(state, folder):
    if state == 'off':
        if os.path.exists(AGENT):
            subprocess.run(['launchctl', 'unload', AGENT], capture_output=True)
            os.remove(AGENT)
        print(green('✓ Rangement automatique désactivé.'))
        return
    os.makedirs(os.path.dirname(AGENT), exist_ok=True)
    os.makedirs(DATA, exist_ok=True)
    agent = {
        'Label': LABEL,
        'ProgramArguments': [sys.executable, os.path.abspath(__file__), '--oui', '--silencieux', '--dossier', folder],
        'WatchPaths': [folder],          # à chaque changement dans le dossier…
        'StartInterval': 3600,           # …et au moins une fois par heure
        'ThrottleInterval': 30,
        'StandardErrorPath': os.path.join(DATA, 'erreurs.log'),
    }
    with open(AGENT, 'wb') as f:
        plistlib.dump(agent, f)
    subprocess.run(['launchctl', 'unload', AGENT], capture_output=True)
    subprocess.run(['launchctl', 'load', AGENT], check=True)
    print(green('✓ Rangement automatique activé pour %s.' % folder))
    print(dim('  Les nouveaux fichiers seront rangés environ 2 minutes après la fin du téléchargement.'))
    print(dim('  Si rien ne se passe, voir « Rangement automatique » dans le README (autorisation macOS).'))


def main():
    ap = argparse.ArgumentParser(description='Range ton dossier Téléchargements par type de fichier.')
    ap.add_argument('--dossier', default='~/Downloads', help='dossier à ranger (par défaut : Téléchargements)')
    ap.add_argument('--oui', action='store_true', help='ranger sans demander confirmation')
    ap.add_argument('--annuler', action='store_true', help='annuler le dernier rangement')
    ap.add_argument('--auto', choices=('on', 'off'), help='rangement automatique en arrière-plan')
    ap.add_argument('--age', type=int, default=120, help='âge minimum des fichiers en secondes (par défaut : 120)')
    ap.add_argument('--silencieux', action='store_true', help=argparse.SUPPRESS)
    args = ap.parse_args()

    folder = os.path.realpath(os.path.expanduser(args.dossier))
    if args.annuler:
        return undo()
    if args.auto:
        return auto(args.auto, folder)
    if not os.path.isdir(folder):
        sys.exit('Dossier introuvable : %s' % folder)
    try:
        tidy(folder, args.oui, args.silencieux, args.age)
    except PermissionError:
        sys.exit("macOS refuse l'accès à %s. Autorise le Terminal dans Réglages Système → "
                 "Confidentialité et sécurité → Fichiers et dossiers." % folder)


if __name__ == '__main__':
    main()
