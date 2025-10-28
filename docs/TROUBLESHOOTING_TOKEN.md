# Troubleshooting: "GitHub token not found" Error

If you're seeing this error even after setting your token, follow this guide step by step.

## The Error

```
Error: GitHub token not found. Set GITHUB_TOKEN environment variable or use --token flag.
```

## Quick Diagnosis

Run this command to check if your token is set:

```bash
echo $GITHUB_TOKEN
```

**If you see output** (your token): The token is set, but ActionsGuard isn't reading it → Go to [Solution 1](#solution-1-restart-your-terminal)

**If you see nothing**: The token isn't set → Go to [Solution 2](#solution-2-set-token-correctly)

---

## Solution 1: Restart Your Terminal

If you just set the token in the current session, it should work. But if you're in a **virtual environment**, you might need to:

```bash
# Deactivate virtual environment
deactivate

# Reactivate it
source venv/bin/activate

# Set token again
export GITHUB_TOKEN="your_token_here"

# Verify
echo $GITHUB_TOKEN

# Try running ActionsGuard
actionsguard scan --repo owner/repo
```

---

## Solution 2: Set Token Correctly

### For macOS/Linux

**Option A: Current terminal session only**

```bash
export GITHUB_TOKEN="your_token_here"
```

**Option B: Make it permanent (Recommended)**

```bash
# For Zsh (default on macOS)
echo 'export GITHUB_TOKEN="your_token_here"' >> ~/.zshrc
source ~/.zshrc

# For Bash (Linux/older macOS)
echo 'export GITHUB_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

**Verify it worked:**

```bash
echo $GITHUB_TOKEN
# Should show your token
```

### For Windows

**PowerShell:**

```powershell
# Current session
$env:GITHUB_TOKEN = "your_token_here"

# Permanent (requires admin)
[System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN', 'your_token_here', 'User')
```

**Command Prompt:**

```cmd
set GITHUB_TOKEN=your_token_here
```

---

## Solution 3: Use --token Flag Instead

If environment variables aren't working, use the `--token` flag directly:

```bash
actionsguard scan --repo owner/repo --token "your_token_here"
```

---

## Common Mistakes

### 1. Wrong Quotes

❌ **Wrong:**
```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx  # No quotes
export GITHUB_TOKEN='ghp_xxxxxxxxxxxx  # Missing closing quote
```

✅ **Correct:**
```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"  # Double quotes
export GITHUB_TOKEN='ghp_xxxxxxxxxxxx'  # Single quotes
```

### 2. Wrong Shell Config File

If you're using **Zsh** (default on modern macOS), but edited **~/.bashrc**, it won't work!

**Check your shell:**
```bash
echo $SHELL
```

**Use the correct file:**
- If output is `/bin/zsh` → Edit `~/.zshrc`
- If output is `/bin/bash` → Edit `~/.bashrc`

### 3. Token Has Spaces

Make sure there are no spaces around the `=` sign:

❌ **Wrong:**
```bash
export GITHUB_TOKEN = "ghp_xxxx"  # Spaces around =
```

✅ **Correct:**
```bash
export GITHUB_TOKEN="ghp_xxxx"  # No spaces
```

### 4. Using sudo

Don't use `sudo` with actionsguard - it runs in a different environment:

❌ **Wrong:**
```bash
sudo actionsguard scan --repo owner/repo  # Won't see your GITHUB_TOKEN
```

✅ **Correct:**
```bash
actionsguard scan --repo owner/repo  # No sudo needed
```

### 5. Virtual Environment Issues

If you set the token BEFORE activating your virtual environment, it won't be available:

**Correct Order:**
```bash
# 1. Activate venv first
source venv/bin/activate

# 2. THEN set token
export GITHUB_TOKEN="ghp_xxxx"

# 3. Run actionsguard
actionsguard scan --repo owner/repo
```

---

## Debug Commands

Run these commands to diagnose the issue:

```bash
# 1. Check if token is set
echo $GITHUB_TOKEN

# 2. Check if it's a valid format
echo $GITHUB_TOKEN | wc -c  # Should be 40+ characters

# 3. Check your current shell
echo $SHELL

# 4. Check if you're in a virtual environment
which python3

# 5. Test token with GitHub API
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# Should return your GitHub user info in JSON format
```

---

## Advanced: Check Token Permissions

Your token might be set but lack the necessary permissions:

```bash
# Check token scopes (Classic token)
curl -I -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user \
  | grep -i x-oauth-scopes

# Test repository access
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/owner/repo

# Test organization access
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/orgs/your-org
```

---

## Still Not Working?

### Option 1: Create a .env file

```bash
# In your project directory
echo 'GITHUB_TOKEN=your_token_here' > .env

# Load it before running
export $(cat .env | xargs)
actionsguard scan --repo owner/repo
```

### Option 2: Use inline token

```bash
GITHUB_TOKEN="your_token_here" actionsguard scan --repo owner/repo
```

### Option 3: Update installation

You might have an older version. Try:

```bash
cd actions-guard
git pull origin main
pip3 install . --force-reinstall
```

---

## Verify Everything Works

Once you think you've fixed it, run this test:

```bash
# Test 1: Token is set
echo "Token set: $([ -z "$GITHUB_TOKEN" ] && echo NO || echo YES)"

# Test 2: Token length (should be 40+)
echo "Token length: $(echo -n "$GITHUB_TOKEN" | wc -c)"

# Test 3: ActionsGuard can see it
actionsguard scan --repo kubernetes/kubernetes --format json

# If this works, you're all set! 🎉
```

---

## Get Help

If none of these solutions work:

1. Run the debug commands above
2. Copy the output
3. Create an issue: https://github.com/cybrking/actions-guard/issues
4. Include:
   - Your OS (macOS/Linux/Windows)
   - Your shell (`echo $SHELL`)
   - Output of `echo $GITHUB_TOKEN | wc -c`
   - Any error messages

---

## Prevention: Make Token Permanent

To avoid this issue in the future, add token to your shell config:

```bash
# For macOS (Zsh)
echo 'export GITHUB_TOKEN="your_token_here"' >> ~/.zshrc

# For Linux (Bash)
echo 'export GITHUB_TOKEN="your_token_here"' >> ~/.bashrc

# Reload
source ~/.zshrc  # or source ~/.bashrc

# Test
echo $GITHUB_TOKEN
```

**⚠️ Security Note:** Make sure `~/.zshrc` or `~/.bashrc` has proper permissions:

```bash
chmod 600 ~/.zshrc  # Only you can read/write
```

---

**Quick Reference:**

```bash
# Set token (current session)
export GITHUB_TOKEN="your_token_here"

# Verify
echo $GITHUB_TOKEN

# Use it
actionsguard scan --repo owner/repo

# Or use flag instead
actionsguard scan --repo owner/repo --token "your_token_here"
```
