"""Langue de l'appli : français (textes du code) ou anglais (traductions ci-dessous).

T("texte français {x}", x=…) -> le texte dans la langue choisie, avec les valeurs mises dedans.
Un texte sans traduction reste en français (jamais de plantage).
Langue choisie dans ⚙ > Language / Langue ; « auto » = celle de Windows (français -> fr, sinon en).
"""
import locale
import os

LANG = "fr"
THOUSANDS, DECIMAL = " ", ","


def detect():
    """Langue de Windows (ou du système) : « fr » si français, sinon « en »."""
    try:
        if os.name == "nt":
            import ctypes
            lid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return "fr" if (lid & 0x3FF) == 0x0C else "en"       # 0x0C = français (France, Belgique, Canada, Suisse…)
    except Exception:
        pass
    try:
        loc = locale.getlocale()[0] or os.environ.get("LANG", "")
    except Exception:
        loc = os.environ.get("LANG", "")
    return "fr" if (loc or "").lower().startswith("fr") else "en"


def set_lang(code):
    global LANG, THOUSANDS, DECIMAL
    LANG = code if code in ("fr", "en") else detect()
    THOUSANDS, DECIMAL = (",", ".") if LANG == "en" else (" ", ",")
    return LANG


def T(text, **kw):
    out = EN.get(text, text) if LANG == "en" else text
    if kw:
        try:
            out = out.format(**kw)
        except (KeyError, IndexError, ValueError):
            out = text.format(**kw)
    return out


