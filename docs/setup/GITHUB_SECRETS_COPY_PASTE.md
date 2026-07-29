# COPY THESE SECRETS TO GITHUB

> 📍 Destination: https://github.com/purelevenexim-ai/crm/settings/secrets/actions

---

## Secret 1: UAT_SSH_HOST

**Name:** `UAT_SSH_HOST`

**Value:**
```
172.232.118.208
```

---

## Secret 2: UAT_SSH_USER

**Name:** `UAT_SSH_USER`

**Value:**
```
root
```

---

## Secret 3: UAT_SSH_KEY

**Name:** `UAT_SSH_KEY`

**Value:**
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACC09WQjzQZowWojxrMB5zXwyAZuIaVMJIyBPM3nD7TijgAAAJgCvtV0Ar7V
dAAAAAtzc2gtZWQyNTUxOQAAACC09WQjzQZowWojxrMB5zXwyAZuIaVMJIyBPM3nD7Tijg
AAAEA92QuS2rXUbM8OhtQmt5nU2FxAAPot+zISg5WGEYVpv7T1ZCPNBmjBaiPGswHnNfDI
Bm4hpUwkjIE8zecPtOKOAAAAE3VhdC0xNzIuMjMyLjExOC4yMDgBAg==
-----END OPENSSH PRIVATE KEY-----
```

---

## Secret 4: PROD_SSH_HOST

**Name:** `PROD_SSH_HOST`

**Value:**
```
172.105.48.142
```

---

## Secret 5: PROD_SSH_USER

**Name:** `PROD_SSH_USER`

**Value:**
```
root
```

---

## Secret 6: PROD_SSH_KEY

**Name:** `PROD_SSH_KEY`

**Value:**
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACBfHZUhtaOTHJp5sxn3uNKEQrbiHuTlr1+ci/m2Ul3FPQAAAJhje8YwY3vG
MAAAAAtzc2gtZWQyNTUxOQAAACBfHZUhtaOTHJp5sxn3uNKEQrbiHuTlr1+ci/m2Ul3FPQ
AAAECa3jPFghVeBahfjiBmJi4OfWotFD0Udr/2JLbRJGxyS18dlSG1o5McmnmzGfe40oRC
tuIe5OWvX5yL+bZSXcU9AAAAE3Byb2QtMTcyLjEwNS40OC4xNDIBAg==
-----END OPENSSH PRIVATE KEY-----
```

---

## How to Add These

1. Open: https://github.com/purelevenexim-ai/crm/settings/secrets/actions
2. Click: **"New repository secret"** button
3. For each secret above:
   - Copy the **Name** (e.g., `UAT_SSH_HOST`)
   - Paste into the "Name" field
   - Copy the **Value** (the IP address or entire private key)
   - Paste into the "Value" field
   - Click: **"Add secret"**

---

## Verify Setup

After adding all 6 secrets, you should see:

```
✅ PROD_SSH_HOST
✅ PROD_SSH_KEY
✅ PROD_SSH_USER
✅ UAT_SSH_HOST
✅ UAT_SSH_KEY
✅ UAT_SSH_USER
```

---

## Now Triggers are Active

Once GitHub Secrets are set:

- **Push to `uat` branch** → Auto-deploys to `172.232.118.208:/opt/miguel`
- **Push to `main` branch** → Auto-deploys to `172.105.48.142:/opt/pureleven`

View deployment logs at: `github.com/purelevenexim-ai/crm/actions`

