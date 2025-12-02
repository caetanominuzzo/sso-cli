# sso-cli

SSO auth CLI - Keycloak/OIDC tokens & roles.

CLI tool for authenticating with Keycloak/OIDC providers, fetching access tokens, and listing user roles. Supports multiple environments, password and client credentials authentication, with secrets stored in the system keyring. With prefix matching for quick access and organized role display from both JWT tokens and userinfo endpoints.

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

# List roles (JWT + UserInfo)
sso prod user@example.com -r

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
