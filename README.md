# Email_to_Webhook Converter

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Ubuntu 24.04](https://img.shields.io/badge/Ubuntu-24.04-orange.svg)](https://releases.ubuntu.com/24.04/)

A robust Python application that converts email alerts into webhooks. Perfect for automating trading strategies or notification systems that rely on email triggers but require webhook integration.

## Features

- **Email Monitoring**: Continuously monitors an email inbox for new messages
- **JSON Parsing**: Extracts and validates JSON payloads from email content
- **Webhook Conversion**: Transforms email content into webhook calls
- **Error Handling**: Robust error management with automatic recovery
- **Flexible Deployment**: Run as standalone application or system service
- **Comprehensive Logging**: Detailed logging system with rotation
- **Archive System**: Automatic archiving of processed messages and webhooks

## Prerequisites

- Ubuntu Server 24.04 or higher
- Python 3.10 or higher
- `pip3` and `virtualenv`
- IMAP-enabled email account
- Webhook endpoint(s)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/email-to-webhook.git
cd email-to-webhook
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
nano .env
```

5. Configure your environment variables:
```bash
ADMIN_CHECK='<authentication.key>'
EMAIL_PORT=993
EMAIL_SERVER='<email.provider.name>'
EMAIL_ACCOUNT='<user.account@email.provider>'
EMAIL_PASSWORD='<user.password>'
```

## Usage

### Standalone Mode
```bash
python email_to_webhook_converter.py
```

### Service Mode
1. Install the systemd service:
```bash
sudo cp email-webhook.service /etc/systemd/system/
sudo systemctl daemon-reload
```

2. Start the service:
```bash
sudo systemctl enable email-webhook
sudo systemctl start email-webhook
```

3. Check service status:
```bash
sudo systemctl status email-webhook
```

## Email Format

Messages must contain a valid JSON array with at least two objects:

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

See [FORMAT](Documentation/English/email-format-docs-en.md) for detailed message format specifications.

## Configuration

### Webhook Endpoints
Edit `email_to_webhook_converter.py` to configure your webhook endpoints:

```python
WEBHOOK_ADDRESSES = {
    "SERVER_1": 'https://<your-webhook-endpoint>',
    # Add additional endpoints as needed
}
```

### Logging
Logs are stored in:
- Application logs: `~/venv/crypto/BeBo_bridge/modules/email_to_webhook/log/`
- System logs: `journalctl -u email-webhook`

## Project Structure

```
email-to-webhook/
├── email_to_webhook_converter.py
├── email_to_webhook_helper.py
├── .env
├── email-webhook.service
├── requirements.txt
├── LICENSE
└── docs/
    ├── FORMAT.md
    └── INSTALLATION.md
```

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE.md) file for details.

## Acknowledgments

- [IMAPClient](https://github.com/mjs/imapclient) for robust IMAP implementation
- Trading community for inspiration and testing
