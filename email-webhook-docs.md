# Email to Webhook Converter
## Guida all'Installazione e Configurazione

Questa guida ti permetterà di installare e configurare il convertitore Email to Webhook su Ubuntu Server 24.04 o superiore.

## Licenza
Questo software è rilasciato sotto licenza MIT.

## Prerequisiti
- Ubuntu Server 24.04 o superiore
- Python 3.10 o superiore
- pip3
- virtualenv

## 1. Preparazione dell'Ambiente
### 1.1 Installazione dei Requisiti di Sistema
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv -y
```

### 1.2 Creazione dell'Ambiente Virtuale
```bash
mkdir -p ~/venv/crypto/BeBo_bridge/modules/email_to_webhook
cd ~/venv/crypto
python3 -m venv .
source bin/activate
```

### 1.3 Installazione delle Dipendenze Python
```bash
pip install imapclient requests
```

## 2. Installazione del Software
### 2.1 Copia dei File
Crea i seguenti file nella directory `~/venv/crypto/BeBo_bridge/modules/email_to_webhook/`:

1. `email_to_webhook_converter.py`
2. `email_to_webhook_helper.py`
3. `.env` (file di configurazione)

### 2.2 Configurazione delle Variabili d'Ambiente
Crea il file `.env` nella tua home directory:
```bash
nano ~/.env
```

Inserisci le seguenti variabili, sostituendo i valori tra <...> con i tuoi dati:
```bash
ADMIN_CHECK='<authentication.key>'
EMAIL_PORT=993
EMAIL_SERVER='<email.provider.address>'
EMAIL_ACCOUNT='<user.account@email.provider>'
EMAIL_PASSWORD='<user.password>'
```

### 2.3 Configurazione degli URL Webhook
Modifica il file `email_to_webhook_converter.py` e aggiorna il dizionario `WEBHOOK_ADDRESSES` con i tuoi endpoint:
```python
WEBHOOK_ADDRESSES = {
    "SERVER_1": 'https://<your-webhook-endpoint>',
    # Aggiungi altri server se necessario
}
```

## 3. Modalità di Esecuzione

### 3.1 Modalità Standalone
Per eseguire il software in modalità standalone:
```bash
cd ~/venv/crypto/BeBo_bridge/modules/email_to_webhook
source ~/venv/crypto/bin/activate
python email_to_webhook_converter.py
```

### 3.2 Modalità Servizio (Systemd)
Per installare il software come servizio di sistema:

1. Crea il file di servizio:
```bash
sudo nano /etc/systemd/system/email-webhook.service
```

2. Copia il contenuto del file `email-webhook.service` sostituendo `<username>` con il tuo username:
```ini
[Unit]
Description=Email to Webhook Converter Service
After=network.target
 
[Service]
Type=simple
User=<username>
EnvironmentFile=/home/<username>/.env
WorkingDirectory=/home/<username>/venv/crypto/BeBo_bridge/modules/email_to_webhook
ExecStart=/home/<username>/venv/crypto/bin/python email_to_webhook_converter.py
StandardOutput=null
StandardError=journal
Restart=always
RestartSec=10
 
[Install]
WantedBy=multi-user.target
```

3. Abilita e avvia il servizio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable email-webhook
sudo systemctl start email-webhook
```

4. Verifica lo stato del servizio:
```bash
sudo systemctl status email-webhook
```

## 4. Monitoraggio e Log

### 4.1 Log del Software
I log vengono salvati in:
```
~/venv/crypto/BeBo_bridge/modules/email_to_webhook/log/email_monitor.log
```

### 4.2 Log di Sistema (modalità servizio)
Per visualizzare i log di sistema:
```bash
sudo journalctl -u email-webhook -f
```

## 5. Webhook Archiviati
I webhook processati vengono salvati in:
```
~/venv/crypto/BeBo_bridge/modules/email_to_webhook/webhook/
```

## 6. Risoluzione dei Problemi

### 6.1 Il servizio non si avvia
Verifica:
1. I permessi dei file:
```bash
chmod 600 ~/.env
chmod 644 ~/venv/crypto/BeBo_bridge/modules/email_to_webhook/*.py
```

2. I log di sistema:
```bash
sudo journalctl -u email-webhook -n 50
```

### 6.2 Errori di connessione
- Verifica le credenziali nel file `.env`
- Controlla che la porta IMAP (993) sia accessibile
- Verifica che l'autenticazione a due fattori sia disabilitata per l'account email

## 7. Manutenzione

### 7.1 Aggiornamento del Software
1. Ferma il servizio:
```bash
sudo systemctl stop email-webhook
```

2. Aggiorna i file Python
3. Riavvia il servizio:
```bash
sudo systemctl start email-webhook
```

### 7.2 Rotazione dei Log
I log vengono ruotati automaticamente ogni giorno e mantenuti per 30 giorni.