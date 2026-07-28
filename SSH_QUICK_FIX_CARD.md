# 🚀 SSH FIX QUICK CARD - Print This

**Problem:** VS Code Remote SSH: `Could not resolve hostname miguel-crm`  
**Solution:** Proper SSH config for Production & UAT  
**Time to Fix:** 5-10 minutes

---

## ⚡ QUICKEST FIX (Works immediately)

```bash
# Just use the IP directly in VS Code:
# 1. Click Remote-SSH icon (bottom left)
# 2. Click "Connect to Host..."
# 3. Type: root@172.232.118.208
# 4. Press Enter
# 5. Done! Connected to production
```

---

## ✅ PROPER FIX (Recommended)

### 1. Create SSH Config
```bash
cat > ~/.ssh/config << 'EOF'
# UAT Server
Host uat
    HostName 172.232.118.208
    User root
    IdentityFile ~/.ssh/uat
    Port 22
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null

# Production Server
Host prod
    HostName 172.105.48.142
    User root
    IdentityFile ~/.ssh/prod
    Port 22
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
EOF

chmod 644 ~/.ssh/config
```

### 2. Test It
```bash
ssh prod          # Should connect
ssh uat           # Should connect
```

### 3. Use in VS Code
- Click Remote-SSH icon
- Select "prod" or "uat" from dropdown
- Done!

---

## 🔑 IF YOU DON'T HAVE SSH KEY

```bash
# Generate one
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""

# Copy to server
ssh-copy-id -i ~/.ssh/id_rsa.pub root@172.232.118.208
```

---

## 🆘 COMMON ERRORS

| Error | Fix |
|-------|-----|
| "Could not resolve hostname" | Add proper `Host` entry to `~/.ssh/config` |
| "Permission denied" | Run: `ssh-copy-id -i ~/.ssh/id_rsa.pub root@<IP>` |
| "Connection refused" | Server SSH not running or port blocked |
| "Connection timeout" | Check IP is correct: `ping <IP>` |

---

## 📋 WHAT YOU NEED

```
1. ~/.ssh/id_rsa          ← Your private key
2. ~/.ssh/config          ← Host definitions (SEE BELOW)
3. <UAT_IP_ADDRESS>       ← Get from team/admin
```

---

## 🎯 SSH CONFIG TEMPLATE (ACTUAL CONFIG)

```ssh
# UAT Server
Host uat
    HostName 172.232.118.208
    User root
    IdentityFile ~/.ssh/uat
    Port 22
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null

# Production Server
Host prod
    HostName 172.105.48.142
    User root
    IdentityFile ~/.ssh/prod
    Port 22
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
```

**Save as:** `~/.ssh/config`  
**Permissions:** `chmod 644 ~/.ssh/config`

---

## ✨ VERIFY IT WORKS

```bash
# Terminal test
ssh prod                    # Should connect

# VS Code test
1. Cmd+Shift+P
2. Type: Remote-SSH: Connect to Host
3. Select "prod"
4. Should open without error ✓
```

---

## 📁 FILES CREATED FOR YOU

1. **SSH_CONFIG_FIX_UAT.md** - Complete setup guide
2. **SSH_TROUBLESHOOTING_GUIDE.md** - Problem solutions
3. **setup_ssh_config.sh** - Automated script
4. **SSH_ISSUES_FIXED_UAT.md** - Full reference

---

## 🚀 RUN AUTOMATED SETUP

```bash
chmod +x /opt/pureleven/setup_ssh_config.sh
./setup_ssh_config.sh

# Then update UAT IP in generated config
```

---

## 📞 NEED HELP?

- **Terminal SSH issue?** → SSH_TROUBLESHOOTING_GUIDE.md
- **VS Code issue?** → SSH_CONFIG_FIX_UAT.md
- **Need to do setup?** → Read SSH_ISSUES_FIXED_UAT.md

---

**Status:** ✅ Ready to fix  
**Next:** Pick a fix option and follow steps  
**Time needed:** 5-10 minutes  
**Difficulty:** Easy
