# Email to Webhook Converter
## Installation and Configuration Guide

This guide will help you install and configure the Email to Webhook converter on Ubuntu Server 24.04 or higher.

## License
This software is released under the MIT License.

## Prerequisites
- Ubuntu Server 24.04 or higher
- Python 3.10 or higher
- pip3
- virtualenv

## 1. Environment Setup
### 1.1 System Requirements Installation
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv -y
```

### 1.2 Virtual Environment Creation
```bash
mkdir -p ~/venv/crypto/BeBo_bridge/modules/email_to_webhook
cd ~/venv/crypto
python3 -m venv .
source bin/activate
```

### 1.3 Python Dependencies Installation
```bash
pip install imapclient requests
```

## 2. Software Installation
### 2.1 File Copying
Create the following files in the `~/venv/crypto/BeBo_bridge/modules/email_to_webhook/` directory:

1. `email_to_webhook_converter.py`
2. `email_to_webhook_helper.py`
3. `.env` (configuration file)

### 2.2 Environment Variables Configuration
Create the `.env` file in your home directory:
```bash
nano ~/.env
```

Insert the following variables, replacing the values between <...> with your data:
```bash
ADMIN_CHECK='<authentication.key>'
EMAIL_PORT=993
EMAIL_SERVER='<email.provider.address>'
EMAIL_ACCOUNT='<user.account@email.provider>'
EMAIL_PASSWORD='<user.password>'
```

### 2.3 Webhook URLs Configuration
Edit the `email_to_webhook_converter.py` file and update the `WEBHOOK_ADDRESSES` dictionary with your endpoints:
```python
WEBHOOK_ADDRESSES = {
    "SERVER_1": 'https://<your-webhook-endpoint>',
    # Add other servers if needed
}
```

## 3. Execution Modes

### 3.1 Standalone Mode
To run the software in standalone mode:
```bash
cd ~/venv/crypto/BeBo_bridge/modules/email_to_webhook
source ~/venv/crypto/bin/activate
python email_to_webhook_converter.py
```

### 3.2 Service Mode (Systemd)
To install the software as a system service:

1. Create the service file:
```bash
sudo nano /etc/systemd/system/email-webhook.service
```

2. Copy the content of `email-webhook.service` replacing `<username>` with your username:
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

3. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable email-webhook
sudo systemctl start email-webhook
```

4. Check service status:
```bash
sudo systemctl status email-webhook
```

## 4. Monitoring and Logs

### 4.1 Software Logs
Logs are saved in:
```
~/venv/crypto/BeBo_bridge/modules/email_to_webhook/log/email_monitor.log
```

### 4.2 System Logs (service mode)
To view system logs:
```bash
sudo journalctl -u email-webhook -f
```

## 5. Archived Webhooks
Processed webhooks are saved in:
```
~/venv/crypto/BeBo_bridge/modules/email_to_webhook/webhook/
```

## 6. Troubleshooting

### 6.1 Service Won't Start
Check:
1. File permissions:
```bash
chmod 600 ~/.env
chmod 644 ~/venv/crypto/BeBo_bridge/modules/email_to_webhook/*.py
```

2. System logs:
```bash
sudo journalctl -u email-webhook -n 50
```

### 6.2 Connection Errors
- Verify credentials in the `.env` file
- Check if IMAP port (993) is accessible
- Verify that two-factor authentication is disabled for the email account

## 7. Maintenance

### 7.1 Software Update
1. Stop the service:
```bash
sudo systemctl stop email-webhook
```

2. Update Python files
3. Restart the service:
```bash
sudo systemctl start email-webhook
```

### 7.2 Log Rotation
Logs are automatically rotated daily and kept for 30 days.