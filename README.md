# Aide à la rédaction de comptes rendus médicaux — Anonymiseur

Application web **locale** qui anonymise des comptes rendus (CR) médicaux puis,
**optionnellement**, aide à les rédiger via une IA — à partir du **texte
anonymisé** uniquement.

> ## ⚠️ Avertissement — outil pédagogique, PAS un dispositif médical
>
> **Cet outil est fourni à des fins UNIQUEMENT PÉDAGOGIQUES et de démonstration.**
>
> - Ce **n'est pas un dispositif médical (DM)** au sens du Règlement (UE)
>   2017/745. Il n'est ni certifié, ni marqué CE, ni destiné à un usage clinique
>   ou diagnostique.
> - Il **ne doit pas** être utilisé pour la prise en charge de patients réels, ni
>   pour produire des comptes rendus à visée médicale opposable.
> - L'anonymisation repose sur des règles heuristiques **sans garantie
>   d'exhaustivité** : aucune assurance que toutes les données identifiantes
>   soient retirées sur un format de document non prévu.
> - La génération de CR par IA peut produire des **erreurs** ; tout contenu doit
>   être vérifié par un professionnel. Aucune responsabilité de l'auteur ne
>   saurait être engagée du fait de son utilisation.

> **Modèle de confidentialité**
> - L'**anonymisation** est faite **100 % en local** (extraction PDF + masquage
>   par règles dans le serveur Python local). Aucune donnée patient ne sort du poste.
> - La **génération de CR** est **optionnelle** : si tu l'utilises, c'est le texte
>   **déjà anonymisé** (`[NOM]`, `[DATE]`, `[ID]`…) qui est envoyé au fournisseur
>   d'IA choisi. Les clés API restent stockées localement.

## Fonctionnalités

- **🗂 Workflow** : liste de travail des examens déposés dans les dossiers
  surveillés (triés du plus récent), anonymisés automatiquement (✓), puis
  fenêtre d'**interprétation** → génération du CR par l'IA, écrit en `.txt` à
  côté du document source.
- **✍ Manuel** : anonymise un PDF ou un texte collé à la demande, avec aperçu
  PDF avant/après et bouton *Anonymiser* / *Anonymiser et rédiger le CR*.
- **Génération de CR multi-fournisseurs** : DeepSeek, OpenAI ou Anthropic
  (Claude), avec un **system prompt par type d'examen** (l'équivalent d'un
  GEM / GPT dédié) et un test de connexion intégré.
- **Types de documents personnalisés** : on fournit un CR **fictif**, une IA
  repère les champs identifiants et propose des règles qui tournent ensuite
  **100 % en local**.
- **Surveillance de dossiers** : anonymisation automatique en tâche de fond des
  PDF déposés (récursif, conserve la mise en page).

## Types de CR pris en charge nativement

| Type | Appareil | Identifiants retirés (spécifiques) |
|------|----------|-------------------------------------|
| Échographie cardiaque | Philips | Nom (en-tête + pieds de page), N° patient, date d'étude |
| Polygraphie ventilatoire | Nox T3 | Nom (2 ordres), date de naissance, dates |
| Holter ECG | Schiller MT-200 | Nom (en-têtes EN/FR), date de naissance, horodatages |

D'autres types peuvent être ajoutés via l'assistant **« Gestion de document »**.

## Ce qui est retiré / conservé

**Retiré** : nom du patient, n° patient / dossier, date de naissance, âge, sexe,
toutes les dates calendaires et horodatages date+heure, médecin
référent/opérateur, établissement, e-mail, téléphone, NIR.

**Conservé** : toutes les mesures et conclusions, taille / poids / IMC / SC, et
les **heures « nues »** (`11:47`, durées d'épisodes, durée d'enregistrement) —
elles portent souvent une information clinique et ne sont pas identifiantes une
fois le nom et la date de naissance retirés.

> Méthode : **règles locales** (extraction des champs étiquetés puis
> remplacement global + regex). Anonymisation **pure** (jetons fixes, aucune
> table de correspondance conservée).

## Le Workflow en pratique

1. Les dossiers à suivre sont cochés dans **⚙ Configuration**.
2. Dès qu'un examen (PDF) arrive dans un de ces dossiers (ou un sous-dossier),
   il **remonte en tête** de la liste et est **anonymisé automatiquement** (✓).
3. On le sélectionne : la liseuse affiche le document anonymisé (bascule
   Original/Anonymisé), avec le récapitulatif des éléments masqués.
4. On saisit son **interprétation** (ex. *« hypokinésie basale inférieure, fuite
   mitrale modérée »*), puis **Générer le CR (IA)**.
5. Le CR généré s'affiche et est **enregistré en `.txt`** à côté du PDF source.

Le listing est **rapide** (métadonnées seulement) ; l'anonymisation est traitée
en tâche de fond, du plus récent au plus ancien — adapté à un partage réseau
contenant beaucoup de dossiers.

