# Flusso di Processo - Email to Webhook Converter

## 1. Inizializzazione

### 1.1 Verifica Ambiente
Il processo inizia verificando la presenza delle variabili d'ambiente necessarie:

```python
REQUIRED_ENV_VARS = [
    "EMAIL_PORT", 
    "EMAIL_SERVER", 
    "EMAIL_ACCOUNT", 
    "EMAIL_PASSWORD", 
    "ADMIN_CHECK"
]

for var in REQUIRED_ENV_VARS:
    if not os.environ.get(var):
        raise EnvironmentError(f"Errore: La variabile d'ambiente {var} non è impostata.")
```

### 1.2 Setup Configurazione
Viene creato il dizionario di configurazione:

```python
CONFIG = {
    'email': {
        'port': os.environ.get('EMAIL_PORT'),
        'server': os.environ.get('EMAIL_SERVER'),
        'account': os.environ.get('EMAIL_ACCOUNT'),
        'password': os.environ.get('EMAIL_PASSWORD'),
    },
    'webhook': {
        'url': WEBHOOK_ADDRESSES[WEBHOOK_RECIPIENT],
        'timeout': 5
    },
    'system': {
        'log_folder': str(Path.home() / 'venv' / 'crypto' / 'BeBo_bridge' / 
                         'modules' / 'email_to_webhook' / 'log'),
        'webhook_folder': str(Path.home() / 'venv' / 'crypto' / 'BeBo_bridge' / 
                            'modules' / 'email_to_webhook' / 'webhook'),
        'idle_refresh_time': 5,
        'reconnect_delay': 5
    }
}
```

## 2. Setup del Sistema di Logging

### 2.1 Configurazione Logger
```python
def __setup_logging(self) -> logging.Logger:
    logger = logging.getLogger('EmailMonitor')
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # File handler con rotazione giornaliera
    log_file = Path(self.__config['system']['log_folder']) / 'email_monitor.log'
    file_handler = TimedRotatingFileHandler(
        log_file, 
        when='midnight', 
        interval=1, 
        backupCount=30
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger
```

## 3. Connessione al Server Email

### 3.1 Gestione della Connessione IMAP
```python
def __connect(self, tentativi: int = 3) -> None:
    self.__logout()  # Chiudi eventuali connessioni residue

    server: str = self.__config['email']['server']
    port: int = self.__config['email']['port']
    account: str = self.__config['email']['account']

    for attempt in range(tentativi):
        try:
            self.__client = IMAPClient(server, port=port, ssl=True, timeout=10)
            self.__client.login(account, self.__password)
            self.__client.select_folder('INBOX')
            self.__connection_time = datetime.now()
            self.logger.info(f"Connesso a {server}:{port} (tentativo {attempt + 1})")
            return

        except IMAPClient.Error as e:
            match str(e).lower():
                case msg if 'authentication failed' in msg:
                    self.logger.error("Credenziali errate")
                    raise
                case msg if 'no such folder' in msg:
                    self.logger.error("Cartella INBOX non trovata")
                    raise RuntimeError("Configurazione mailbox errata") from e
            
            self.logger.warning(f"Problema IMAP (tentativo {attempt + 1}): {e}")
            self.__client = None

        except (TimeoutError, ConnectionRefusedError) as e:
            self.logger.warning(f"Errore rete ({e.__class__.__name__}): {e}")
            sleep(2 ** attempt * 0.5 + (attempt * 0.3))

    raise ConnectionError(f"Connessione fallita dopo {tentativi} tentativi")
```

## 4. Monitoraggio Email

### 4.1 Loop Principale di Monitoraggio
```python
def monitor_emails(self) -> None:
    while True:
        try:
            self.__connect()
            self.__setup_folder(self.__processed_folder)
            self.__setup_folder(self.__unmanaged_folder)
            idle_mode = False

            while True:
                try:
                    if not idle_mode:
                        self.__client.idle()
                        idle_mode = True

                    events = self.__client.idle_check(
                        timeout=self.__config['system']['idle_refresh_time']
                    )
                    
                    if events:
                        if events[0][1] != b'Still here':
                            self.logger.debug(f"Evento IMAP: {events}")
                        self.__client.idle_done()
                        idle_mode = False
                        self.__process_new_emails()
                        continue

                    self.__client.idle_done()
                    idle_mode = False
                    self.__process_new_emails()

                except IMAPClient.Error as e:
                    self.logger.error(f"Errore IMAP: {e}")
                    idle_mode = False
                    break
                
                except KeyboardInterrupt:
                    if idle_mode:
                        self.__client.idle_done()
                    raise

            self.__logout()
            sleep(self.__reconnect_delay)

        except KeyboardInterrupt:
            self.logger.debug("Interruzione utente confermata")
            self.__logout()
            break
            
        except Exception as e:
            self.logger.error(f"[monitor_emails]: {e}")
            self.__logout()
            sleep(self.__reconnect_delay)
```

