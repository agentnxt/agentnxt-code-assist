#!/bin/bash
# Deploy CodeAssist to VPS
# Usage: ./deploy-vps.sh

set -e

VPS_HOST="vps.openautonomyx.com"
VPS_USER="ubuntu"
VPS_PASS="Static@12"  # Set your password
APP_DIR="/opt/codeassist"

echo "Deploying to $VPS_USER@$VPS_HOST..."

# Create remote directory
sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" << EOF
  sudo mkdir -p $APP_DIR
  sudo chown $VPS_USER:$VPS_USER $APP_DIR
  cd $APP_DIR
  git clone https://github.com/AGenNext/CodeAssist.git .
  cd ..
  rm -rf CodeAssist
  mv CodeAssist.codeassist $APP_DIR
EOF

echo "Installing dependencies..."
sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "
  cd $APP_DIR
  python3 -m venv venv
  source venv/bin/activate
  pip install -e .
"

echo "Starting service..."
sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "
  sudo tee /etc/systemd/system/codeassist.service > /dev/null << SYSTEMD
[Unit]
Description=CodeAssist API
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/agennext-code-assist serve --host 0.0.0.0 --port 8090
Restart=always

[Install]
WantedBy=multi-user.target
SYSTEMD

  sudo systemctl daemon-reload
  sudo systemctl enable codeassist
  sudo systemctl start codeassist
"

echo "Deployment complete!"
echo "API: http://$VPS_HOST:8090"
echo "Docs: http://$VPS_HOST:8090/docs"