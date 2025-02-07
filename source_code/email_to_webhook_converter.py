"""
Modulo per la conversione da email a webhook.

Questo modulo converte le email inviate da TradingView
in webhook conformi allo standard di BeBo_bridge, permettendo
di usare il piano free per automatizzare le strategie di trading.
Il piano free include infatti l'invio di email associate alla generazione
degli alert.
"""

import os
import json
import time
import requests
from pathlib import Path
from threading import Timer
from email_to_webhook_helper import EmailMonitor, EMAIL_TO_WEBHOOK_HELPER


# Versione del modulo
EMAIL_TO_WEBHOOK_CONVERTER: str = 'v1.9.6'

# Configurazioni di base
REQUIRED_ENV_VARS = ["EMAIL_PORT", "EMAIL_SERVER", "EMAIL_ACCOUNT", "EMAIL_PASSWORD", "ADMIN_CHECK"]

# Controllo iniziale delle variabili d'ambiente
for var in REQUIRED_ENV_VARS:
    if not os.environ.get(var):
        raise EnvironmentError(f"Errore: La variabile d'ambiente {var} non è impostata.")

# Definizione degli URL dei Webhook
WEBHOOK_ADDRESSES = {
    "SERVER_1": 'https://<1st_server_address>',
    "SERVER_2": 'https://<2nd_server_address>',
    "SERVER_3": 'https://<3rd_server_address>',
    "SERVER_4": 'https://<4th_server_address>',
    "SERVER_5": 'https://<5th_server_address>'
}

# Definizione del provider e URL
WEBHOOK_RECIPIENT: str = 'SERVER_1'

# Configurazione
CONFIG = {
    'email': {
        'port': os.environ.get('EMAIL_PORT'),
        'server': os.environ.get('EMAIL_SERVER'),
        'account': os.environ.get('EMAIL_ACCOUNT'),
        'password': os.environ.get('EMAIL_PASSWORD'),
    },
    'webhook': {
        'url': '',
        'timeout': 5  # secondi
    },
    'system': {
        'log_folder': str(Path.home() / 'venv' / 'crypto' / 'BeBo_bridge' / 'modules' / 'email_to_webhook' / 'log'),
        'webhook_folder': str(Path.home() / 'venv' / 'crypto' / 'BeBo_bridge' / 'modules' / 'email_to_webhook' / 'webhook'),
        'idle_refresh_time': 5,  # secondi
        'reconnect_delay': 5  # secondi
    }
}

# Aggiornamento del CONFIG con l'URL corretto
try:
    CONFIG['webhook']['url'] = WEBHOOK_ADDRESSES[WEBHOOK_RECIPIENT]
except KeyError as e:
    raise ValueError(f"Provider non supportato: {WEBHOOK_RECIPIENT}") from e

if CONFIG['webhook']['url'] is None:
    raise ValueError(f"URL per il provider '{WEBHOOK_RECIPIENT}' non trovato.")

# Inizializza il monitor e ottieni il logger
monitor = EmailMonitor(CONFIG)
logger = monitor.logger

def check_network_connection(logger, retries=3, timeout=5):  # <-- Passiamo 'logger' come parametro, altrimenti ciaone ai log.
    """Verifica la connettività di rete con logging integrato."""
    urls = [
        "https://www.google.com",
        "https://1.1.1.1",
        "https://api.github.com"
    ]
    
    logger.info("Inizio verifica connettività di rete...")
    
    for attempt in range(retries):
        logger.info(f"Tentativo {attempt + 1}/{retries}")
        for idx, url in enumerate(urls):
            try:
                response = requests.get(url, timeout=timeout)
                if response.status_code == 200:
                    logger.info(f"Connessione riuscita a {url}")
                    return True
            except (requests.ConnectionError, requests.Timeout) as e:
                logger.warning(f"Fallito tentativo a {url}")
                if idx == len(urls) - 1:
                    logger.warning("Nessun endpoint raggiungibile in questo tentativo")
        
        if attempt < retries - 1:
            logger.info("Attesa prima del prossimo tentativo...")
            time.sleep(2)
    
    logger.error("Verifica connettività fallita dopo tutti i tentativi")
    return False

def main() -> None:
    """Funzione principale per avviare il monitoraggio."""

    os.system('/usr/bin/clear')
    
    # Verifica connettività
    if not check_network_connection(logger):  # Passa il logger come parametro
        logger.critical("Connessione Internet assente o instabile.")
        exit(1)

    # Controlla se la password email è impostata
    if not CONFIG['email']['password']:
        logger.critical("Password email non trovata nelle variabili d'ambiente.")
        exit(1)

    # Preparo il payload per il webhook di stato
    admin_check = os.environ.get("ADMIN_CHECK", "manca-il-token-di-autenticazione")
    _auth = json.dumps({"user": "0", "check": admin_check})
    _action = json.dumps({
        "action": "notify",
        "message": (
            f"%5B%20EMAIL%20to%20WEBHOOK%20%5D%0A"
            f"%2E%20converter%20%2D%20{EMAIL_TO_WEBHOOK_CONVERTER}%0A"
            f"%2E%20helper%20%2D%20{EMAIL_TO_WEBHOOK_HELPER}%0A"
            f"%5B%20{WEBHOOK_RECIPIENT}%20%5D"
        )
    })
    _payload = json.loads(f"[{_action},{_auth}]")

    # Avvio il webhook di benvenuto con un timer
    welcome_delay: float = 10
    webhook_thread = Timer(welcome_delay, monitor.send_webhook, args=(_payload,))
    webhook_thread.daemon = True
    webhook_thread.start()

    # Avvio il monitoraggio delle email
    monitor.monitor_emails()

if __name__ == "__main__":
    main()