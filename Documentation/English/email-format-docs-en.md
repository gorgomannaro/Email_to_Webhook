# Email Format for Email to Webhook Converter

## General Specifications

The email body must:
- Be in plain-text format
- Contain a single valid JSON array
- Start with '[' and end with ']'
- Contain at least two JSON objects: action and authentication
- Have no text before or after the JSON array

## Base Structure
```json
[
  {
    "action": "string",
    "parameters": "values"
  },
  {
    "user": "string",
    "check": "string"
  }
]
```

### First Object: Action
The first object describes the action to execute and its parameters.

### Second Object: Authentication
The second object always contains:
- `user`: user identifier
- `check`: authentication token

## Valid Examples

### 1. Simple Notification
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

### 2. Trading Order
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

### 3. Configuration Update
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

## Invalid Examples

### 1. Invalid JSON
```
[
  {
    "action": "notify"
    "message": "Missing comma"
  },
  {
    "user": "0",
    "check": "abc123"
  }
]
```

### 2. Additional Text
```
Hello,
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
Thanks
```

### 3. Missing Authentication Object
```json
[
  {
    "action": "notify",
    "message": "Test alert"
  }
]
```

## Important Notes

1. **JSON Formatting**
   - Formatting (spaces, line breaks) is not relevant
   - The array can be on a single line or multiple lines
   - Extra spaces are ignored

2. **Encoding**
   - Use UTF-8
   - Special characters must be properly encoded in JSON

3. **Size**
   - Email should not exceed 64KB
   - Single string values should not exceed 1024 characters

4. **Security**
   - Do not include sensitive information in the `message` field
   - The `check` token must be kept secret
   - Do not use special characters in the user ID

## Debugging Tips

If the webhook is not sent, verify that:
1. The email is in plain-text and not HTML
2. The JSON is validated (use an online validator)
3. There are no hidden characters before '[' or after ']'
4. The authentication object is properly formatted
5. All string values are in double quotes

## Support Tools

To validate JSON before sending:
1. [JSONLint](https://jsonlint.com/)
2. [JSON Editor Online](https://jsoneditoronline.org/)

## Format Testing

Before implementing in production, it is recommended to:
1. Test with a simple notification
2. Check logs for any parsing errors
3. Verify that the webhook is received correctly