## Génération de CR par IA

Configurable dans **⚙ Configuration → Génération de CR (IA)** :

- **Fournisseur** : DeepSeek, OpenAI ou Anthropic (Claude).
- **Clé API** (stockée localement dans `%LOCALAPPDATA%\AnonymiseurCR\llm.json`),
  avec un bouton **🔌 Tester la connexion** (un test réussi enregistre la clé).
- **Modèle** modifiable, et **un system prompt par type d'examen**.

> ⚠️ La génération **envoie le texte anonymisé à un service externe**. Vérifie le
> récapitulatif des éléments masqués avant d'envoyer. La surveillance
> automatique de dossiers ne fait QUE l'anonymisation, jamais de génération IA.

## Surveillance automatique de dossiers (watcher)

En tâche de fond, dès qu'un PDF est déposé dans un dossier surveillé, une version
anonymisée est créée **dans le même dossier**, mise en page conservée, sous un
**nom neutre** `ANOM_0001.pdf`, `ANOM_0002.pdf`… (aucun nom patient dans le nom
de fichier). Récursif par défaut (descend dans les sous-dossiers).

Réglages dans **`config.json`** (relu à chaud) :

```json
{
  "poll_interval_seconds": 10,
  "watch": [
    { "directory": "C:/Users/.../CR_a_anonymiser/ETT",
      "cr_type": "echo_cardiaque", "enabled": true, "recursive": true }
  ]
}
```

- `cr_type` : `echo_cardiaque`, `polygraphie`, `holter`, un type personnalisé, ou
  **`auto`** (détection d'après le contenu).
- Garde-fous : fichiers `ANOM_*` ignorés, pas de retraitement, attente de
  stabilité du fichier, PDF scannés (sans texte) signalés et ignorés.

## Installation (.exe, sans Python)

- **Installeur** : `installer/AnonymiseurCR_Setup_1.0.0.exe` — installation par
  utilisateur, **sans droits administrateur**, raccourcis menu Démarrer + Bureau.
- **Version portable** : `dist/AnonymiseurCR.exe` — se lance tel quel.

L'exécutable embarque tout (serveur web + interface + PDF.js + surveillance). Au
lancement, le navigateur s'ouvre sur l'interface ; **fermer la fenêtre** (console)
arrête l'application. Données propres à chaque poste, créées au 1er lancement
dans `%LOCALAPPDATA%\AnonymiseurCR\` (config, clés, journaux).

**Reconstruire** : `build_installer.bat` (nécessite le venv +
[Inno Setup 6](https://jrsoftware.org/isinfo.php) pour l'installeur).

## Développement

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m uvicorn main:app --app-dir backend --port 8000
# puis ouvrir http://127.0.0.1:8000
```

(ou double-clic sur `run.bat`, qui crée le venv au premier lancement).

## Structure

```
app_launcher.py     point d'entrée de l'app empaquetée (serveur + watcher + navigateur)
watcher.py          surveillance de dossiers (anonymisation automatique)
backend/
  main.py           API FastAPI + service du front
  appconfig.py      chemins portables (dev vs .exe) + config par défaut
  pdf_extract.py    extraction texte (pdfplumber)
  extractors.py     extraction des identifiants par type de CR
  rules.py          règles regex génériques (dates, âge, sexe, contacts…)
  anonymizer.py     moteur texte (extraction → remplacement global → règles)
  pdf_redact.py     rédaction du PDF d'origine (PyMuPDF), structure conservée
  custom_types.py   types de documents appris via IA
  worklist.py       Workflow : liste de travail + anonymisation en tâche de fond
  llm.py            génération de CR multi-fournisseurs (DeepSeek/OpenAI/Anthropic)
frontend/
  index.html        interface web (Workflow / Manuel / Gestion / Configuration)
  vendor/pdfjs/     PDF.js (liseuse intégrée, hors-ligne)
```

## Limites

- PDF **scannés** (images sans couche texte) non gérés (pas d'OCR).
- Les règles natives sont calibrées sur les modèles fournis ; un nouveau modèle
  peut nécessiter un type personnalisé ou un ajustement dans `extractors.py` /
  `rules.py`. Le récapitulatif permet de vérifier avant tout envoi à une IA.

## Avertissement (rappel)

**Outil à des fins pédagogiques uniquement — ce n'est PAS un dispositif médical
(DM).** Non certifié, non marqué CE, non destiné à un usage clinique ou
diagnostique, et à ne pas utiliser sur des patients réels.

La responsabilité de vérifier l'anonymisation (récapitulatif des éléments masqués
+ aperçu PDF) **avant** toute transmission à un service d'IA incombe à
l'utilisateur. Aucune garantie d'exhaustivité du masquage sur un format de
document non prévu, et aucune garantie d'exactitude des CR générés par l'IA.
