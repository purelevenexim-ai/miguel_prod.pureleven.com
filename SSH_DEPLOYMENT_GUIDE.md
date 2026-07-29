# 🚀 SSH Configuration Deployment Guide

**Date:** February 27, 2026  
**Status:** ✅ READY FOR IMMEDIATE DEPLOYMENT  
**UAT IP:** 172.232.118.208  
**Prod IP:** 172.105.48.142

---

## ⚡ IMMEDIATE DEPLOYMENT (2 minutes)

### Step 1: Copy the SSH Configuration
```bash
# Copy from the ready-to-use config file
cp /opt/pureleven/SSH_CONFIG_READY_TO_USE ~/.ssh/config

# Set correct permissions
chmod 644 ~/.ssh/config
```

### Step 2: Verify SSH Keys Exist
```bash
# Check for UAT key
ls -la ~/.ssh/uat
# Should show: -rw------- 1 user user ... uat

# Check for Production key
ls -la ~/.ssh/prod
# Should show: -rw------- 1 user user ... prod

# If keys don't exist, copy them from secure location
```

### Step 3: Test Connections
```bash
# Test UAT (172.232.118.208)
ssh uat
# Expected: Connected to UAT server

# Test Production (172.105.48.142)
ssh prod
# Expected: Connected to production server
```

### Step 4: Use in VS Code
1. Open VS Code
2. Click Remote-SSH icon (bottom left)
3. Click "Connect to Host..."
4. Select **uat** or **prod**
5. Should connect without errors ✓

---

## 📋 Configuration Details

### UAT Server
```
Host:          uat
IP Address:    172.232.118.208
Username:      root
SSH Key:       ~/.ssh/uat
Port:          22
Access:        For staging/testing
```

### Production Server
```
Host:          prod
IP Address:    172.105.48.142
Username:      root
SSH Key:       ~/.ssh/prod
Port:          22
Access:        For production system
```

---

## 🔐 SSH Key Setup

### If Keys Already Exist (Most Common)
```bash
# Verify keys are in place
ls ~/.ssh/uat
ls ~/.ssh/prod

# Verify permissions (should be 600)
chmod 600 ~/.ssh/uat
chmod 600 ~/.ssh/prod

# Done! Just copy the config file
```

### If Keys Need to be Created
```bash
# Generate UAT key
ssh-keygen -t rsa -b 4096 -f ~/.ssh/uat -N ""
chmod 600 ~/.ssh/uat

# Generate Production key
ssh-keygen -t rsa -b 4096 -f ~/.ssh/prod -N ""
chmod 600 ~/.ssh/prod

# Then copy keys to servers (ask your DevOps team)
```

### If Keys Need to be Added to Servers
```bash
# Add UAT key
ssh-copy-id -i ~/.ssh/uat.pub -o "StrictHostKeyChecking=no" root@172.232.118.208

# Add Production key
ssh-copy-id -i ~/.ssh/prod.pub -o "StrictHostKeyChecking=no" root@172.105.48.142

# Then set permissions on servers
ssh uat 'chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys'
ssh prod 'chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys'
```

---

## ✅ Verification Checklist

### Configuration File
- [ ] `~/.ssh/config` exists
- [ ] Contains both `Host uat` and `Host prod` entries
- [ ] Permissions are 644: `chmod 644 ~/.ssh/config`
- [ ] SSH syntax is correct: `ssh -G uat` works
- [ ] SSH syntax is correct: `ssh -G prod` works

### SSH Keys
- [ ] `~/.ssh/uat` exists with 600 permissions
- [ ] `~/.ssh/prod` exists with 600 permissions
- [ ] Both keys are RSA format
- [ ] Public keys are on remote servers

### Connectivity
- [ ] Can ping UAT: `ping 172.232.118.208`
- [ ] Can ping Prod: `ping 172.105.48.142`
- [ ] Can SSH to UAT: `ssh uat` → prompt appears
- [ ] Can SSH to Prod: `ssh prod` → prompt appears

### VS Code Integration
- [ ] Remote-SSH extension installed
- [ ] Can see "uat" in host dropdown
- [ ] Can see "prod" in host dropdown
- [ ] Can connect without errors
- [ ] Can open remote folder

---

## 📊 Quick Reference

### Connect to UAT
```bash
# Terminal
ssh uat

# VS Code
Remote-SSH: Connect to Host → uat
```

### Connect to Production
```bash
# Terminal
ssh prod

# VS Code
Remote-SSH: Connect to Host → prod
```

### Check Configuration
```bash
# Show complete configuration for UAT
ssh -G uat

# Show complete configuration for Production
ssh -G prod

# Verbose connection test (debugging)
ssh -vvv uat
ssh -vvv prod
```

### Update Configuration
```bash
# Edit SSH config
nano ~/.ssh/config

# Verify syntax after editing
ssh -G uat
ssh -G prod
```

---

## 🚨 Troubleshooting

