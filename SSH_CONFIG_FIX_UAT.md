# 🔧 SSH Configuration Fix - UAT Environment

**Date:** February 27, 2026  
**Issue:** SSH hostname resolution failing (`Could not resolve hostname miguel-crm`)  
**Solution:** Proper SSH config setup for UAT environment

---

## 🔍 Problem Analysis

### Current Error
```
ssh: Could not resolve hostname miguel-crm: nodename nor servname provided, or not known
```

### Root Causes
1. **Missing SSH config entry** - `miguel-crm` host not properly defined in `~/.ssh/config`
2. **Incorrect hostname/IP** - The Host entry may not point to correct IP address
3. **Missing authentication** - SSH key path not specified or incorrect

---

## ✅ Solution: Fix SSH Configuration

### Step 1: Check Current SSH Config
```bash
cat ~/.ssh/config
# Look for [miguel-crm] or similar entry
```

### Step 2: Create/Update SSH Config

**File location:** `~/.ssh/config` (or `/Users/bthomas/miguel_ssh_config`)

**Add this configuration:**

```ssh
# Production Server
Host prod
    HostName 172.232.118.208
    User root
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null

# UAT Server
Host uat
    HostName <UAT_IP_ADDRESS>
    User root
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null

# Development/Local
Host local
    HostName localhost
    User root
    Port 2222
```

### Step 3: Test SSH Connection

```bash
# Test production
ssh prod
# Expected: Connected to 172.232.118.208

# Test UAT
ssh uat
# Expected: Connected to <UAT_IP>
```

---

## 🎯 For VS Code Remote SSH

### Update VS Code SSH Config

**File:** `/Users/bthomas/miguel_ssh_config`

Replace contents with:

```ssh
# Production
Host prod
    HostName 172.232.118.208
    User root
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null

# UAT - Main Configuration
Host uat
    HostName <UAT_IP_ADDRESS>
    User root
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
    ConnectTimeout 10

# Alternative UAT alias
Host uat-mirror
    HostName <UAT_IP_ADDRESS>
    User root
    IdentityFile ~/.ssh/id_rsa
```

### Update VS Code Settings

**File:** `.vscode/settings.json`

```json
{
  "remote.SSH.configFile": "/Users/bthomas/miguel_ssh_config",
  "remote.SSH.defaultExtensions": [],
  "remote.SSH.enableRemoteCommand": true,
  "remote.SSH.showLoginTerminal": true,
  "remote.SSH.logLevel": "debug"
}
```

---

## 🔑 SSH Key Setup

### Generate SSH Key (if needed)
```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
```

### Copy Public Key to Servers

**For Production:**
```bash
cat ~/.ssh/id_rsa.pub | ssh root@172.232.118.208 'cat >> ~/.ssh/authorized_keys'
```

**For UAT:**
```bash
cat ~/.ssh/id_rsa.pub | ssh root@<UAT_IP> 'cat >> ~/.ssh/authorized_keys'
```

### Set Correct Permissions
```bash
# On local machine
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
chmod 700 ~/.ssh

# On remote servers
ssh root@172.232.118.208 'chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys'
ssh root@<UAT_IP> 'chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys'
```

---

## 🧪 Testing SSH Connection

### Basic SSH Test
```bash
# Test prod
ssh -v prod
# Should show: "Connected to 172.232.118.208"

# Test UAT
ssh -v uat
# Should show: "Connected to <UAT_IP>"
```

### VS Code Remote SSH Test
1. Open VS Code
2. Click "Remote-SSH" in bottom left
3. Select "Connect to Host"
4. Choose **prod** or **uat**
5. Should connect without hostname resolution error

---

## 🚨 Troubleshooting

### Issue: "Could not resolve hostname"
**Solutions:**
1. Check IP address is correct: `ping <IP_ADDRESS>`
2. Verify SSH config syntax: `ssh -G uat` (should show config)
3. Check file permissions: `chmod 644 ~/.ssh/config`

### Issue: "Permission denied (publickey)"
**Solutions:**
1. Verify private key exists: `ls -la ~/.ssh/id_rsa`
2. Check public key on server: `ssh root@<IP> 'cat ~/.ssh/authorized_keys'`
3. Re-add key if needed: `ssh-copy-id -i ~/.ssh/id_rsa.pub root@<IP_ADDRESS>`

### Issue: "Connection timeout"
**Solutions:**
1. Check server is running: `ping <IP_ADDRESS>`
2. Check SSH port: `nmap -p 22 <IP_ADDRESS>` (or use telnet)
3. Check firewall: `sudo ufw status` (on server)
4. Add to SSH config: `ConnectTimeout 30`

### Issue: "Received disconnect from"
**Solutions:**
1. Check SSH service on server: `systemctl status ssh`
2. Check server logs: `tail -f /var/log/auth.log`
3. Restart SSH: `sudo systemctl restart ssh`

---

## 📋 Configuration Checklist

### Local Machine
- [ ] SSH key generated (`~/.ssh/id_rsa`)
- [ ] SSH config file created (`~/.ssh/config`)
- [ ] Correct permissions set (600 on key, 644 on config)
- [ ] VS Code SSH extension installed
- [ ] VS Code config points to correct SSH config file

### Production Server (172.232.118.208)
- [ ] SSH service running
- [ ] Public key in `~/.ssh/authorized_keys`
- [ ] Correct permissions on SSH directories
- [ ] Port 22 open and accessible
- [ ] SSH connection test passed

### UAT Server
- [ ] SSH service running
- [ ] Public key in `~/.ssh/authorized_keys`
- [ ] Correct permissions on SSH directories
- [ ] Port 22 open and accessible
- [ ] SSH connection test passed
- [ ] IP address documented

---

## 📝 Required Information

To complete UAT setup, provide:
1. **UAT Server IP Address** - `<UAT_IP_ADDRESS>`
2. **UAT Server User** - (usually `root` or `ubuntu`)
3. **UAT Server Port** - (usually 22)
4. **Authentication Method** - Key-based or password
5. **VPN Required?** - If yes, configure before SSH

---

## 🎯 Quick Reference

### Connect to Production
```bash
# Terminal
ssh prod

# VS Code
Remote-SSH: Connect to Host → prod
```

### Connect to UAT
```bash
# Terminal
ssh uat

# VS Code
Remote-SSH: Connect to Host → uat
```

### Verify Connection
```bash
# Check if host config is correct
ssh -G prod    # Shows config for 'prod' host
ssh -G uat     # Shows config for 'uat' host

# Test connection (verbose)
ssh -v prod    # Verbose output for production
ssh -v uat     # Verbose output for UAT
```

---

## 🔐 Security Notes

### In Production
- [ ] Never hardcode passwords in config
- [ ] Use SSH key-based authentication only
- [ ] Restrict key permissions (600)
- [ ] Use `StrictHostKeyChecking yes` (accept after first connection)
- [ ] Enable SSH logging for audit trail

### For Development
- [ ] Can use `StrictHostKeyChecking no` for dev/UAT
- [ ] Never share private keys
- [ ] Rotate keys periodically
- [ ] Keep SSH version updated

---

## 📞 Next Steps

1. **Identify UAT IP** - Get the actual IP address of UAT server
2. **Update SSH config** - Add UAT host entry with correct IP
3. **Test connection** - Verify SSH works from terminal
4. **Update VS Code** - Configure VS Code for remote SSH
5. **Test VS Code** - Connect through Remote-SSH extension

---

**Status:** Ready for implementation  
**Last Updated:** February 27, 2026  
**Next Step:** Add actual UAT IP address and test connection