EN = {
    # ------------------------------------------------------------ noms courts
    "Sans médaille": "No medal", "Bronze": "Bronze", "Argent": "Silver", "Or": "Gold", "Diamant": "Diamond",
    "Great One": "Great One",
    "Automne (orange)": "Autumn (orange)", "Forêt (vert)": "Forest (green)", "Glace (bleu)": "Ice (blue)",
    "Sang (rouge)": "Blood (red)",
    "Fenêtre": "Window", "TikTok": "TikTok", "Stream": "Stream",
    "En bas de l'écran": "Bottom of the screen",
    "En haut de l'écran (l'heure du jeu reste visible, encadrée)": "Top of the screen (the game clock stays visible, framed)",
    "En haut, sous la barre du jeu (heure du jeu visible)": "Top, under the game's top bar (game clock visible)",
    "Pleine (on ne voit pas le jeu)": "Solid (the game is hidden)", "80 %": "80%", "60 % (conseillé)": "60% (recommended)",
    "40 %": "40%", "25 % (très transparente)": "25% (very see-through)",
    "Petite": "Small", "Moyenne": "Medium", "Grande": "Large",
    "Toutes les réserves": "All reserves",
    "Kills déjà faits": "Kills already done", "Great Ones déjà eus": "Great Ones already got",
    "lié à Kill_Farm (profil « {x} »)": "linked to Kill_Farm (profile \"{x}\")",

    # ------------------------------------------------------------ fenêtre principale
    "Recherche de ta sauvegarde…": "Looking for your game save…",
    "Sauvegarde trouvée ✓ · le compteur suit tes bêtes ramassées": "Save found ✓ · the counter follows your harvested animals",
    "Pas de sauvegarde : compteur à la main seulement (⚙ > Dossier de sauvegarde)":
        "No save found: manual counter only (⚙ > Game save folder)",
    "Raccourci déjà pris par une autre appli : {name}": "Hotkey already used by another app: {name}",
    "Bête inconnue": "Unknown animal",
    "Dernière bête ramassée : {name} · {grade} · {when}": "Last harvested animal: {name} · {grade} · {when}",
    "Bête ramassée non reconnue : lance son farm, la prochaine sera demandée.":
        "Harvested animal not recognized: start its farm, the next one will be asked.",
    "réserve inconnue": "unknown reserve",
    "Tu viens de ramasser une bête que je ne reconnais pas ({res}, {grade}).":
        "You just harvested an animal I don't recognize ({res}, {grade}).",
    "C'était laquelle ? Elle sera comptée, et je m'en souviendrai pour les prochaines.":
        "Which one was it? It will be counted, and I'll remember it for the next ones.",
    "Retenu : cette bête = {name}. Les prochaines seront comptées toutes seules.":
        "Got it: this animal = {name}. The next ones will be counted automatically.",
    "Aucune de mes bêtes de farm (ne rien compter)": "None of my farm animals (don't count anything)",
    "Great One retiré : les chiffres sont revenus comme avant.": "Great One removed: the numbers are back to how they were.",
    "Dernier kill retiré du farm.": "Last kill removed from the farm.",
    "Rien à annuler.": "Nothing to undo.",
    "🏆 Mon dernier kill était un Great One": "🏆 My last kill was a Great One",
    "🏆 Mon dernier kill était un Great One…": "🏆 My last kill was a Great One…",
    "Aucun kill compté depuis le dernier Great One.\n\n"
    "Ton Great One n'a pas été compté du tout ? Clique d'abord sur « +1 », puis reviens ici.":
        "No kill counted since the last Great One.\n\n"
        "Your Great One wasn't counted at all? Click \"+1\" first, then come back here.",
    "Ton dernier kill ({name}) était un Great One ?\n\n"
    "• Great Ones : {a} → {b}\n"
    "• Dernier GO tombé en {k}\n"
    "• Le compteur depuis le dernier GO repart de 0\n\n"
    "(Erreur ? « ↶ Annuler le dernier kill » remet tout comme avant.)":
        "Was your last kill ({name}) a Great One?\n\n"
        "• Great Ones: {a} → {b}\n"
        "• Last GO took {k}\n"
        "• The counter since the last GO goes back to 0\n\n"
        "(Mistake? \"↶ Undo last kill\" puts everything back.)",
    "Great One ajouté. Félicitations ! 🏆": "Great One added. Congratulations! 🏆",
    "▶ Lancer un nouveau farm…": "▶ Start a new farm…",
    "✎ Modifier les chiffres du farm…": "✎ Edit the farm numbers…",
    "✕ Supprimer ce farm…": "✕ Delete this farm…",
    "Kills depuis le dernier Great One": "Kills since the last Great One",
    "Total du farm": "Farm total",
    "Grand chiffre": "Big number",
    "Taille de la carte TikTok": "TikTok card size",
    "Position de la barre Stream": "Stream bar position",
    "Transparence de la barre Stream": "Stream bar transparency",
    "🎨 Couleur": "🎨 Color",
    "Barre Stream : la souris passe à travers (touche ²)": "Stream bar: mouse clicks go through (` key)",
    "Dossier de sauvegarde du jeu…": "Game save folder…",
    "Créer un raccourci sur le Bureau": "Create a desktop shortcut",
    "Ouvrir le dossier de mes farms": "Open my farms folder",
    "🎓 Tutoriel : apprendre l'appli": "🎓 Tutorial: learn the app",
    "📰 Nouveautés de la version": "📰 What's new in this version",
    "Aide": "Help",
    "💬 Discord : mises à jour et aide": "💬 Discord: updates and help",
    "⇄ Passer à Kill_Farm (l'appli complète)": "⇄ Switch to Kill_Farm (the full app)",
    "Quitter": "Quit",
    "Langue : Français": "Language: English",
    "Couleur de la barre : {x}": "Bar color: {x}",
    "Barre Stream : couleur {x} %": "Stream bar: color {x}%",
    "Couleur : {x}": "Color: {x}",
    "{app} · Mise à jour {v}": "{app} · Update {v}",
    "MISE À JOUR": "UPDATE",
    "Tes réglages sont gardés : affichage au démarrage, couleur, position de la barre, raccourcis, farms et chiffres.":
        "Your settings are kept: startup display, color, bar position, hotkeys, farms and numbers.",
    "C'est parti !": "Let's go!",
    "Farms {x} : mêmes farms, mêmes chiffres dans les 2 applis.\n\n":
        "Farms {x}: same farms, same numbers in both apps.\n\n",
    "Tes farms : {x}\n": "Your farms: {x}\n",
    "Mises à jour et aide : Discord {x}\n": "Updates and help: Discord {x}\n",
    "\n\n(Il sera aussi supprimé dans Kill_Farm : les 2 applis ont les mêmes farms.)":
        "\n\n(It will also be deleted in Kill_Farm: both apps share the same farms.)",
    "Supprimer le farm « {name} · {res} » et ses {k} ?": "Delete the farm \"{name} · {res}\" and its {k}?",
    "Barre Stream BLOQUÉE : la souris passe à travers (² pour débloquer)":
        "Stream bar LOCKED: mouse clicks go through (` to unlock)",
    "Barre Stream DÉBLOQUÉE : clic droit = menu (² pour bloquer)": "Stream bar UNLOCKED: right-click = menu (` to lock)",
    "BLOQUÉ · la souris passe à travers": "LOCKED · mouse clicks go through",
    "DÉBLOQUÉ · clic droit = menu": "UNLOCKED · right-click = menu",
    "Affichage {x}": "{x} display",
    "↶ Annuler le dernier kill": "↶ Undo last kill",
    "Position de la barre": "Bar position",
    "Transparence de la barre": "Bar transparency",
    "📺 Barre Stream visible dans TikTok LIVE Studio (opaque)": "📺 Stream bar visible in TikTok LIVE Studio (opaque)",
    "📺 Barre visible dans TikTok LIVE Studio (opaque)": "📺 Bar visible in TikTok LIVE Studio (opaque)",
    "Barre Stream opaque : dans TikTok LIVE Studio, Capture de fenêtre > « KillFarm Lite – Stream »": "Opaque Stream bar: in TikTok LIVE Studio, Window capture > \"KillFarm Lite – Stream\"",
    "Barre Stream transparente": "See-through Stream bar",
    "📺 Fenêtre Live pour TikTok LIVE Studio": "📺 Live window for TikTok LIVE Studio",
    "Barre Stream opaque (sans transparence)": "Opaque Stream bar (no transparency)",
    "Fenêtre Live ouverte : dans TikTok LIVE Studio, Capture de fenêtre > « KillFarm Lite – Live »": "Live window open: in TikTok LIVE Studio, Window capture > \"KillFarm Lite – Live\"",
    "Fenêtre Live fermée": "Live window closed",
    "🌐 Lien de la barre (TikTok LIVE Studio / OBS)…": "🌐 Bar link (TikTok LIVE Studio / OBS)…",
    "Impossible de lancer la barre web (ports 8777 à 8797 déjà pris).": "Can't start the web bar (ports 8777 to 8797 already in use).",
    " · aucun farm lancé": " · no farm started",
    "🔘 Bulle menu rapide (bord de l'écran)": "🔘 Quick-menu bubble (screen edge)",
    "Bulle affichée : clic = menu rapide, glisse-la pour la déplacer": "Bubble shown: click = quick menu, drag it to move",
    "Bulle cachée (⚙ pour la remettre)": "Bubble hidden (⚙ to bring it back)",
    "   {a} depuis le dernier GO · total {b}": "   {a} since the last GO · total {b}",
    "Aucun farm lancé": "No farm started",
    "⇄ Changer de farm": "⇄ Switch farm",
    "Affichage": "Display",
    "Ouvrir la fenêtre KillFarm": "Open the KillFarm window",
    "Mettre la bulle à gauche": "Move the bubble to the left",
    "Mettre la bulle à droite": "Move the bubble to the right",
    "Cacher la bulle": "Hide the bubble",
    "📌 Mini menu au bord de l'écran": "📌 Mini menu on the screen edge",
    "Logo au bord de l'écran : clic = mini menu": "Logo on the screen edge: click = mini menu",
    "Mini menu enlevé (⚙ pour le remettre)": "Mini menu removed (⚙ to bring it back)",
    "↶ Annuler": "↶ Undo",
    "⇄ Farm ▾": "⇄ Farm ▾",
    "▶ Nouveau": "▶ New",
    "👁 Affichage ▾": "👁 Display ▾",
    "🌐 Lien barre": "🌐 Bar link",
    "🪟 Fenêtre": "🪟 Window",
    "— Réduire": "— Minimize",
    "Cacher / montrer (F8)": "Hide / show (F8)",
    "▶ Nouveau pour commencer": "▶ New to start",
    "kills depuis": "kills since",
    "le dernier GO": "the last GO",
    "Dernier GO : {x}": "Last GO: {x}",
    "Total : {x}": "Total: {x}",
    "Ouvrir le mini menu": "Open the mini menu",
    "Mettre à gauche": "Move to the left",
    "Mettre à droite": "Move to the right",
    "Enlever le mini menu": "Remove the mini menu",
    'KILLFARM · FARM EN COURS': 'KILLFARM · CURRENT FARM',
    '{n} Great One': '{n} Great One',
    '{n} Great Ones': '{n} Great Ones',
    'DERNIER GO': 'LAST GO',
    'En bas, au centre (conseillé)': 'Bottom, centered (recommended)',
    'En haut, au centre': 'Top, centered',
    'En haut, sous la barre du jeu': 'Top, under the game bar',
    '+1  KILL': '+1  KILL',
    'Annuler': 'Undo',
    'Changer de farm ▾': 'Switch farm ▾',
    'Nouveau farm': 'New farm',
    'Affichage ▾': 'Display ▾',
    'Lien du live': 'Live link',
    'Grande fenêtre': 'Big window',
    '« Nouveau farm » pour commencer': '"New farm" to start',
    'FARM': 'FARM',
    'TOTAL': 'TOTAL',
    'Couleur': 'Color',
    "Mini menu au bord de l'écran": 'Mini menu on the screen edge',
    'Lien de la barre pour le live (TikTok LIVE Studio / OBS)…': 'Bar link for the live (TikTok LIVE Studio / OBS)…',
    'Position de la barre': 'Bar position',
    'Transparence de la barre': 'Bar transparency',
    'Barre opaque (sans transparence)': 'Opaque bar (no transparency)',
    'La souris passe à travers la barre (touche ²)': 'Mouse goes through the bar (key under Esc)',
    'Fenêtre Live (capture de fenêtre)': 'Live window (window capture)',
    'Barre Stream & live': 'Stream bar & live',
    'Sauvegarde & fichiers': 'Save & files',
    "Tutoriel : apprendre l'appli": 'Tutorial: learn the app',
    'Nouveautés de la version': "What's new",
    'Discord : mises à jour et aide': 'Discord: updates and help',
    'Aide & réseaux': 'Help & socials',
    'Bienvenue dans KillFarm Lite': 'Welcome to KillFarm Lite',
    "L'appli compte toute seule les bêtes que tu RAMASSES dans theHunter, avec leur grade.\n\nElle lit seulement ta sauvegarde : elle ne touche jamais au jeu.\n\nCe tuto te montre tout en 1 minute.": 'The app counts by itself every animal you HARVEST in theHunter, with its grade.\n\nIt only reads your save: it never touches the game.\n\nThis tutorial shows you everything in 1 minute.',
    '1. Lancer un farm': '1. Start a farm',
    "Clique ici, choisis la réserve (celle où tu joues est déjà choisie), puis l'animal. C'est tout !\n\nFarm déjà commencé ? Mets tes chiffres au départ. Plus rapide : quand tu ramasses une bête sans farm, un bandeau « Farmer celle-là » apparaît.": 'Click here, pick the reserve (the one you\'re playing is already selected), then the animal. That\'s it!\n\nFarm already started? Enter your numbers at the start. Faster: when you harvest an animal with no farm, a "Farm this one" banner shows up.',
    '2. Ton compteur': '2. Your counter',
    'Le grand chiffre = tes kills depuis le dernier Great One (ou le total du farm : au choix dans ⚙ > Affichage).\n\nÀ droite : le total du farm et tes Great Ones. En haut : en combien de kills est tombé ton dernier GO.': 'The big number = your kills since the last Great One (or the farm total: choose in ⚙ > Display).\n\nOn the right: the farm total and your Great Ones. At the top: how many kills your last GO took.',
    '3. Les grades et le Great One': '3. Grades and the Great One',
    "Chaque bête ramassée est rangée selon sa médaille : sans médaille, bronze, argent, or, diamant, Great One.\n\nQuand ton Great One tombe, le compteur repart de 0 tout seul et « GREAT ONE ! » s'affiche. Pas reconnu ? Clic droit > « Mon dernier kill était un Great One ». Clic droit sur un badge = +1 / −1.": 'Every harvested animal is sorted by its medal: no medal, bronze, silver, gold, diamond, Great One.\n\nWhen your Great One drops, the counter goes back to 0 by itself and "GREAT ONE!" shows up. Not detected? Right-click > "My last kill was a Great One". Right-click a badge = +1 / −1.',
    '4. Corriger': '4. Fix the numbers',
    '« −1 / +1 » pour ajuster le compteur.\n« Annuler le dernier kill » si une bête a été comptée par erreur.': '"−1 / +1" to adjust the counter.\n"Undo the last kill" if an animal was counted by mistake.',
    '5. Mes farms': '5. My farms',
    "Tous tes farms : passe de l'un à l'autre, modifie les chiffres ou supprime un farm.\n\nTous tes farms comptent en même temps.": 'All your farms: switch between them, edit the numbers or delete a farm.\n\nAll your farms count at the same time.',
    '6. Les affichages': '6. Displays',
    "Fenêtre = ce panneau.\nTikTok = une carte à glisser où tu veux, pour tes vidéos.\nStream = un tableau en bas au centre de l'écran : bête, kills du farm, dernier GO, total, grades.\n\nF7 = changer d'affichage, F8 = cacher / montrer, ² (sous Échap) = la souris passe à travers le tableau ou non.": 'Window = this panel.\nTikTok = a card to drag anywhere, for your videos.\nStream = a board at the bottom center of the screen: animal, farm kills, last GO, total, grades.\n\nF7 = switch display, F8 = hide / show, key under Esc = mouse goes through the board or not.',
    '7. Le mini menu': '7. The mini menu',
    "Ton logo reste collé au bord droit de l'écran, par-dessus le jeu. Glisse-le : il se colle au bord le plus proche.\n\nUn clic dessus : le mini menu sort (+1 KILL, Annuler, Great One, Changer de farm) et cette grande fenêtre se range. « Grande fenêtre » la rouvre.": 'Your logo stays docked on the right edge of the screen, over the game. Drag it: it sticks to the nearest edge.\n\nClick it: the mini menu slides out (+1 KILL, Undo, Great One, Switch farm) and this big window hides. "Big window" brings it back.',
    '8. Ta barre sur ton live': '8. Your bar on your live',
    "Mini menu > « Lien du live » : l'adresse est copiée.\n\nTikTok LIVE Studio : Ajouter une source > Lien > colle > résolution 1120 x 124.\nOBS : source Navigateur, 1120 x 124.\n\nLes chiffres bougent en direct pendant ton live. Garde l'appli ouverte.": 'Mini menu > "Live link": the address is copied.\n\nTikTok LIVE Studio: Add source > Link > paste > resolution 1120 x 124.\nOBS: Browser source, 1120 x 124.\n\nThe numbers move live during your stream. Keep the app open.',
    '9. Réglages': '9. Settings',
    '⚙ en 4 parties : Affichage (7 couleurs dont TikTok, Twitch, YouTube, écran, langue), Barre Stream & live, Sauvegarde & fichiers, Aide & réseaux (ce tuto, Discord).\n\nClic droit sur le tableau, la carte ou le logo = le même menu rapide.': '⚙ in 4 parts: Display (7 colors incl. TikTok, Twitch, YouTube, screen, language), Stream bar & live, Save & files, Help & socials (this tutorial, Discord).\n\nRight-click the board, the card or the logo = the same quick menu.',
    'Dernier conseil': 'Last tip',
    'Mets le jeu en « Fenêtré sans bordure » (Options > Affichage) : en « Plein écran », Windows cache le tableau et le mini menu derrière le jeu.\n\nBonne chasse !': 'Set the game to "Borderless window" (Options > Display): in "Fullscreen", Windows hides the board and the mini menu behind the game.\n\nHappy hunting!',
    "Barre, carte et mini menu sur l'écran {n}": 'Bar, card and mini menu on screen {n}',
    'Écran {n}': 'Screen {n}',
    ' (principal)': ' (main)',
    'Écran (barre, carte, mini menu)': 'Screen (bar, card, mini menu)',
    'Écran': 'Screen',
    '  {a} depuis le dernier GO  ·  total {b}': '  {a} since the last GO  ·  total {b}',
    '+1 kill': '+1 kill',
    'Annuler le dernier kill': 'Undo the last kill',
    'Mon dernier kill était un Great One': 'My last kill was a Great One',
    'Changer de farm': 'Switch farm',
    'Bloquer / débloquer la barre (²)': 'Lock / unlock the bar (key under Esc)',
    'Lien de la barre pour le live…': 'Bar link for the live…',
    'Réduire le mini menu': 'Minimize the mini menu',
    'Cacher (F8)': 'Hide (F8)',
    'Pleine (conseillé : textes bien nets)': 'Full (recommended: sharp text)',
    '60 %': '60 %',
    '🏆 GREAT ONE ! Compteur remis à 0.': '🏆 GREAT ONE! Counter reset to 0.',
    'Barre pour ton live': 'Bar for your live',
    'BARRE POUR TON LIVE': 'BAR FOR YOUR LIVE',
    'Ton adresse (elle ne marche que sur ce PC) :': 'Your address (works on this PC only):',
    '✓ {x} copiée': '✓ {x} copied',
    'Copier': 'Copy',
    'Adresse': 'Address',
    'TikTok LIVE Studio': 'TikTok LIVE Studio',
    "Ajouter une source  ›  Lien  ›  colle l'adresse  ›  1120 x 124": 'Add source  ›  Link  ›  paste the address  ›  1120 x 124',
    "Sources  ›  +  ›  Navigateur  ›  colle l'adresse  ›  1120 x 124": 'Sources  ›  +  ›  Browser  ›  paste the address  ›  1120 x 124',
    'Fond transparent :': 'See-through background:',
    "Copier l'adresse sans fond": 'Copy the no-background address',
    'Adresse sans fond': 'No-background address',
    "Voir l'aperçu": 'Preview',
    'Garde KillFarm ouvert pendant le live.': 'Keep KillFarm open during the live.',
    'TikTok (rose et cyan)': 'TikTok (pink & cyan)',
    'Twitch (violet)': 'Twitch (purple)',
    'YouTube (rouge)': 'YouTube (red)',
    'Quitter KillFarm': 'Quit KillFarm',
    "Adresse de la barre (déjà copiée) :\n{u}\n\nTikTok LIVE Studio : Ajouter une source > Lien > colle l'adresse, résolution personnalisée 1120 x 124.\nOBS : Sources > + > Navigateur > colle l'adresse, largeur 1120, hauteur 124.\n\nFond transparent : ajoute ?fond=0 à la fin de l'adresse (?fond=0.6 = 60 %).\nGarde KillFarm Lite ouvert pendant le live.": "Bar address (already copied):\n{u}\n\nTikTok LIVE Studio: Add source > Link > paste the address, custom resolution 1120 x 124.\nOBS: Sources > + > Browser > paste the address, width 1120, height 124.\n\nSee-through background: add ?fond=0 at the end of the address (?fond=0.6 = 60 %).\nKeep KillFarm Lite open during the live.",
    "Bloquer la barre : la souris passe à travers (²)": "Lock the bar: mouse clicks go through (`)",
    "Cacher (F8)": "Hide (F8)",
    "⇄ Passer à Kill_Farm (complète)": "⇄ Switch to Kill_Farm (full)",
    "Quitter KillFarm Lite": "Quit KillFarm Lite",
    "kills du farm · depuis le GO": "farm kills · since the GO",
    "total du farm": "farm total",
    "Farmer celle-là": "Farm this one",
    "▶ Lancer un farm": "▶ Start a farm",
    "▶ Nouveau farm": "▶ New farm",
    "☰ Mes farms": "☰ My farms",
    "Affichage :": "Display:",
    "F7 = affichage · F8 = cacher · ² = bloquer / débloquer la barre Stream":
        "F7 = display · F8 = hide · ` = lock / unlock the Stream bar",
    "Aucun farm lancé": "No farm started",
    "Clique sur « ▶ Lancer un farm » :\nchoisis la réserve et l'animal.\nChaque bête ramassée sera\ncomptée toute seule.":
        "Click \"▶ Start a farm\":\npick the reserve and the animal.\nEvery animal you harvest will\nbe counted automatically.",
    "Dernier GO tombé en {x}": "Last GO took {x}",
    "— (pas encore de GO)": "— (no GO yet)",
    "Depuis le dernier GO": "Since the last GO",
    "Tu viens de ramasser": "You just harvested",
    "Ta dernière bête ramassée": "Your last harvested animal",
    "{head} : {name} ({res}).\nLancer un farm de cette bête ?": "{head}: {name} ({res}).\nStart a farm of this animal?",
    "Aucun farm\n\nClic droit >\n▶ Lancer un nouveau farm": "No farm\n\nRight-click >\n▶ Start a new farm",
    "Total du farm {n} · {go} GO": "Farm total {n} · {go} GO",
    "{n} depuis le dernier GO · {go} GO": "{n} since the last GO · {go} GO",
    " · aucun farm lancé (clic droit > ▶ Lancer un nouveau farm)": " · no farm started (right-click > ▶ Start a new farm)",
    "KILLS DU FARM": "FARM KILLS", "FARM": "FARM",
    "KILLS POUR LE DERNIER GO": "KILLS FOR THE LAST GO", "DERNIER GO": "LAST GO",
    "TOTAL DU FARM": "FARM TOTAL", "TOTAL": "TOTAL",

    # ------------------------------------------------------------ messages
    "Raccourci « KillFarm Lite » créé sur ton Bureau.": "\"KillFarm Lite\" shortcut created on your desktop.",
    "Je n'ai pas pu créer le raccourci. Lance l'appli en double-cliquant sur « KillFarm Lite.exe ».":
        "I couldn't create the shortcut. Start the app by double-clicking \"KillFarm Lite.exe\".",
    "Je ne trouve pas la sauvegarde de theHunter: Call of the Wild.\n\n"
    "Choisis le dossier :  Documents > Avalanche Studios > COTW > Saves > (ton numéro Steam).\n\n"
    "Astuce : lance le jeu une fois avant, pour que la sauvegarde existe.":
        "I can't find your theHunter: Call of the Wild save.\n\n"
        "Pick the folder:  Documents > Avalanche Studios > COTW > Saves > (your Steam number).\n\n"
        "Tip: start the game once first, so the save exists.",
    "Dossier Saves\\(numéro Steam) de theHunter": "theHunter Saves\\(Steam number) folder",
    "Ce dossier ne ressemble pas à une sauvegarde du jeu (pas de fichier hunting_log_adf).\nLe garder quand même ?":
        "This folder doesn't look like a game save (no hunting_log_adf file).\nKeep it anyway?",
    "C'est noté. Relance KillFarm Lite pour lire cette sauvegarde.": "Done. Restart KillFarm Lite to read this save.",
    "Je n'ai pas pu ouvrir Kill_Farm.": "I couldn't open Kill_Farm.",
    "Créer un raccourci « KillFarm Lite » (avec le logo) sur ton Bureau ?\n\n"
    "Tu pourras lancer l'appli en double-cliquant dessus.":
        "Create a \"KillFarm Lite\" shortcut (with the logo) on your desktop?\n\n"
        "You'll be able to start the app by double-clicking it.",

    # ------------------------------------------------------------ aide
    "LANCER UN FARM\n"
    "« ▶ Lancer un farm » : choisis la réserve et l'animal (ou « Farmer celle-là » pour ta dernière bête).\n"
    "Joue : chaque bête RAMASSÉE de ton farm est comptée toute seule, avec son grade. "
    "L'appli lit la sauvegarde du jeu, elle ne la modifie jamais.\n\n"
    "AFFICHAGES  (F7 = changer, F8 = cacher / montrer)\n"
    "• Fenêtre : le compteur complet.\n"
    "• TikTok : une carte à glisser où tu veux à la souris ; clic droit = menu.\n"
    "• Stream : une barre en bas ou en haut de l'écran, on voit le jeu à travers. La souris passe à travers : "
    "touche ² (sous Échap) pour la débloquer, puis clic droit = menu.\n\n"
    "CORRIGER\n"
    "• −1 / +1, « Annuler le dernier kill ».\n"
    "• Clic droit sur un badge de grade : +1 / −1.\n"
    "• Great One pas reconnu : ☰ Mes farms > « Mon dernier kill était un Great One ».\n"
    "• Bête pas reconnue : l'appli te demande laquelle c'était et s'en souvient.\n\n"
    "IMPORTANT\n"
    "Mets le jeu en « Fenêtré sans bordure » (Options > Affichage) : en « Plein écran », la carte et la barre "
    "sont cachées.\n\n":
        "START A FARM\n"
        "\"▶ Start a farm\": pick the reserve and the animal (or \"Farm this one\" for your last animal).\n"
        "Play: every animal of your farm that you HARVEST is counted automatically, with its grade. "
        "The app only reads the game save, it never changes it.\n\n"
        "DISPLAYS  (F7 = switch, F8 = hide / show)\n"
        "• Window: the full counter.\n"
        "• TikTok: a card you drag anywhere with the mouse; right-click = menu.\n"
        "• Stream: a bar at the bottom or top of the screen, see-through. Mouse clicks go through it: "
        "press the ` key (under Esc) to unlock it, then right-click = menu.\n\n"
        "FIX THE NUMBERS\n"
        "• −1 / +1, \"Undo last kill\".\n"
        "• Right-click a grade badge: +1 / −1.\n"
        "• Great One not detected: ☰ My farms > \"My last kill was a Great One\".\n"
        "• Animal not recognized: the app asks you which one it was and remembers it.\n\n"
        "IMPORTANT\n"
        "Set the game to \"Borderless window\" (Options > Display): in \"Fullscreen\", the card and the bar "
        "are hidden.\n\n",

    # ------------------------------------------------------------ nouveautés
    "English / Français": "English / Français",
    "L'appli parle maintenant anglais : ⚙ > Language / Langue. Au premier lancement, "
    "elle prend toute seule la langue de ton Windows. Tes farms sont gardés.":
        "The app now speaks English: ⚙ > Language / Langue. On first start it picks your Windows language "
        "automatically. Your farms are kept.",
    "Touche sous Échap": "Key under Esc",
    "La touche ² marche maintenant sur tous les claviers (c'est la touche ` sur un clavier anglais).":
        "The lock key now works on every keyboard: it's the key under Esc (` on a US / UK keyboard).",
    "Great One pas reconnu ?": "Great One not detected?",
    "☰ Mes farms > « Mon dernier kill était un Great One » (ou clic droit sur le badge Great One) : "
    "le GO est compté et le compteur repart de 0.":
        "☰ My farms > \"My last kill was a Great One\" (or right-click the Great One badge): "
        "the GO is counted and the counter starts again from 0.",
    "Discord et TikTok": "Discord and TikTok",
    "⚙ > Discord : les mises à jour et l'aide. Ton pseudo TikTok est sur la carte.":
        "⚙ > Discord: updates and help. The TikTok handle is on the card.",
    "Toujours là": "Still here",
    "Barre Stream transparente, carte TikTok à glisser, bête inconnue demandée et retenue.":
        "See-through Stream bar, draggable TikTok card, unknown animals asked once and remembered.",

    # ------------------------------------------------------------ lancer un farm
    "Lancer un farm": "Start a farm",
    "⚡ Ta dernière bête ramassée : {name} ({res})": "⚡ Your last harvested animal: {name} ({res})",
    "1 · Réserve": "1 · Reserve",
    "2 · Animal": "2 · Animal",
    "Chercher :": "Search:",
    "Choisis un animal ci-dessus.": "Pick an animal above.",
    "Déjà commencé avant ? (sinon laisse 0)": "Already started before? (otherwise leave 0)",
    "Dernier GO tombé en (kills)": "Last GO took (kills)",
    "▶ Démarrer le farm": "▶ Start the farm",
    "Aucun animal trouvé.": "No animal found.",
    "\nIl n'est peut-être pas dans {x} : essaie « Toutes les réserves ».": "\nMaybe it isn't in {x}: try \"All reserves\".",
    "Farm lancé : {name} · {res}. Bonne chasse !": "Farm started: {name} · {res}. Happy hunting!",

    # ------------------------------------------------------------ tutoriel
    "TUTORIEL · {a} / {b}": "TUTORIAL · {a} / {b}",
    "Passer": "Skip", "Suivant ▶": "Next ▶", "Terminer": "Finish", "▶ Lancer mon premier farm": "▶ Start my first farm",
    "Bienvenue dans KillFarm Lite": "Welcome to KillFarm Lite",
    "L'appli compte toute seule les bêtes que tu RAMASSES dans theHunter, avec leur grade.\n\n"
    "Elle lit seulement ta sauvegarde : elle ne touche jamais au jeu.\n\nCe tuto te montre tout en 1 minute.":
        "The app automatically counts the animals you HARVEST in theHunter, with their grade.\n\n"
        "It only reads your save: it never touches the game.\n\nThis tutorial shows you everything in 1 minute.",
    "1. Lancer un farm": "1. Start a farm",
    "Clique ici, choisis la réserve (celle où tu joues est déjà choisie), puis l'animal. C'est tout !\n\n"
    "Encore plus rapide : quand tu ramasses une bête sans farm, un bandeau « Farmer celle-là » apparaît.":
        "Click here, pick the reserve (the one you're playing is already selected), then the animal. That's it!\n\n"
        "Even faster: when you harvest an animal with no farm, a \"Farm this one\" banner shows up.",
    "2. Ton compteur": "2. Your counter",
    "Le grand chiffre = tes kills depuis le dernier Great One (ou le total du farm : au choix dans ⚙).\n\n"
    "À droite : le total du farm et le nombre de Great Ones.":
        "The big number = your kills since the last Great One (or the farm total: your choice in ⚙).\n\n"
        "On the right: the farm total and the number of Great Ones.",
    "3. Les grades": "3. The grades",
    "Chaque bête ramassée est rangée selon sa médaille : sans médaille, bronze, argent, or, diamant, "
    "Great One.\n\nClic droit sur un badge = corriger à la main (+1 / −1). Un Great One pas reconnu : clic droit "
    "sur son badge > « Mon dernier kill était un Great One ».":
        "Every harvested animal is sorted by its medal: no medal, bronze, silver, gold, diamond, Great One.\n\n"
        "Right-click a badge = fix it by hand (+1 / −1). A Great One not detected: right-click its badge > "
        "\"My last kill was a Great One\".",
    "4. Corriger": "4. Fix the numbers",
    "« −1 / +1 » pour ajuster le compteur.\n« Annuler le dernier kill » si une bête a été comptée par erreur.":
        "\"−1 / +1\" to adjust the counter.\n\"Undo last kill\" if an animal was counted by mistake.",
    "5. Mes farms": "5. My farms",
    "Tous tes farms : passe de l'un à l'autre, modifie les chiffres (si tu avais commencé avant l'appli) ou "
    "supprime un farm.\n\nTous tes farms comptent en même temps.":
        "All your farms: switch between them, edit the numbers (if you started before the app) or delete a farm.\n\n"
        "All your farms count at the same time.",
    "6. Les affichages": "6. The displays",
    "Fenêtre = ce panneau.\nTikTok = une carte à glisser où tu veux, pour tes vidéos.\n"
    "Stream = une longue barre en bas de l'écran.\n\nF7 = changer d'affichage, F8 = cacher / montrer.\n"
    "La carte TikTok se glisse toujours à la souris (clic droit = menu). La souris passe à travers la barre "
    "Stream (pour jouer tranquille) : touche ² (sous Échap) pour la débloquer.":
        "Window = this panel.\nTikTok = a card you drag anywhere, for your videos.\n"
        "Stream = a long bar at the bottom of the screen.\n\nF7 = switch display, F8 = hide / show.\n"
        "The TikTok card can always be dragged with the mouse (right-click = menu). Mouse clicks go through the "
        "Stream bar (so you can play): press the ` key (under Esc) to unlock it.",
    "7. Réglages et couleurs": "7. Settings and colors",
    "⚙ : 4 couleurs (Automne, Forêt, Glace, Sang), taille de la carte TikTok, barre en haut ou en bas, "
    "transparence de la barre (on voit le jeu à travers), dossier de sauvegarde… et ce tuto, pour le revoir "
    "quand tu veux.\n\n💬 ⚙ > Discord : les mises à jour et l'aide.":
        "⚙: 4 colors (Autumn, Forest, Ice, Blood), TikTok card size, bar at the top or bottom, bar transparency "
        "(see the game through it), save folder, language… and this tutorial, to watch it again anytime.\n\n"
        "💬 ⚙ > Discord: updates and help.",
    "Dernier conseil": "One last tip",
    "Mets le jeu en « Fenêtré sans bordure » (Options > Affichage) : en « Plein écran », Windows cache la "
    "carte et la barre par-dessus le jeu.\n\nBonne chasse !":
        "Set the game to \"Borderless window\" (Options > Display): in \"Fullscreen\", Windows hides the card and "
        "the bar over the game.\n\nHappy hunting!",

    # ------------------------------------------------------------ modifier les chiffres
    "Modifier les chiffres": "Edit the numbers",
    "Total du farm (tous les kills)": "Farm total (all kills)",
    "Grades des bêtes ramassées": "Grades of harvested animals",
    "Enregistrer": "Save", "Annuler": "Cancel",
    "Mets uniquement des nombres.": "Only numbers, please.",
    "Chiffres enregistrés ✓": "Numbers saved ✓",
}
