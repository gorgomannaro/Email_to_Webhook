# Formato Email per Email to Webhook Converter

## Specifiche Generali

Il corpo dell'email deve:
- Essere in formato plain-text
- Contenere un singolo array JSON valido
- Iniziare con '[' e terminare con ']'
- Contenere almeno due oggetti JSON: azione e autenticazione
- Non contenere altro testo prima o dopo l'array JSON

## Struttura Base
```json
[
  {
    "action": "string",
    "parametri": "valori"
  },
  {
    "user": "string",
    "check": "string"
  }
]
```

### Primo Oggetto: Azione
Il primo oggetto descrive l'azione da eseguire e i suoi parametri.

### Secondo Oggetto: Autenticazione
Il secondo oggetto contiene sempre:
- `user`: identificativo utente
- `check`: token di autenticazione

## Esempi Validi

### 1. Notifica Semplice
```json
[
  {
    "action": "notify",
    "message": "Test alert"
  },
  {
    "user": "0",
    "check": "abc123"
  }
]
```

### 2. Ordine di Trading
```json
[
  {
    "action": "trade",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "quantity": "0.001",
    "price": "45000"
  },
  {
    "user": "1",
    "check": "xyz789"
  }
]
```

### 3. Aggiornamento Configurazione
```json
[
  {
    "action": "config",
    "param": "stop_loss",
    "value": "2.5"
  },
  {
    "user": "0",
    "check": "def456"
  }
]
```

## Esempi NON Validi

### 1. JSON non valido
```
[
  {
    "action": "notify"
    "message": "Manca la virgola"
  },
  {
    "user": "0",
    "check": "abc123"
  }
]
```

### 2. Testo aggiuntivo
```
Ciao,
[
  {
    "action": "notify",
    "message": "Test"
  },
  {
    "user": "0",
    "check": "abc123"
  }
]
Grazie
```

### 3. Manca oggetto autenticazione 
```json
[
  {
    "action": "notify",
    "message": "Test alert"
  }
]
```

## Note Importanti

1. **Formattazione JSON**
   - La formattazione (spazi, interruzioni di riga) non è rilevante
   - L'array può essere su una singola riga o su più righe
   - Gli spazi extra vengono ignorati

2. **Codifica**
   - Utilizzare UTF-8
   - Caratteri speciali devono essere correttamente codificati in JSON

3. **Dimensioni**
   - L'email non dovrebbe superare i 64KB
   - I valori stringa singoli non dovrebbero superare i 1024 caratteri

4. **Sicurezza**
   - Non includere informazioni sensibili nel campo `message`
   - Il token `check` deve essere mantenuto segreto
   - Non utilizzare caratteri speciali nell'ID utente

## Suggerimenti per il Debug

Se il webhook non viene inviato, verificare che:
1. L'email sia in plain-text e non HTML
2. Il JSON sia validato (usare un validatore online)
3. Non ci siano caratteri nascosti prima di '[' o dopo ']'
4. L'oggetto autenticazione sia correttamente formattato
5. Tutti i valori stringa siano tra doppi apici

## Tool di Supporto

Per validare il JSON prima dell'invio:
1. [JSONLint](https://jsonlint.com/)
2. [JSON Editor Online](https://jsoneditoronline.org/)

## Test del Formato

Prima di implementare in produzione, si consiglia di:
1. Testare con una notifica semplice
2. Verificare i log per eventuali errori di parsing
3. Controllare che il webhook venga ricevuto correttamente