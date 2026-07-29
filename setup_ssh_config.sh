#!/bin/bash

#############################################################################
# SSH Configuration Setup Script for VS Code Remote SSH
# Purpose: Fix SSH connection issues for production and UAT environments
# Usage: ./setup_ssh_config.sh
#############################################################################

set -e

echo "=========================================="
echo "SSH Configuration Setup for Remote SSH"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect OS
OS=$(uname -s)
if [[ "$OS" == "Darwin" ]]; then
    echo "Detected: macOS"
    SSH_CONFIG="$HOME/.ssh/config"
    VS_CONFIG="$HOME/miguel_ssh_config"
elif [[ "$OS" == "Linux" ]]; then
    echo "Detected: Linux"
    SSH_CONFIG="$HOME/.ssh/config"
    VS_CONFIG="$HOME/miguel_ssh_config"
else
    echo "Unknown OS. Please configure SSH manually."
    exit 1
fi

echo ""
echo "Step 1: Create SSH directory if needed..."
if [ ! -d "$HOME/.ssh" ]; then
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    echo -e "${GREEN}✓${NC} Created ~/.ssh directory"
else
    echo -e "${GREEN}✓${NC} ~/.ssh directory exists"
fi

echo ""
echo "Step 2: Check if SSH key exists..."
if [ ! -f "$HOME/.ssh/id_rsa" ]; then
    echo -e "${YELLOW}⚠${NC} SSH key not found. Generating new key..."
    ssh-keygen -t rsa -b 4096 -f "$HOME/.ssh/id_rsa" -N "" -C "$(whoami)@$(hostname)"
    chmod 600 "$HOME/.ssh/id_rsa"
    chmod 644 "$HOME/.ssh/id_rsa.pub"
    echo -e "${GREEN}✓${NC} SSH key generated at ~/.ssh/id_rsa"
else
    echo -e "${GREEN}✓${NC} SSH key exists"
fi

echo ""
echo "Step 3: Create VS Code SSH config file..."

# Create the SSH config file for VS Code
cat > "$VS_CONFIG" << 'EOF'
# VS Code Remote SSH Configuration
# Created for Miguel CRM Platform

# Production Server (Linode)
Host prod
    HostName 172.232.118.208
    User root
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
    ConnectTimeout 10
    ServerAliveInterval 60
    ServerAliveCountMax 3

# UAT Server (To be configured)
Host uat
    HostName 192.168.1.100
    User root
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
    ConnectTimeout 10
    ServerAliveInterval 60
    ServerAliveCountMax 3

# Local/Development
Host local
    HostName localhost
    User root
    Port 2222
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
EOF

chmod 644 "$VS_CONFIG"
echo -e "${GREEN}✓${NC} Created VS Code SSH config at $VS_CONFIG"

echo ""
echo "Step 4: Update/Create main SSH config..."

# Backup existing config if it exists
if [ -f "$SSH_CONFIG" ]; then
    cp "$SSH_CONFIG" "$SSH_CONFIG.backup.$(date +%s)"
    echo -e "${YELLOW}⚠${NC} Backed up existing SSH config"
fi

# Create/update the main SSH config
cat > "$SSH_CONFIG" << 'EOF'
# SSH Configuration for Miguel CRM
# Updated February 27, 2026

# Production Server
Host prod
    HostName 172.232.118.208
    User root
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
    ConnectTimeout 10
    ServerAliveInterval 60
    ServerAliveCountMax 3

# UAT Server
Host uat
    HostName 192.168.1.100
    User root
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
    ConnectTimeout 10
    ServerAliveInterval 60
    ServerAliveCountMax 3

# Local/Development
Host local
    HostName localhost
    User root
    Port 2222
    IdentityFile ~/.ssh/id_rsa

# Global SSH options
Host *
    AddKeysToAgent yes
    UseKeychain yes
    IgnoreUnknown UseKeychain
EOF

chmod 644 "$SSH_CONFIG"
echo -e "${GREEN}✓${NC} Updated SSH config at $SSH_CONFIG"

echo ""
echo "Step 5: Set correct permissions..."
chmod 700 "$HOME/.ssh"
chmod 600 "$HOME/.ssh/id_rsa"
chmod 644 "$HOME/.ssh/id_rsa.pub"
chmod 644 "$HOME/.ssh/config"
echo -e "${GREEN}✓${NC} Permissions set correctly"

echo ""
echo "Step 6: Verify SSH configuration..."
echo -e "\n${YELLOW}Configuration for 'prod':${NC}"
ssh -G prod 2>/dev/null | head -5 || echo "Error reading config"

echo -e "\n${YELLOW}Configuration for 'uat':${NC}"
ssh -G uat 2>/dev/null | head -5 || echo "Error reading config"

echo ""
echo "=========================================="
echo "SSH Setup Complete!"
echo "=========================================="
echo ""
echo "Configuration files created:"
echo "  - VS Code SSH config: $VS_CONFIG"
echo "  - Main SSH config: $SSH_CONFIG"
echo ""
echo "Next steps:"
echo "  1. Test SSH connection:"
echo "     ssh -v prod    # Test production"
echo "     ssh -v uat     # Test UAT"
echo ""
echo "  2. Copy SSH key to servers:"
echo "     ssh-copy-id -i ~/.ssh/id_rsa.pub root@172.232.118.208  # Prod"
echo "     ssh-copy-id -i ~/.ssh/id_rsa.pub root@<UAT_IP>         # UAT"
echo ""
echo "  3. Update UAT IP in SSH config:"
echo "     Edit $VS_CONFIG and $SSH_CONFIG"
echo "     Replace: HostName 192.168.1.100 (line ~20)"
echo "     With:    HostName <ACTUAL_UAT_IP>"
echo ""
echo "  4. Open VS Code and connect:"
echo "     Command Palette → Remote-SSH: Connect to Host → prod or uat"
echo ""
echo -e "${GREEN}Done!${NC}"
