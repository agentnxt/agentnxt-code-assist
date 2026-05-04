# VPS Deployment Scripts

Run these on your local machine to deploy to `ubuntu@Static@12@vps.openautonomyx.com`.

## Option 1: Git Clone (Recommended)

```bash
# SSH into the server
ssh ubuntu@vps.openautonomyx.com

# Clone and setup
sudo mkdir -p /opt/codeassist
cd /opt/codeassist
git clone https://github.com/AGenNext/CodeAssist.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Create systemd service
sudo nano /etc/systemd/system/codeassist.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable codeassist
sudo systemctl start codeassist
```

Systemd service content:
```ini
[Unit]
Description=CodeAssist API
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/codeassist
Environment=PATH=/opt/codeassist/venv/bin
ExecStart=/opt/codeassist/venv/bin/agennext-code-assist serve --host 0.0.0.0 --port 8090
Restart=always

[Install]
WantedBy=multi-user.target
```

## Option 2: Docker

```bash
# On VPS
sudo apt update
sudo apt install -y docker.io docker-compose

# Clone and start
git clone https://github.com/AGenNext/CodeAssist.git
cd CodeAssist
sudo docker-compose up -d

# Access at http://your-vps-ip:8090
```

## Option 3: Python Directly

```bash
# SSH into server
ssh ubuntu@vps.openautonomyx.com

# Install
git clone https://github.com/AGenNext/CodeAssist.git
cd CodeAssist
pip install -e .

# Run in screen/tmux or with nohup
nohup agennext-code-assist serve --host 0.0.0.0 --port 8090 > server.log 2>&1 &
```

## Access

- API: http://vps.openautonomyx.com:8090
- Docs: http://vps.openautonomyx.com:8090/docs