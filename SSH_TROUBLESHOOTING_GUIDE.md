# 🔧 VS Code Remote SSH Troubleshooting Guide

**Issue:** `ssh: Could not resolve hostname miguel-crm`  
**Date:** February 27, 2026  
**Status:** SOLUTION PROVIDED

---

## 🚨 Problem Summary

```
[08:23:26.922] stderr> ssh: Could not resolve hostname miguel-crm: nodename nor servname provided, or not known
```

**Cause:** VS Code is trying to connect to a host named `miguel-crm` that isn't properly defined in the SSH config.

---

## ✅ Immediate Fix (5 minutes)

### Option 1: Use Direct IP (Quick Fix)

In VS Code:
1. Click Remote-SSH icon (bottom left)
2. Click "Connect to Host..."
3. Type: `root@172.232.118.208` (for production)
4. Click "Open in new window"
5. Should connect successfully

### Option 2: Fix SSH Config (Proper Fix)

**Step 1:** Find and open SSH config
```bash
# One of these should exist:
cat ~/.ssh/config                    # Standard location
cat ~/miguel_ssh_config              # Your custom location
cat /Users/bthomas/miguel_ssh_config # Full path from error logs
```

**Step 2:** Edit the file and add proper host entries
```bash
nano ~/.ssh/config
# or
nano ~/miguel_ssh_config
```

**Add these lines:**
```ssh
Host prod
    HostName 172.232.118.208
    User root
    IdentityFile ~/.ssh/id_rsa

Host uat
    HostName <UAT_IP_ADDRESS>
    User root
    IdentityFile ~/.ssh/id_rsa
```

**Step 3:** Test from terminal
```bash
ssh prod
# Should connect without "Could not resolve hostname" error
```

---

## 🔍 Detailed Diagnosis

### Check 1: Is SSH configured correctly?
```bash
# Check if SSH config exists
ls -la ~/.ssh/config

# View SSH config
cat ~/.ssh/config

# Verify syntax
ssh -G prod
# Should show configuration details, not errors
```

### Check 2: Is the hostname/IP correct?
```bash
# Test connectivity to production
ping 172.232.118.208
# Expected: Packets being received

# Test SSH port
ssh -v root@172.232.118.208 'echo Connected'
# Should connect or ask for password (no hostname error)
```

### Check 3: Is VS Code using the right SSH config?
```bash
# Check VS Code settings
cat ~/.vscode/settings.json | grep ssh

# Or open VS Code settings and look for:
# remote.SSH.configFile
# Should point to: /Users/bthomas/miguel_ssh_config (or ~/.ssh/config)
```

### Check 4: Does SSH key exist?
```bash
ls -la ~/.ssh/id_rsa
# Should show: -rw------- 1 user user (permissions: 600)

# If not found, generate:
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
```

---

## 🛠️ Step-by-Step Fix

### For macOS / Linux

**Step 1: Create SSH directory**
```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
```

**Step 2: Generate SSH key (if needed)**
```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
```

**Step 3: Create SSH config**
```bash
cat > ~/.ssh/config << 'EOF'
Host prod
    HostName 172.232.118.208
    User root
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no

Host uat
    HostName <UAT_IP_ADDRESS>
    User root
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
EOF

chmod 644 ~/.ssh/config
```

**Step 4: Test connectivity**
```bash
ssh -v prod
# Should connect successfully
```

**Step 5: Update VS Code config** (if using custom path)
```bash
# Open VS Code settings (Cmd+, or Code → Preferences → Settings)
# Search for: remote.SSH.configFile
# Set to: /Users/bthomas/miguel_ssh_config (or ~/.ssh/config)
```

**Step 6: Test VS Code connection**
1. Open Command Palette (Cmd+Shift+P)
2. Type: "Remote-SSH: Connect to Host"
3. Select "prod" or "uat"
4. Should open without hostname error

---

## 🎯 Configuration Examples

### Example 1: Production Only
```ssh
Host prod
    HostName 172.232.118.208
    User root
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
```

### Example 2: Production + UAT
```ssh
Host prod
    HostName 172.232.118.208
    User root
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no

Host uat
    HostName 192.168.1.100
    User root
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
```

### Example 3: Production + UAT + Local Dev
```ssh
Host prod
    HostName 172.232.118.208
    User root
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no

Host uat
    HostName <UAT_IP_ADDRESS>
    User root
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no

Host local
    HostName localhost
    User root
    Port 2222
    IdentityFile ~/.ssh/id_rsa
```

