# GitHub Token Guide for ActionsGuard

This guide explains how to create and configure GitHub tokens for ActionsGuard.

## Why Do I Need a Token?

ActionsGuard uses the GitHub API to:
- Fetch repository information
- Read workflow files from `.github/workflows/`
- List repositories in organizations
- Access repository metadata

## Token Types

### Fine-grained Personal Access Tokens (Recommended) ⭐

**Advantages:**
- ✅ More secure - limited to specific repositories
- ✅ Granular permissions - only what's needed
- ✅ Automatic expiration (forces regular rotation)
- ✅ Audit log for token usage
- ✅ Can be restricted by IP address
- ✅ GitHub's recommended approach

**Disadvantages:**
- Slightly more complex to set up
- Need to update when adding new repositories

### Classic Personal Access Tokens

**Advantages:**
- ✅ Simple to set up
- ✅ Works across all accessible repositories

**Disadvantages:**
- ❌ Broader access than needed
- ❌ No automatic expiration
- ❌ Less secure

## Creating a Fine-grained Token

### Step 1: Navigate to Token Creation

Go to: https://github.com/settings/personal-access-tokens/new

### Step 2: Basic Information

- **Token name**: `ActionsGuard Scanner`
- **Expiration**: 90 days (recommended) or custom
- **Description**: `Security scanning for GitHub Actions workflows`

### Step 3: Repository Access

Choose based on your use case:

**For Single Repository Scanning:**
- Select: "Only select repositories"
- Click "Select repositories" and choose the repos you want to scan

**For Organization Scanning:**
- Select: "All repositories"
- This gives access to all repos in organizations you're a member of

**For Public Repository Scanning Only:**
- Select: "Public Repositories (read-only)"
- No additional permissions needed

### Step 4: Repository Permissions

Set these permissions:

| Permission | Access Level | Purpose |
|------------|-------------|---------|
| **Actions** | Read | Access workflow files in `.github/workflows/` |
| **Contents** | Read | Read repository files and structure |
| **Metadata** | Read | Access basic repository information (automatic) |

### Step 5: Organization Permissions (Optional)

Only needed for organization scanning:

| Permission | Access Level | Purpose |
|------------|-------------|---------|
| **Members** | Read | List repositories in the organization |

### Step 6: Generate and Save

1. Click "Generate token"
2. **Copy the token immediately** - it starts with `github_pat_`
3. Store it securely (password manager recommended)

## Creating a Classic Token

### Step 1: Navigate to Token Creation

Go to: https://github.com/settings/tokens/new

### Step 2: Configure Token

- **Note**: `ActionsGuard Scanner`
- **Expiration**: 90 days (recommended)

### Step 3: Select Scopes

**For Private Repository Scanning:**
- ✅ `repo` - Full control of private repositories
  - Includes: `repo:status`, `repo_deployment`, `public_repo`, `repo:invite`, `security_events`

**For Public Repository Scanning Only:**
- ✅ `public_repo` - Access public repositories only

**For Organization Scanning:**
- ✅ `read:org` - Read org and team membership, read org projects

### Step 4: Generate and Save

1. Click "Generate token"
2. **Copy the token immediately** - it starts with `ghp_`
3. Store it securely

## Setting Up the Token

### macOS/Linux

```bash
# Set for current session
export GITHUB_TOKEN="your_token_here"

# Make it permanent (choose your shell)
# For Zsh (default on macOS):
echo 'export GITHUB_TOKEN="your_token_here"' >> ~/.zshrc
source ~/.zshrc

# For Bash:
echo 'export GITHUB_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

### Windows

**PowerShell:**
```powershell
# Set for current session
$env:GITHUB_TOKEN = "your_token_here"

# Make it permanent
[System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN', 'your_token_here', 'User')
```

**Command Prompt:**
```cmd
set GITHUB_TOKEN=your_token_here
```

### CI/CD Systems

**GitHub Actions:**
```yaml
- name: Run ActionsGuard
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: actionsguard scan --org my-org
```

**GitLab CI:**
```yaml
variables:
  GITHUB_TOKEN: $GITHUB_TOKEN  # Set in CI/CD settings
```

## Verifying Your Token

### Check if Token is Set

```bash
# Should display your token (be careful in shared terminals!)
echo $GITHUB_TOKEN

# Check if it's set (without displaying)
[ -z "$GITHUB_TOKEN" ] && echo "Token not set" || echo "Token is set"
```

### Test Token Validity

```bash
# Should return your GitHub username
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user | jq '.login'

# Check rate limits
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/rate_limit | jq '.rate'
```

### Test Token Permissions

```bash
# List accessible repositories
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user/repos | jq '.[].full_name'

# Test org access
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user/orgs | jq '.[].login'
```

## Security Best Practices

1. **Use Fine-grained Tokens**: More secure and auditable
2. **Set Expiration**: Force regular token rotation
3. **Minimum Permissions**: Only grant what's needed
4. **Secure Storage**: Use environment variables or secret managers
5. **Never Commit Tokens**: Add to `.gitignore`
6. **Rotate Regularly**: Create new tokens every 90 days
7. **Revoke Unused Tokens**: Clean up at https://github.com/settings/tokens
8. **Monitor Usage**: Check audit logs for suspicious activity

## Troubleshooting

### "Bad credentials" Error

```bash
Error: 401 Unauthorized - Bad credentials
```

**Solutions:**
- Token may be expired or revoked
- Token may not be set correctly
- Verify with: `echo $GITHUB_TOKEN`
- Create a new token

### "Not Found" for Organization

```bash
Error: 404 Not Found
```

**Solutions:**
- Organization name may be incorrect
- You may not be a member of the organization
- For fine-grained tokens: Check "Members: Read" permission
- For classic tokens: Verify `read:org` scope

### Rate Limit Issues

```bash
Error: API rate limit exceeded
```

**Solutions:**
- Authenticated requests: 5,000/hour
- Unauthenticated: 60/hour
- Check reset time: `curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit`
- Wait for reset or use different token

### Permission Denied on Private Repos

```bash
Error: Repository not found or access denied
```

**Solutions:**
- For fine-grained: Add repository to "Repository access"
- For classic: Ensure `repo` scope (not just `public_repo`)
- Verify you have access to the repository

## Token Management

### Rotating Tokens

When tokens expire or need rotation:

1. Create new token with same permissions
2. Test new token: `GITHUB_TOKEN=new_token actionsguard --version`
3. Update environment variable
4. Revoke old token
5. Update CI/CD secrets

### Revoking Tokens

**Fine-grained tokens:**
https://github.com/settings/personal-access-tokens

**Classic tokens:**
https://github.com/settings/tokens

Click "Delete" next to the token you want to revoke.

## Questions?

See the main [README.md](README.md) or [QUICKSTART.md](QUICKSTART.md) for more information.
