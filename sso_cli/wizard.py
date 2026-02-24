"""
Drill-down config manager.
Secrets are captured with getpass (masked) and stored in the OS keyring.
They are NEVER written to disk.
"""

import sys
import getpass
from typing import Any, Dict

import inquirer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from .config import find_config_path, load_config, save_config
from .secrets import delete_secret, store_secret

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


def _user_menu(config: Dict, env_key: str, user_key: str) -> None:
    while True:
        choice = _pick(f"{env_key} / {user_key}", ["[e] Edit secret", "[-] Delete user", _BACK])
        if choice == "[e] Edit secret":
            secret = getpass.getpass(f"  New secret for {user_key}: ")
            store_secret(env_key, user_key, secret)
            console.print(f"  [green]Updated: {env_key}/{user_key}[/green]")
        elif choice == "[-] Delete user":
            del config[env_key]["users"][user_key]
            delete_secret(env_key, user_key)
            console.print(f"  [yellow]Deleted user '{user_key}'[/yellow]")
            return
        else:
            return


def _env_menu(config: Dict, env_key: str) -> None:
    while True:
        users = config[env_key]["users"]
        labels = [f"{uk}  [{users[uk]['auth_type']}]" for uk in users]
        options = labels + [f"[+] Add user", f"[-] Delete environment '{env_key}'", _BACK]
        choice = _pick(f"Environment: {env_key}", options)
        if choice == _BACK:
            return
        elif choice == "[+] Add user":
            _prompt_user(config, env_key)
        elif choice == f"[-] Delete environment '{env_key}'":
            for uk in list(users):
                delete_secret(env_key, uk)
            del config[env_key]
            console.print(f"  [yellow]Deleted environment '{env_key}'[/yellow]")
            return
        else:
            user_key = list(users)[labels.index(choice)]
            _user_menu(config, env_key, user_key)


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
        env_labels = [f"{ek}  ({len(config[ek]['users'])} user(s))" for ek in config]
        options = env_labels + ["[+] Add environment", _SAVE_QUIT]
        choice = _pick("Environments", options)
        if choice == _SAVE_QUIT:
            break
        elif choice == "[+] Add environment":
            _prompt_env(config)
        else:
            env_key = list(config)[env_labels.index(choice)]
            _env_menu(config, env_key)

    save_config(config, out_path)
    console.print()
    console.print(Panel(f"[green]Config saved to [bold]{out_path}[/bold][/green]", border_style="green"))
    return out_path