### Issue: "Could not resolve hostname"
```bash
# Verify host is in config
ssh -G uat
# Should show HostName: 172.232.118.208

# Verify config file syntax
cat ~/.ssh/config | grep -A 5 "Host uat"
```

### Issue: "Permission denied (publickey)"
```bash
# Verify SSH key exists
ls -la ~/.ssh/uat
# Should show: -rw------- (permissions 600)

# Check if key is on server
ssh uat 'cat ~/.ssh/authorized_keys'
# Should show your public key

# If not, add it:
ssh-copy-id -i ~/.ssh/uat.pub root@172.232.118.208
```

### Issue: "Connection refused"
```bash
# Verify server is running
ping 172.232.118.208

# Check SSH port is open
nc -zv 172.232.118.208 22

# Check server SSH service
ssh uat 'systemctl status ssh'
```

### Issue: "Connection timeout"
```bash
# Verify IP is reachable
ping 172.232.118.208

# Check with verbose output
ssh -vvv uat

# Increase timeout in config (add to Host uat section):
# ConnectTimeout 30
```

---

## 🎯 For VS Code Users

### Update VS Code Settings
```json
{
  "remote.SSH.configFile": "~/.ssh/config",
  "remote.SSH.defaultExtensions": [],
  "remote.SSH.enableRemoteCommand": true,
  "remote.SSH.showLoginTerminal": true,
  "remote.SSH.logLevel": "debug"
}
```

### Test Connection in VS Code
1. Open Command Palette (Cmd+Shift+P)
2. Type: "Remote-SSH: Connect to Host"
3. Should see "uat" and "prod" in dropdown
4. Click either one
5. Should open remote connection
6. Should see remote filesystem in Explorer

---

## 📝 Step-by-Step Deployment

### For New Team Member

1. **Get SSH Keys**
   ```bash
   # Receive ~/.ssh/uat and ~/.ssh/prod from IT/DevOps
   # Verify they're in your ~/.ssh directory
   ls ~/.ssh/uat ~/.ssh/prod
   ```

2. **Copy SSH Config**
   ```bash
   cp /opt/pureleven/SSH_CONFIG_READY_TO_USE ~/.ssh/config
   chmod 644 ~/.ssh/config
   ```

3. **Test Terminal Access**
   ```bash
   ssh uat
   # Type 'exit' to disconnect
   
   ssh prod
   # Type 'exit' to disconnect
   ```

4. **Install VS Code Remote-SSH**
   - Open VS Code
   - Extensions → Search "Remote - SSH"
   - Install by Microsoft
   - Reload window

5. **Connect in VS Code**
   - Click Remote-SSH icon
   - Select "Connect to Host"
   - Choose "uat" or "prod"
   - Done!

---

## 🔐 Security Notes

### Best Practices
- ✅ Use SSH key-based authentication (not passwords)
- ✅ Keep private keys secure (600 permissions)
- ✅ Never share private keys
- ✅ Use separate keys for UAT and Production
- ✅ Rotate keys periodically

### What This Config Does
- ✅ Prevents password prompts
- ✅ Uses key-based authentication
- ✅ Automatically manages SSH keys
- ✅ Keeps connections alive
- ✅ Uses compression for faster transfers

### What This Config Does NOT Do
- ❌ Does not store passwords (good!)
- ❌ Does not accept password auth (good!)
- ❌ Does not require passphrase (configured without one)
- ❌ Does not create/generate keys (you must have them)

---

## 📞 Troubleshooting Resources

If you have issues:

1. **Check SSH Config**: See TROUBLESHOOTING section above
2. **Read SSH Guides**: See other SSH_*.md files in /opt/pureleven/
3. **Run Verbose Test**: `ssh -vvv uat` shows detailed info
4. **Ask Team**: Share output of `ssh -vvv uat` and `~/.ssh/config` content

---

## ✨ Success Indicators

After deployment:
- ✅ `ssh uat` works in terminal
- ✅ `ssh prod` works in terminal
- ✅ VS Code shows both hosts in dropdown
- ✅ Can connect via VS Code Remote-SSH
- ✅ Can open remote folder in VS Code
- ✅ Can edit files on remote servers
- ✅ No "Could not resolve hostname" errors

---

## 📋 Deployment Checklist

- [ ] SSH configuration file obtained
- [ ] SSH keys obtained and placed in ~/.ssh/
- [ ] Config file copied to ~/.ssh/config
- [ ] Permissions set correctly (644 on config, 600 on keys)
- [ ] Terminal SSH test passed (ssh uat, ssh prod)
- [ ] VS Code Remote-SSH extension installed
- [ ] VS Code connection test passed
- [ ] Can open remote folder and see files
- [ ] Team members have same setup

---

**Status:** ✅ READY FOR DEPLOYMENT  
**Deployment Time:** 5-10 minutes  
**Difficulty:** Easy  
**Support:** See /opt/pureleven/SSH_*.md files

Ready to deploy? Start with Step 1 above! 🚀
