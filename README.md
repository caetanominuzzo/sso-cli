# sso-cli

> **sso-cli has evolved into [dev-vault](https://pypi.org/project/dev-vault/)** -- a full developer secret vault with OIDC token support, secret injection, and AI-agent integration. sso-cli will continue to work, but all new features go into dev-vault. Migrate with: `pip install dev-vault && dv migrate sso-cli`

[![PyPI version](https://badge.fury.io/py/sso-cli.svg)](https://pypi.org/project/sso-cli/)
[![Downloads](https://static.pepy.tech/badge/sso-cli)](https://pepy.tech/project/sso-cli)

**Enterprise SSO tokens in one command.**

For developers, scripts, and AI agents.

```bash
pip install sso-cli
```

```bash
$ sso prod user@example.com
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

No `.env` files. No multi-step flows. Fresh tokens, fetched on demand from the system keyring.

---

## Three ways to use it

### For developers

Test any protected endpoint without leaving the terminal:

```bash
curl https://api.dev.example.com/orders \
  -H "Authorization: Bearer $(sso dev test@dev.com)"
```

### For scripts and pipelines

Drop it into any automation — the token is always fresh:

```bash
BEARER=$(sso prod service-account)
curl -H "Authorization: Bearer $BEARER" https://api.example.com/data
```

### For AI agents

Give Cursor, Claude Code, Copilot, or any agent access to SSO-protected APIs:

```
Test this endpoint using the bearer token from $(sso dev test@dev.com)
```

Works with any agent that can run shell commands.

---

## Why sso-cli?

Getting a token from enterprise SSO is always a multi-step process — browser flows, OAuth parameters, token endpoints. That friction adds up fast when you're writing scripts, testing APIs, or building with AI agents.

sso-cli turns it into a one-liner. It handles OIDC/OAuth2, token refresh, and credential storage so you don't have to.

---

## Install

```bash
pip install sso-cli
```

If the `sso` command is not found after installation:

```bash
sso-setup-path
source ~/.zshrc   # or ~/.bashrc, or restart your terminal on Windows
```

## Usage

```bash
# Get a token
sso prod user@example.com

# Prefix matching — type less
sso p u          # → sso prod user@example.com (if unique)

# List roles (JWT + UserInfo/Introspection)
sso prod user@example.com -r    # users: JWT + UserInfo
sso prod api-client -r           # clients: JWT + Introspection

# List/Remove environments and users
sso -l env
sso -l user
sso -d env prod
sso -d user prod user@example.com

# Interactive mode
sso
```

## Config

Configuration is stored in `~/sso_config.yaml` (auto-created on first use). All setup is done through the interactive flow — no manual YAML editing required.

Example structure (for reference):

```yaml
environments:
  prod:
    sso_url: https://sso.example.com
    realm: Production
    client_id: my-client-id  # optional, prompted if needed

users:
  prod:
    user@example.com:
      auth_type: password
      email: user@example.com
    api-client:
      auth_type: client_credentials
      client_id: api-client
```

Secrets (passwords and client secrets) are stored securely in the system keyring — never written to disk.

---

PyPI package: https://pypi.org/project/sso-cli/

## See Also

- [dev-vault](https://pypi.org/project/dev-vault/) — Developer secret vault + OIDC token provider (the evolution of sso-cli).
- [Agent State](https://agentstate.tech/) — an open toolbox that gives AI agents persistent memory, tools, and organizational context across sessions via a shared Git repository.
- [terminal-to-here](https://github.com/caetanominuzzo/terminal-to-here) — VS Code extension for quickly navigating terminals to the current file's directory.
