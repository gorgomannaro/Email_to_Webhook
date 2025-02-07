import os
import json
from time import time, sleep
import email
import logging
import requests
from pathlib import Path
from datetime import datetime
from imapclient import IMAPClient
from logging.handlers import TimedRotatingFileHandler
from concurrent.futures import ThreadPoolExecutor


# Versione del modulo
EMAIL_TO_WEBHOOK_HELPER: str = 'v1.9.6'

class EmailMonitor:
    def __init__(self, config: dict) -> None:
        self.__config = config
        self.__password = config['email']['password']
        self.__reconnect_delay = config['system']['reconnect_delay']        
        self.__client = None
        self.__connection_time = None
        self.__processed_folder = 'PROCESSED'
        self.__unmanaged_folder = 'UNMANAGED'
        self.__setup_directories()
        self.logger = self.__setup_logging()
        self.__executor = ThreadPoolExecutor(max_workers=5)  # Creiamo un ThreadPoolExecutor con 5 worker

    def __setup_logging(self) -> logging.Logger:
        
        # Crea l'oggetto "logger" e pulisci gli handlers
        logger = logging.getLogger('EmailMonitor')
        logger.handlers.clear()  # Rimuovi handler esistenti
        logger.setLevel(logging.DEBUG)
        # logger.setLevel(logging.INFO)
        
        # Configura formattatore
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # File handler (rotazione giornaliera)
        log_file = Path(self.__config['system']['log_folder']) / 'email_monitor.log'
        file_handler = TimedRotatingFileHandler(log_file, when='midnight', interval=1, backupCount=30)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger
    
    def __setup_directories(self) -> None:
        log_folder = Path(self.__config['system']['log_folder'])
        webhook_folder = Path(self.__config['system']['webhook_folder'])
        try:
            log_folder.mkdir(parents=True, exist_ok=True)
            webhook_folder.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise  # Propaga l'OSError originale
    
    def __connect(self, tentativi: int = 3) -> None:
        """Connette al server IMAP con gestione essenziale degli errori.
        
        Eccezioni propagate:
        - IMAPClient.Error: in caso di credenziali errate o errori specifici IMAP
        - RuntimeError: in caso di cartella INBOX non trovata
        - ConnectionError: se tutti i tentativi di riconnessione falliscono
        """
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
                        raise last_exception  # Propaga l'errore originale interrompendo i tentativi
                    case msg if 'no such folder' in msg:
                        self.logger.error("Cartella INBOX non trovata")
                        raise RuntimeError("Configurazione mailbox errata") from e
                
                self.logger.warning(f"Problema IMAP (tentativo {attempt + 1}): {e}")
                self.__client = None

            except (TimeoutError, ConnectionRefusedError) as e:
                self.logger.warning(f"Errore rete ({e.__class__.__name__}): {e}")
                sleep(2 ** attempt * 0.5 + (attempt * 0.3))  # Backoff con jitter leggero

        raise ConnectionError(f"Connessione fallita dopo {tentativi} tentativi") from last_exception
    
    def __logout(self) -> None:
        """Chiude la connessione in modo sicuro con gestione dello stato IDLE"""
        if self.__client:
            try:
                # Controlla se siamo in stato IDLE
                if getattr(self.__client, '_idle_processing', False):
                    try:
                        self.__client.idle_done()
                    except (IMAPClient.Error, OSError) as e:
                        self.logger.debug(f"Errore uscita IDLE: {e}")

                # Effettua il logout standard
                try:
                    self.__client.logout()
                except (IMAPClient.AbortError, IMAPClient.Error, OSError) as e:
                    self.logger.debug(f"Errore durante il logout: {e}")
                
            except AttributeError as e:
                self.logger.warning(f"Connessione già chiusa: {e}")
            
            finally:
                self.__client = None
    
    def __setup_folder(self, folder_name: str) -> None:
        """Crea una cartella se non esiste già.
        
        Args:
            folder_name: Nome della cartella da creare
        """
        folders = self.__client.list_folders()
        folder_names = [name.decode() if isinstance(name, bytes) else name 
                    for (flags, delimiter, name) in folders]
        
        if folder_name not in folder_names:
            self.logger.info(f"Creazione cartella '{folder_name}'...")
            self.__client.create_folder(folder_name)

    def __move_email(self, uid: int, destination_folder: str) -> None:
        """Sposta un'email nella cartella specificata.
        
        Args:
            uid: ID univoco dell'email da spostare
            destination_folder: Nome della cartella di destinazione
        """
        try:
            self.__client.move(uid, destination_folder)
            log_method = (self.logger.warning if destination_folder == self.__unmanaged_folder 
                        else self.logger.info)
            log_method(f"Email {uid} spostata in {destination_folder}")
        except (IMAPClient.Error, OSError) as e:
            self.logger.critical(f"Errore spostamento email {uid} in {destination_folder}: {e}")
    
    def __process_new_emails(self) -> None:
        """Elabora le nuove email."""
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
    
    def __manage_email(self, raw_email: bytes, uid: int) -> None:
        """Gestisce l'elaborazione di un'email."""
        try:
            message = email.message_from_bytes(raw_email)
            content = message.get_payload(decode=True).decode(errors="replace").strip()
            
            if not (content.startswith('[') and content.endswith(']')):
                raise ValueError("Il contenuto dell'email non è un array JSON valido.")
            
            payload_list = json.loads(content)
            if len(payload_list) < 2:
                raise ValueError("Il JSON deve contenere almeno due elementi.")
            
            self.logger.info(f"Email {uid} processata correttamente.")
            
            # Esegui il webhook in un thread separato e attendi il risultato
            execution = self.__executor.submit(self.send_webhook, payload_list)
            status = execution.result()  # Aspetta che il thread termini e restituisca il valore
            
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


    def send_webhook(self, payload: dict) -> bool:
        """Invia un webhook con retry."""
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
            # raise
        return status

    def __save_payload(self, payload: dict) -> None:
        """Salva il payload in un file JSON."""
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

    def monitor_emails(self) -> None:
        """Monitoraggio email con corretta gestione degli stati IMAP"""
        while True:
            try:
                self.__connect()
                self.__setup_folder(self.__processed_folder)
                self.__setup_folder(self.__unmanaged_folder)
                connection_start = time()
                idle_mode = False

                while True:
                    try:
                        if not idle_mode:
                            self.__client.idle()
                            idle_mode = True
                            # self.logger.debug("Entrato in stato IDLE")

                        events = self.__client.idle_check(timeout=self.__config['system']['idle_refresh_time'])
                        
                        if events:
                            if events[0][1] != b'Still here':  # [(b'OK', b'Still here')] arriva ogni 2 minuti su ...@ik.me
                                self.logger.debug(f"Evento IMAP: {events}")
                            self.__client.idle_done()
                            idle_mode = False
                            self.__process_new_emails()
                            continue

                        # Timeout senza eventi, processa comunque
                        self.__client.idle_done()
                        idle_mode = False
                        self.__process_new_emails()

                    except IMAPClient.Error as e:
                        self.logger.error(f"Errore IMAP: {e}")
                        idle_mode = False
                        break
                    
                    except KeyboardInterrupt:
                        self.logger.debug("Interruzione ricevuta")
                        if idle_mode:
                            self.__client.idle_done()
                        raise
                
                self.__logout()
                self.logger.debug(f"Ho perso la connessione, riprovo tra {self.__reconnect_delay} secondi.")
                sleep(self.__reconnect_delay)

            except KeyboardInterrupt:
                self.logger.debug("Interruzione utente confermata")
                self.__logout()
                break
                
            except Exception as e:
                self.logger.error(f"[monitor_emails]: {e}")
                self.__logout()
                sleep(self.__reconnect_delay)

    def __del__(self):
        """Chiude l'executor quando l'oggetto viene distrutto."""
        self.__executor.shutdown(wait=True)
