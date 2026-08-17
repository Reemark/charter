# Charter Site Watcher

Surveille **https://voyage.benin.bj/** et envoie un email à
**lordelesly@gmail.com** dès qu'une modification du contenu est détectée.

Fonctionne entièrement via **GitHub Actions** : aucun serveur à gérer, aucun
coût (dans les limites gratuites de GitHub), scan automatique toutes les
**2 heures**.

## Mise en place (5 minutes)

### 1. Créer un mot de passe d'application Gmail

L'envoi d'email se fait via le compte Gmail `lordelesly@gmail.com` (ou un
autre compte expéditeur si tu préfères).

1. Va sur https://myaccount.google.com/apppasswords
2. Active la validation en 2 étapes si ce n'est pas déjà fait (obligatoire
   pour créer un mot de passe d'application)
3. Crée un mot de passe d'application (nom libre, ex: "charter-watcher")
4. Copie le mot de passe généré (16 caractères) — tu ne le reverras plus

### 2. Ajouter les secrets sur GitHub

Dans ce dépôt : **Settings → Secrets and variables → Actions → New repository secret**

| Nom du secret   | Valeur                                              |
|-----------------|------------------------------------------------------|
| `SMTP_USER`     | l'adresse Gmail qui envoie le mail (ex: `lordelesly@gmail.com`) |
| `SMTP_PASSWORD` | le mot de passe d'application généré à l'étape 1     |

C'est tout — le destinataire (`lordelesly@gmail.com`) et l'URL surveillée
sont déjà configurés dans `.github/workflows/scan.yml`.

### 3. Activer le workflow

Le fichier `.github/workflows/scan.yml` est déjà prêt. Dès que ce dépôt est
poussé sur GitHub avec les secrets configurés, le scan démarre automatiquement
toutes les 2 heures.

### 4. Tester immédiatement (sans attendre 2h)

Onglet **Actions** du dépôt → workflow **"Scan du site toutes les 2h"** →
bouton **"Run workflow"**. Regarde les logs pour confirmer que tout
fonctionne.

Pour tester l'envoi d'email même sans modification, coche l'option
**force_email_on_no_change** dans le lancement manuel du workflow. Le script
enverra alors un email de test indiquant qu'il n'y a pas eu de changement.

Test local pour simuler le même comportement :

```bash
SEND_EMAIL_ON_NO_CHANGE=true python scan.py
```

## Comment ça marche

- `scan.py` récupère le texte visible de la page, calcule une empreinte
  (hash SHA-256), et la compare à celle du dernier scan.
- L'état du dernier scan est stocké dans `state/last_scan.json`, qui est
  automatiquement commité dans le dépôt par le workflow — c'est ce qui permet
  de comparer les scans d'une exécution à l'autre sans base de données ni
  serveur.
- **Premier scan** : aucun email n'est envoyé (rien à comparer), seule la
  version initiale est enregistrée.
- **Scans suivants** : si le contenu a changé → email envoyé avec la date de
  détection. Sinon → rien (pas de spam).
- **En cas d'erreur** (site inaccessible, certificat SSL invalide, etc.) →
  un email d'alerte est également envoyé pour te prévenir.

## Changer la configuration

Tout se règle dans `.github/workflows/scan.yml`, section `env` :

```yaml
env:
  TARGET_URL: https://voyage.benin.bj/
  EMAIL_TO: lordelesly@gmail.com
  SMTP_HOST: smtp.gmail.com
  SMTP_PORT: "587"
```

Pour changer la fréquence, modifie la ligne `cron` en haut du fichier
(actuellement `0 */2 * * *` = toutes les 2h). Attention : GitHub Actions peut
retarder légèrement les cron jobs en cas de forte charge sur leur
infrastructure — ce n'est pas garanti à la minute près, mais reste fiable à
quelques minutes près.

## Test en local (optionnel)

```bash
pip install -r requirements.txt
export SMTP_USER="ton-compte@gmail.com"
export SMTP_PASSWORD="ton-mot-de-passe-application"
python scan.py
```
