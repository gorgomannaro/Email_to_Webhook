# Process Flow - Email to Webhook Converter

## 1. Initialization

### 1.1 Environment Check
The process begins by verifying the required environment variables:

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
        raise EnvironmentError(f"Error: Environment variable {var} is not set.")
```

### 1.2 Configuration Setup
The configuration dictionary is created:

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

## 2. Logging System Setup

### 2.1 Logger Configuration
```python
def __setup_logging(self) -> logging.Logger:
    logger = logging.getLogger('EmailMonitor')
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # File handler with daily rotation
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

## 3. Email Server Connection

### 3.1 IMAP Connection Management
```python
def __connect(self, attempts: int = 3) -> None:
    self.__logout()  # Close any residual connections

    server: str = self.__config['email']['server']
    port: int = self.__config['email']['port']
    account: str = self.__config['email']['account']

    for attempt in range(attempts):
        try:
            self.__client = IMAPClient(server, port=port, ssl=True, timeout=10)
            self.__client.login(account, self.__password)
            self.__client.select_folder('INBOX')
            self.__connection_time = datetime.now()
            self.logger.info(f"Connected to {server}:{port} (attempt {attempt + 1})")
            return

        except IMAPClient.Error as e:
            match str(e).lower():
                case msg if 'authentication failed' in msg:
                    self.logger.error("Invalid credentials")
                    raise
                case msg if 'no such folder' in msg:
                    self.logger.error("INBOX folder not found")
                    raise RuntimeError("Invalid mailbox configuration") from e
            
            self.logger.warning(f"IMAP issue (attempt {attempt + 1}): {e}")
            self.__client = None

        except (TimeoutError, ConnectionRefusedError) as e:
            self.logger.warning(f"Network error ({e.__class__.__name__}): {e}")
            sleep(2 ** attempt * 0.5 + (attempt * 0.3))

    raise ConnectionError(f"Connection failed after {attempts} attempts")
```

## 4. Email Monitoring

### 4.1 Main Monitoring Loop
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
                            self.logger.debug(f"IMAP Event: {events}")
                        self.__client.idle_done()
                        idle_mode = False
                        self.__process_new_emails()
                        continue

                    self.__client.idle_done()
                    idle_mode = False
                    self.__process_new_emails()

                except IMAPClient.Error as e:
                    self.logger.error(f"IMAP Error: {e}")
                    idle_mode = False
                    break
                
                except KeyboardInterrupt:
                    if idle_mode:
                        self.__client.idle_done()
                    raise

            self.__logout()
            sleep(self.__reconnect_delay)

        except KeyboardInterrupt:
            self.logger.debug("User interrupt confirmed")
            self.__logout()
            break
            
        except Exception as e:
            self.logger.error(f"[monitor_emails]: {e}")
            self.__logout()
            sleep(self.__reconnect_delay)
```

## 5. Email Processing

### 5.1 New Email Management
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
                self.logger.error(f"Error processing email {uid}: {e}")
                self.__move_email(uid, self.__unmanaged_folder)
                
    except RuntimeError as e:
        self.logger.error(f"General email processing error: {e}")
```

### 5.2 Email Content Processing
```python
def __manage_email(self, raw_email: bytes, uid: int) -> None:
    try:
        message = email.message_from_bytes(raw_email)
        content = message.get_payload(decode=True).decode(errors="replace").strip()
        
        if not (content.startswith('[') and content.endswith(']')):
            raise ValueError("Email content is not a valid JSON array.")
        
        payload_list = json.loads(content)
        if len(payload_list) < 2:
            raise ValueError("JSON must contain at least two elements.")
        
        self.logger.info(f"Email {uid} processed successfully.")
        
        execution = self.__executor.submit(self.send_webhook, payload_list)
        status = execution.result()
        
        if status:
            self.__save_payload(payload_list)
            self.__move_email(uid, self.__processed_folder)
        else:
            self.logger.error(f"Webhook sending failed for email {uid}")
            self.__move_email(uid, self.__unmanaged_folder)
    
    except (json.JSONDecodeError, ValueError) as e:
        self.logger.error(f"Email parsing {uid} failed: {e}")
        self.__move_email(uid, self.__unmanaged_folder)
    except requests.exceptions.ConnectionError as e:
        self.logger.critical(f"Network error during webhook sending: {e}")
        raise
```

## 6. Webhook Sending and Archiving

### 6.1 Webhook Sending
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
        self.logger.info(f"Webhook sent successfully (status: {response.status_code})")
        status = True
    except requests.RequestException as e:
        self.logger.error(f"[send_webhook]: {e}")
    return status
```

### 6.2 Payload Archiving
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

        self.logger.info(f"Payload saved: {filename}")
    except (OSError, json.JSONDecodeError) as e:
        raise OSError(f"Error saving JSON file: {e}")
```

## 7. Cleanup and Shutdown Management

### 7.1 Logout and Connection Closure
```python
def __logout(self) -> None:
    if self.__client:
        try:
            if getattr(self.__client, '_idle_processing', False):
                try:
                    self.__client.idle_done()
                except (IMAPClient.Error, OSError) as e:
                    self.logger.debug(f"Error exiting IDLE: {e}")

            try:
                self.__client.logout()
            except (IMAPClient.AbortError, IMAPClient.Error, OSError) as e:
                self.logger.debug(f"Error during logout: {e}")
            
        except AttributeError as e:
            self.logger.warning(f"Connection already closed: {e}")
        
        finally:
            self.__client = None
```

### 7.2 Final Cleanup
```python
def __del__(self):
    """Closes the executor when the object is destroyed."""
    self.__executor.shutdown(wait=True)
```

## Logical Process Flow

1. **Initialization**
   - Environment variables verification
   - Configuration setup
   - Logger initialization
   - Required directories creation

2. **Connection**
   - IMAP server connection attempt
   - Error handling and retries
   - System folders setup

3. **Main Loop**
   - IDLE mode entry
   - Events check every 5 seconds
   - Unread email processing
   - Reconnection management

4. **Email Processing**
   - Email content reading
   - JSON parsing
   - Payload validation
   - Webhook sending in separate thread
   - Results archiving

5. **Error Handling**
   - Detailed logging
   - Problematic email movement
   - Automatic reconnection
   - Interruption handling

6. **Cleanup**
   - Connection closure
   - Clean logout
   - Thread executor shutdown