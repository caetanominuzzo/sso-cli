# sso-cli

[![PyPI version](https://badge.fury.io/py/sso-cli.svg)](https://pypi.org/project/sso-cli/)
[![Downloads](https://static.pepy.tech/badge/sso-cli)](https://pepy.tech/project/sso-cli)

CLI tool to fetch Keycloak/OIDC tokens — built for developers and agentic AI workflows.

## Why

The primary use case is **giving agentic LLMs (Cursor, Windsurf, Copilot, etc.) secure access to protected APIs** without exposing credentials.

Ask your AI agent to call any SSO-protected endpoint inline:

```
Test this endpoint using the bearer token from $(sso dev test@dev.com)
```

```
curl https://api.dev.example.com/orders \
  -H "Authorization: Bearer $(sso dev test@dev.com)"
```

The token is fetched on-demand from the system keyring — **no credentials, no `.env` files, no copy-paste** in your prompts or chat history.

Works with any Keycloak/OIDC realm across multiple environments (`dev`, `staging`, `prod`).

## Install

```bash
pip install sso-cli

# After installation, configure PATH automatically:
sso-setup-path

# Then reload your shell configuration:
# For zsh/bash: source ~/.zshrc  or  source ~/.bashrc
# For Windows: restart your terminal
```

**Note:** If the `sso` command is not found after installation, run `sso-setup-path` to automatically add the Python scripts directory to your PATH.

## Usage

```bash
# Get token
sso prod user@example.com

# Prefix matching (auto-complete)
sso p u          # → sso prod user@example.com (if unique)
sso prod u       # → error if ambiguous

# List roles (JWT + UserInfo/Introspection)
sso prod user@example.com -r    # users: JWT + UserInfo
sso prod api-client -r           # clients: JWT + Introspection

# List/Remove
sso -l env
sso -l user
sso -d env prod
sso -d user prod user@example.com

# Interactive
sso
```

## Config

Configuration is stored in `~/sso_config.yaml` (auto-created by the app). All setup is done through the interactive flow - no manual YAML editing required.

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

Secrets (passwords and client secrets) are stored securely in the system keyring. Environments and users are automatically created on first use through an interactive setup flow. The tool supports optional client_id configuration per environment for Keycloak instances that require it.

---

## See Also

- [Agent State](https://agentstate.tech/) — an open standard that gives AI agents persistent memory, tools, and organizational context across sessions via a shared Git repository.
