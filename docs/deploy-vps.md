# Deploy CodeAssist from Docker Hub

## Quick Deploy

```bash
# SSH into your VPS
ssh ubuntu@vps.openautonomyx.com

# Run Docker container directly
docker run -d \
  --name codeassist \
  -p 8090:8090 \
  -e OPENAI_API_KEY=your-key-here \
  agennext/code-assist:latest

# Access at http://your-vps-ip:8090
```

## With Docker Compose

```bash
# SSH into VPS
ssh ubuntu@vps.openautonomyx.com

# Install Docker if needed
sudo apt update
sudo apt install -y docker.io docker-compose

# Create compose file
cat > docker-compose.yml << 'EOF'
services:
  codeassist:
    image: agennext/code-assist:latest
    ports:
      - "8090:8090"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    restart: unless-stopped
EOF

# Create .env file
echo "OPENAI_API_KEY=your-key" > .env

# Start
docker-compose up -d
```

## With Web UI

```bash
cat > docker-compose.yml << 'EOF'
services:
  api:
    image: agennext/code-assist:latest
    ports:
      - "8090:8090"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    restart: unless-stopped
  
  web:
    image: agennext/code-assist-web:latest
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_AGENNEXT_CODE_ASSIST_API_URL=http://api:8090
    depends_on:
      - api
    restart: unless-stopped
EOF

docker-compose up -d

# API: http://your-vps:8090
# Web: http://your-vps:3000
```