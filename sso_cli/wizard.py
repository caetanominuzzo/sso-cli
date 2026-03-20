"""
Drill-down config manager.
Secrets are captured with getpass (masked) and stored in the OS keyring.
They are NEVER written to disk.
"""

import re
import sys
import getpass
from typing import Any, Dict

import inquirer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .config import find_config_path, load_config, save_config
from .secrets import delete_secret, get_secret, store_secret

console = Console()


_BACK = "[<] Back"
_SAVE_QUIT = "[q] Save & quit"


class ModernSelector:
    def select_from_list(self, title: str, options: list) -> int:
        questions = [
            inquirer.List("choice", message=title, choices=options, carousel=True)
        ]
        try:
            answers = inquirer.prompt(questions)
            if answers is None:
                sys.exit(0)
            return options.index(answers["choice"])
        except (KeyboardInterrupt, EOFError):
            sys.exit(0)


_selector = ModernSelector()


def _pick(title: str, options: list) -> str:
    return options[_selector.select_from_list(title, options)]


def _prompt_env(config: Dict) -> None:
    """Prompt for a new environment and add it (with one user) to config."""
    env_key = Prompt.ask("  Environment key (e.g. dev, prod)").strip()
    if not env_key:
        return
    raw = Prompt.ask("  SSO base URL (e.g. sso.example.com)").strip().rstrip("/")
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    console.print("  [dim](case-sensitive in Keycloak)[/dim]")
    realm = Prompt.ask("  Realm name", default="master").strip()
    sso_url = f"{raw}/realms/{realm}"
    console.print(f"  [dim]-> {sso_url}[/dim]")
    config[env_key] = {"name": env_key, "sso_url": sso_url, "users": {}}
    _prompt_user(config, env_key)


def _prompt_user(config: Dict, env_key: str) -> None:
    """Prompt for a new user and store its secret in the keyring."""
    auth = _pick("  Auth type", ["user", "client"])
    if auth == "user":
        email = Prompt.ask("  Email").strip()
        secret = getpass.getpass("  Password: ")
        user_key = email
        config[env_key]["users"][user_key] = {"auth_type": "user", "email": email}
    else:
        client_id = Prompt.ask("  Client ID").strip()
        secret = getpass.getpass("  Client Secret: ")
        user_key = client_id
        config[env_key]["users"][user_key] = {"auth_type": "client", "client_id": client_id}
    store_secret(env_key, user_key, secret)
    console.print(f"  [green]Keyring updated: {env_key}/{user_key}[/green]")


def _user_menu(config: Dict, env_key: str, user_key: str) -> str | None:
    """Manage a single user. Returns the (possibly new) user_key, or None if deleted."""
    current_key = user_key
    while True:
        ud = config[env_key]["users"][current_key]
        auth_type = ud["auth_type"]
        id_label = "Email" if auth_type == "user" else "Client ID"
        id_value = ud.get("email") or ud.get("client_id") or current_key

        console.print()
        console.print(Panel(
            f"[bold]{current_key}[/bold]\n"
            f"  Type: [cyan]{auth_type}[/cyan]\n"
            f"  {id_label}: [cyan]{id_value}[/cyan]",
            title=f"{env_key} / {current_key}",
            border_style="dim",
        ))

        options = [
            f"[e] Edit {id_label.lower()}",
            "[s] Edit secret",
            "[-] Delete user",
            _BACK,
        ]
        choice = _pick(f"User: {current_key}", options)
        if choice == "[s] Edit secret":
            secret = getpass.getpass(f"  New secret for {current_key}: ")
            store_secret(env_key, current_key, secret)
            console.print(f"  [green]Updated: {env_key}/{current_key}[/green]")
        elif choice.startswith("[e]"):
            new_id = Prompt.ask(f"  New {id_label}", default=id_value).strip()
            if new_id and new_id != id_value:
                old_key = current_key
                new_key = new_id
                ud_copy = dict(ud)
                if auth_type == "user":
                    ud_copy["email"] = new_id
                else:
                    ud_copy["client_id"] = new_id
                # migrate secret to new key
                old_secret = get_secret(env_key, old_key)
                del config[env_key]["users"][old_key]
                config[env_key]["users"][new_key] = ud_copy
                if old_secret:
                    store_secret(env_key, new_key, old_secret)
                delete_secret(env_key, old_key)
                current_key = new_key
                console.print(f"  [green]Renamed: {old_key} -> {new_key}[/green]")
        elif choice == "[-] Delete user":
            if not Confirm.ask(
                f"  Delete user [bold]{current_key}[/bold] from [bold]{env_key}[/bold]?",
                default=False,
            ):
                continue
            del config[env_key]["users"][current_key]
            delete_secret(env_key, current_key)
            console.print(f"  [yellow]Deleted user '{current_key}'[/yellow]")
            return None
        else:
            return current_key


def _parse_sso_url(sso_url: str):
    """Extract (base_url, realm) from a full sso_url like https://host/realms/Foo."""
    m = re.match(r"^(https?://[^/]+)(?:/realms/(.+))?$", sso_url.rstrip("/"))
    if m:
        return m.group(1), m.group(2) or "master"
    return sso_url, "master"