## 5. Processamento Email

### 5.1 Gestione Nuove Email
```python
def __process_new_emails(self) -> None:
    try:
        date_str = self.__connection_time.strftime("%d-%b-%Y")
        messages = self.__client.search([b'UNSEEN', b'SINCE', date_str])
        
        if not messages:
            return
            
        for uid in messages:
            try:
                raw_email = self.__client.fetch([uid], ["RFC822"])[uid][b"RFC822"]
                self.__manage_email(raw_email, uid)
            except (IMAPClient.Error, OSError) as e:
                self.logger.error(f"Errore elaborazione email {uid}: {e}")
                self.__move_email(uid, self.__unmanaged_folder)
                
    except RuntimeError as e:
        self.logger.error(f"Errore generale processamento email: {e}")
```

### 5.2 Elaborazione Contenuto Email
```python
def __manage_email(self, raw_email: bytes, uid: int) -> None:
    try:
        message = email.message_from_bytes(raw_email)
        content = message.get_payload(decode=True).decode(errors="replace").strip()
        
        if not (content.startswith('[') and content.endswith(']')):
            raise ValueError("Il contenuto dell'email non è un array JSON valido.")
        
        payload_list = json.loads(content)
        if len(payload_list) < 2:
            raise ValueError("Il JSON deve contenere almeno due elementi.")
        
        self.logger.info(f"Email {uid} processata correttamente.")
        
        execution = self.__executor.submit(self.send_webhook, payload_list)
        status = execution.result()
        
        if status:
            self.__save_payload(payload_list)
            self.__move_email(uid, self.__processed_folder)
        else:
            self.logger.error(f"Invio webhook fallito per l'email {uid}")
            self.__move_email(uid, self.__unmanaged_folder)
    
    except (json.JSONDecodeError, ValueError) as e:
        self.logger.error(f"Parsing email {uid} fallito: {e}")
        self.__move_email(uid, self.__unmanaged_folder)
    except requests.exceptions.ConnectionError as e:
        self.logger.critical(f"Errore di rete durante l'invio del webhook: {e}")
        raise
```

## 6. Invio Webhook e Archiviazione

### 6.1 Invio Webhook
```python
def send_webhook(self, payload: dict) -> bool:
    status: bool = False
    try:
        response = requests.post(
            self.__config['webhook']['url'],
            json=payload,
            timeout=self.__config['webhook']['timeout']
        )
        response.raise_for_status()
        self.logger.info(f"Webhook inviato con successo (status: {response.status_code})")
        status = True
    except requests.RequestException as e:
        self.logger.error(f"[send_webhook]: {e}")
    return status
```

### 6.2 Archiviazione Payload
```python
def __save_payload(self, payload: dict) -> None:
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"alert_{timestamp}.json"
        filepath = Path(self.__config['system']['webhook_folder']) / filename

        data = {
            "timestamp": timestamp,
            "payload": payload
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        self.logger.info(f"Payload salvato: {filename}")
    except (OSError, json.JSONDecodeError) as e:
        raise OSError(f"Errore nel salvataggio del file JSON: {e}")
```

## 7. Gestione Pulizia e Chiusura

### 7.1 Logout e Chiusura Connessioni
```python
def __logout(self) -> None:
    if self.__client:
        try:
            if getattr(self.__client, '_idle_processing', False):
                try:
                    self.__client.idle_done()
                except (IMAPClient.Error, OSError) as e:
                    self.logger.debug(f"Errore uscita IDLE: {e}")

            try:
                self.__client.logout()
            except (IMAPClient.AbortError, IMAPClient.Error, OSError) as e:
                self.logger.debug(f"Errore durante il logout: {e}")
            
        except AttributeError as e:
            self.logger.warning(f"Connessione già chiusa: {e}")
        
        finally:
            self.__client = None
```

### 7.2 Cleanup Finale
```python
def __del__(self):
    """Chiude l'executor quando l'oggetto viene distrutto."""
    self.__executor.shutdown(wait=True)
```

## Flusso Logico del Processo

1. **Inizializzazione**
   - Verifica variabili ambiente
   - Setup configurazione
   - Inizializzazione logger
   - Creazione directory necessarie

2. **Connessione**
   - Tentativo di connessione al server IMAP
   - Gestione errori e ritentativi
   - Setup cartelle di sistema

3. **Loop Principale**
   - Entrata in modalità IDLE
   - Controllo eventi ogni 5 secondi
   - Processamento email non lette
   - Gestione riconnessioni

4. **Processamento Email**
   - Lettura contenuto email
   - Parsing JSON
   - Validazione payload
   - Invio webhook in thread separato
   - Archiviazione risultati

5. **Gestione Errori**
   - Logging dettagliato
   - Spostamento email problematiche
   - Riconnessione automatica
   - Gestione interruzioni

6. **Cleanup**
   - Chiusura connessioni
   - Logout pulito
   - Shutdown executor thread