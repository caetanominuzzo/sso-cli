# sso-cli

[![PyPI version](https://badge.fury.io/py/sso-cli.svg)](https://pypi.org/project/sso-cli/)
[![Downloads](https://static.pepy.tech/badge/sso-cli)](https://pepy.tech/project/sso-cli)

Get OAuth / OIDC access tokens from the terminal.

When working with APIs protected by Keycloak or other SSO providers,
developers often need to manually copy tokens from the browser.
sso-cli lets you fetch those tokens directly from the command line.

```bash
pip install sso-cli
```

```bash
$ sso prod user@example.com
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

```bash
curl https://api.dev.example.com/orders \
  -H "Authorization: Bearer $(sso dev test@dev.com)"
```

No credentials in your prompts, no `.env` files, no copy-paste. The token is fetched on-demand from the system keyring.

PyPI package: https://pypi.org/project/sso-cli/

## Use Cases

- Test a protected API endpoint without copy-pasting tokens
- Authenticate CLI scripts against Keycloak or any OIDC provider
- Give AI agents (Cursor, Claude Code, Copilot) access to SSO-protected URLs
- Fetch a bearer token for curl or httpie one-liners
- Automate token retrieval in CI/CD pipelines
- Access multiple environments (dev, staging, prod) with a single command
- List JWT roles and claims for debugging permission issues

## Why This Exists

Most SSO providers require logging in through a browser just to retrieve an access token. For developers writing scripts, testing APIs, or working with AI agents, this is inconvenient and breaks the flow.

sso-cli solves that by providing a CLI that fetches tokens from any Keycloak/OIDC realm, stores credentials securely in the system keyring, and works across multiple environments.

## Install

```bash
pip install sso-cli
```

After installation, configure PATH automatically:

```bash
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

### AI Agent Integration

Ask your AI agent to call any SSO-protected endpoint inline:

```
Test this endpoint using the bearer token from $(sso dev test@dev.com)
```

Works with Cursor, Windsurf, Copilot, Claude Code, and any agent that can run shell commands.

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

- [Agent State](https://agentstate.tech/) — an open toolbox that gives AI agents persistent memory, tools, and organizational context across sessions via a shared Git repository.
