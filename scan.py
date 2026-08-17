"""
Charter Site Watcher
---------------------
Scanne une URL, compare son contenu texte au dernier scan enregistré
(state/last_scan.json, versionné dans le dépôt), et envoie un email
si une modification est détectée.

Conçu pour être lancé par le workflow GitHub Actions .github/workflows/scan.yml
toutes les 2 heures, mais peut aussi être lancé en local :

    pip install -r requirements.txt
    SMTP_USER=... SMTP_PASSWORD=... python scan.py
"""

import hashlib
import json
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = BASE_DIR / "state" / "last_scan.json"

TARGET_URL = os.getenv("TARGET_URL", "https://voyage.benin.bj/")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
USER_AGENT = os.getenv(
    "REQUEST_USER_AGENT",
    "CharterSiteWatcher/1.0 (+https://github.com/Reemark/charter)",
)


def fetch_page(url: str):
    """Récupère la page et renvoie (texte_visible, html_brut)."""
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    visible_text = " ".join(soup.stripped_strings)
    return visible_text, response.text


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_previous_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return None


def save_state(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def send_email(subject: str, body: str):
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    email_from = os.getenv("EMAIL_FROM", smtp_user)
    email_to = os.getenv("EMAIL_TO", "lordelesly@gmail.com")

    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = email_from
    message["To"] = email_to

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(email_from, [email_to], message.as_string())

    print(f"Email envoyé à {email_to}")


def main():
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"Scan de {TARGET_URL} à {now}")

    try:
        visible_text, _raw_html = fetch_page(TARGET_URL)
    except Exception as exc:
        print(f"Erreur lors du scan : {exc}", file=sys.stderr)
        try:
            send_email(
                f"[Charter Site Watcher] Erreur de scan sur {TARGET_URL}",
                f"Le scan du {now} a échoué avec l'erreur suivante :\n\n{exc}\n\n"
                "Le site est peut-être temporairement inaccessible, ou son "
                "certificat SSL pose un problème. Vérifiez manuellement.",
            )
        except Exception as mail_exc:
            print(f"Erreur lors de l'envoi de l'email d'alerte : {mail_exc}", file=sys.stderr)
        sys.exit(1)

    current_hash = compute_hash(visible_text)
    previous = load_previous_state()

    if previous is None:
        save_state(
            {
                "hash": current_hash,
                "scanned_at": now,
                "text_snapshot": visible_text[:5000],
            }
        )
        print("Aucun historique trouvé : version initiale enregistrée, aucun email envoyé.")
        return

    if previous["hash"] == current_hash:
        print(f"Aucun changement détecté depuis le {previous.get('scanned_at')}.")
        return

    print("Changement détecté !")
    body = (
        f"Une modification a été détectée sur le site surveillé.\n\n"
        f"URL : {TARGET_URL}\n"
        f"Date de détection : {now}\n"
        f"Dernier scan sans changement : {previous.get('scanned_at')}\n\n"
        f"Ouvrez le site pour voir le contenu actuel :\n{TARGET_URL}"
    )
    send_email(f"[Charter Site Watcher] Modification détectée sur {TARGET_URL}", body)

    save_state(
        {
            "hash": current_hash,
            "scanned_at": now,
            "text_snapshot": visible_text[:5000],
        }
    )


if __name__ == "__main__":
    main()