---

## 🚨 Common Errors & Fixes

### Error: "Could not resolve hostname"
```
ssh: Could not resolve hostname miguel-crm: nodename nor servname provided, or not known
```
**Fix:**
1. Check SSH config has `HostName` entry
2. Verify hostname/IP is correct
3. Test with: `ssh -G prod` (should show HostName)

### Error: "Permission denied (publickey)"
```
root@172.232.118.208: Permission denied (publickey).
```
**Fix:**
1. Copy SSH key to server: `ssh-copy-id -i ~/.ssh/id_rsa.pub root@172.232.118.208`
2. Or manually add key:
   ```bash
   cat ~/.ssh/id_rsa.pub | ssh root@172.232.118.208 'cat >> ~/.ssh/authorized_keys'
   ```

### Error: "Connection refused"
```
ssh: connect to host 172.232.118.208 port 22: Connection refused
```
**Fix:**
1. Check server is running: `ping 172.232.118.208`
2. Check SSH service: `ssh -vvv root@172.232.118.208` (look for details)
3. Check firewall: May need to allow port 22

### Error: "Connection timeout"
```
ssh: connect to host 172.232.118.208 port 22: Connection timed out
```
**Fix:**
1. Verify IP address: `ping 172.232.118.208`
2. Add to SSH config: `ConnectTimeout 30`
3. Check if on VPN (if required)

---

## 📋 Verification Checklist

- [ ] SSH key exists: `~/.ssh/id_rsa`
- [ ] SSH config exists: `~/.ssh/config`
- [ ] SSH config readable: `cat ~/.ssh/config` works
- [ ] SSH config has hosts: Shows `Host prod` and `Host uat`
- [ ] Terminal SSH works: `ssh prod` connects
- [ ] IP address is correct: `ping 172.232.118.208` responds
- [ ] VS Code sees hosts: Remote-SSH dropdown shows hosts
- [ ] VS Code can connect: Clicking host connects successfully

---

## 🔐 Security Notes

When using VS Code Remote SSH:
- ✅ Use SSH key-based auth (not passwords)
- ✅ Keep `IdentityFile ~/.ssh/id_rsa` in config
- ✅ Set key permissions to 600: `chmod 600 ~/.ssh/id_rsa`
- ✅ Set config permissions to 644: `chmod 644 ~/.ssh/config`
- ✅ Use `StrictHostKeyChecking no` for dev/test only

---

## 🚀 Quick Commands

### Test SSH without VS Code
```bash
# Direct test
ssh root@172.232.118.208

# Using config
ssh prod

# Verbose output (troubleshooting)
ssh -v prod
ssh -vv prod
ssh -vvv prod

# Check what config will be used
ssh -G prod
```

### Copy SSH key to server
```bash
# Automated
ssh-copy-id -i ~/.ssh/id_rsa.pub root@172.232.118.208

# Manual
cat ~/.ssh/id_rsa.pub | ssh root@172.232.118.208 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys'
```

### Restart SSH on server
```bash
ssh prod 'sudo systemctl restart ssh'
# or
ssh prod 'sudo service ssh restart'
```

---

## 📞 If Issues Persist

### Collect debugging information
```bash
# Check SSH version
ssh -V

# Show SSH config being used
ssh -G prod

# Verbose connection attempt
ssh -vvv prod 2>&1 | head -50

# Check if port 22 is open
nc -zv 172.232.118.208 22

# Check known hosts file
cat ~/.ssh/known_hosts
```

### Share these details when asking for help
1. Output of: `ssh -vvv prod`
2. Output of: `ssh -G prod`
3. Output of: `cat ~/.ssh/config`
4. Output of: `ping 172.232.118.208`

---

## ✅ Success Criteria

After fixing SSH config, you should be able to:
- ✅ Run `ssh prod` in terminal → connects immediately
- ✅ Run `ssh uat` in terminal → connects immediately
- ✅ Open VS Code → Remote-SSH dropdown shows hosts
- ✅ Click "prod" or "uat" → Opens remote folder
- ✅ No "Could not resolve hostname" errors

---

**Status:** Ready to fix  
**Last Updated:** February 27, 2026  
**Next Step:** Run the setup script or follow manual steps above