def _env_menu(config: Dict, env_key: str) -> str | None:
    """Manage a single environment. Returns the (possibly new) env_key, or None if deleted."""
    current_key = env_key
    while True:
        env = config[current_key]
        users = env["users"]
        base_url, realm = _parse_sso_url(env["sso_url"])

        console.print()
        user_lines = ""
        for uk in users:
            u = users[uk]
            uid = u.get("email") or u.get("client_id") or uk
            user_lines += f"  [cyan]{uk}[/cyan]  ({u['auth_type']}: {uid})\n"
        if not user_lines:
            user_lines = "  [dim]No users configured[/dim]\n"

        console.print(Panel(
            f"[bold]{current_key}[/bold]\n"
            f"  URL:   [cyan]{base_url}[/cyan]\n"
            f"  Realm: [cyan]{realm}[/cyan]\n"
            f"  Users:\n{user_lines.rstrip()}",
            title=f"Environment: {current_key}",
            border_style="dim",
        ))

        labels = [f"{uk}  [{users[uk]['auth_type']}]" for uk in users]
        options = (
            labels
            + [
                "[+] Add user",
                "[e] Edit environment",
                f"[-] Delete environment",
                _BACK,
            ]
        )
        choice = _pick(f"Environment: {current_key}", options)
        if choice == _BACK:
            return current_key
        elif choice == "[+] Add user":
            _prompt_user(config, current_key)
        elif choice == "[e] Edit environment":
            current_key = _edit_env(config, current_key, base_url, realm)
        elif choice == "[-] Delete environment":
            if not Confirm.ask(
                f"  Delete environment [bold]{current_key}[/bold] "
                f"and all its {len(users)} user(s)?",
                default=False,
            ):
                continue
            for uk in list(users):
                delete_secret(current_key, uk)
            del config[current_key]
            console.print(f"  [yellow]Deleted environment '{current_key}'[/yellow]")
            return None
        else:
            user_key = list(users)[labels.index(choice)]
            _user_menu(config, current_key, user_key)


def _edit_env(config: Dict, env_key: str, base_url: str, realm: str) -> str:
    """Edit environment properties. Returns the (possibly new) env_key."""
    options = [
        "[k] Rename environment key",
        "[u] Edit SSO base URL",
        "[r] Edit realm",
        _BACK,
    ]
    choice = _pick(f"Edit: {env_key}", options)
    if choice == _BACK:
        return env_key
    elif choice == "[k] Rename environment key":
        new_key = Prompt.ask("  New environment key", default=env_key).strip()
        if new_key and new_key != env_key:
            env_data = config.pop(env_key)
            config[new_key] = env_data
            if env_data.get("name") == env_key:
                env_data["name"] = new_key
            # migrate secrets
            for uk in list(env_data["users"]):
                old_secret = get_secret(env_key, uk)
                if old_secret:
                    store_secret(new_key, uk, old_secret)
                delete_secret(env_key, uk)
            console.print(f"  [green]Renamed: {env_key} -> {new_key}[/green]")
            return new_key
    elif choice == "[u] Edit SSO base URL":
        new_url = Prompt.ask("  SSO base URL", default=base_url).strip().rstrip("/")
        if new_url:
            if not new_url.startswith(("http://", "https://")):
                new_url = "https://" + new_url
            config[env_key]["sso_url"] = f"{new_url}/realms/{realm}"
            console.print(f"  [green]Updated URL: {config[env_key]['sso_url']}[/green]")
    elif choice == "[r] Edit realm":
        console.print("  [dim](case-sensitive in Keycloak)[/dim]")
        new_realm = Prompt.ask("  Realm name", default=realm).strip()
        if new_realm:
            config[env_key]["sso_url"] = f"{base_url}/realms/{new_realm}"
            console.print(f"  [green]Updated realm: {config[env_key]['sso_url']}[/green]")
    return env_key


def run_setup_wizard(append: bool = False) -> str:
    """Drill-down menu to manage sso_config.yaml.

    append=True  -- load existing config and edit/extend it (--setup)
    append=False -- start fresh (auto-setup or --reset)
    """
    config: Dict[str, Any] = {}
    if append:
        try:
            envs, env_users = load_config()
            for ek, ev in envs.items():
                config[ek] = {"name": ev["name"], "sso_url": ev["sso_url"], "users": {}}
                for uk, ud in env_users.get(ek, {}).items():
                    config[ek]["users"][uk] = {k: v for k, v in ud.items() if v is not None}
        except FileNotFoundError:
            pass

    out_path = find_config_path()
    console.print()
    console.print(Panel(
        "[bold cyan]SSO Config Manager[/bold cyan]\n\n"
        "Arrow keys to navigate, Enter to select.\n"
        "[+] Add   [-] Delete   [<] Back   [q] Save & quit\n"
        "Secrets are [bold red]never[/bold red] written to disk.",
        border_style="cyan",
        title="Setup",
    ))

    if not config:
        console.print("\n[dim]No environments yet -- adding the first one.[/dim]")
        _prompt_env(config)

    while True:
        env_lines = []
        for ek in config:
            base_url, realm = _parse_sso_url(config[ek]["sso_url"])
            n_users = len(config[ek]["users"])
            env_lines.append(f"{ek}  ({base_url}, {n_users} user(s))")
        options = env_lines + ["[+] Add environment", _SAVE_QUIT]
        choice = _pick("Environments", options)
        if choice == _SAVE_QUIT:
            break
        elif choice == "[+] Add environment":
            _prompt_env(config)
        else:
            env_key = list(config)[env_lines.index(choice)]
            _env_menu(config, env_key)  # returns new key or None; config mutated in-place

    save_config(config, out_path)
    console.print()
    console.print(Panel(f"[green]Config saved to [bold]{out_path}[/bold][/green]", border_style="green"))
    return out_path
