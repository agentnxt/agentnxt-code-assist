#!/bin/bash
# Simple copy-based deployment for VPS
# Run locally, copies files to VPS

VPS_HOST="vps.openautonomyx.com"
VPS_USER="ubuntu"
VPS_PASS="Static@12"
REMOTE_DIR="/home/ubuntu/codeassist"

echo "Copying files to VPS..."

# Create remote directory
sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "mkdir -p $REMOTE_DIR"

# Copy files
sshpass -p "$VPS_PASS" rsync -az --delete \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='dist' \
  --exclude='.venv' \
  /workspace/project/CodeAssist/ \
  "$VPS_USER@$VPS_HOST:$REMOTE_DIR/"

# Install and start
sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "
  cd $REMOTE_DIR
  python3 -m venv venv
  source venv/bin/activate
  pip install -e .
  nohup source venv/bin/activate > server.log 2>&1 & 
  uvicorn agennext_codeassist.server:app --host 0.0.0.0 --port 8090 &
  echo 'Started!'
"

echo "Done! Access at http://$VPS_HOST:8090"