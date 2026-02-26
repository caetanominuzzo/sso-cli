"""
SSO CLI entry point.
"""

import asyncio
import sys
import argparse
import os
from typing import List

import pyperclip
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .config import backup_config, find_config_path
from .auth import SSOAuthenticator
from .wizard import ModernSelector, run_setup_wizard

console = Console()


def _resolve_prefix(query: str, options: List[str], label: str) -> str:
    if query in options:
        return query
    matches = [o for o in options if o.startswith(query)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous {label} '{query}'. Matches: {', '.join(matches)}")
    raise ValueError(f"{label.capitalize()} '{query}' not found. Available: {', '.join(options)}")


def show_help() -> None:
    auth = SSOAuthenticator()
    console.print()
    console.print(Panel(Text("SSO Authentication Tool", style="bold green"), border_style="green"))
    console.print("\n[bold]Usage:[/bold]")
    console.print("  sso [env] [user]        # get token (non-interactive)")
    console.print("  sso [env] [user] -r     # list roles (JWT + UserInfo)")
    console.print("  sso                     # interactive")
    console.print("  sso --setup             # add environments/users to existing config")
    console.print("  sso --reset             # backup config + start fresh")
    if auth.environments:
        console.print("\n[bold]Environments:[/bold]")
        for k, v in auth.environments.items():
            console.print(f"  [cyan]{k}[/cyan] - {v['name']}")
        console.print("\n[bold]Users:[/bold]")
        for env_key, users in auth.environment_users.items():
            console.print(f"  [bold cyan]{env_key}:[/bold cyan] {', '.join(users)}")
    console.print()


async def _non_interactive(env_arg: str, user_arg: str, *, roles: bool = False) -> None:
    auth = SSOAuthenticator()
    env_key = _resolve_prefix(env_arg, list(auth.environments), "environment")
    user_key = _resolve_prefix(user_arg, list(auth.environment_users.get(env_key, {})), "user")
    if roles:
        await _display_roles(auth, env_key, user_key)
    else:
        token = await auth.get_token(env_key, user_key)
        print(token)


async def _display_roles(auth: SSOAuthenticator, env_key: str, user_key: str) -> None:
    roles_data = await auth.get_user_roles(env_key, user_key)
    console.print()
    console.print("[bold green]Roles[/bold green]")

    for label, key in [("JWT Token", "jwt"), ("UserInfo", "userinfo"), ("Introspection", "introspection")]:
        if key not in roles_data:
            continue
        console.print(f"\n[bold]{label}:[/bold]")
        if roles_data[key]:
            for r in roles_data[key]:
                console.print(f"  [cyan]\u2022[/cyan] {r}")
        else:
            console.print("  [dim]No roles[/dim]")

    console.print()


async def _interactive() -> None:
    console.print()
    console.print(Panel(Text("SSO Authentication Tool", style="bold green"), border_style="green"))

    auth = SSOAuthenticator()
    selector = ModernSelector()

    env_options = [f"{v['name']} ({k})" for k, v in auth.environments.items()]
    env_choice = selector.select_from_list("Select Environment", env_options)
    env_key = list(auth.environments)[env_choice]

    env_users = auth.environment_users.get(env_key, {})
    if not env_users:
        console.print(f"[red]No users configured for environment '{env_key}'.[/red]")
        sys.exit(1)

    user_options = list(env_users)
    user_choice = selector.select_from_list("Select User", user_options)
    user_key = user_options[user_choice]

    console.print()
    console.print(f"[yellow]Authenticating as [bold]{user_key}[/bold] on [bold]{env_key}[/bold]...[/yellow]")

    token = await auth.get_token(env_key, user_key)
    user_info = auth.extract_user_from_token(token)
    console.print()
    try:
        pyperclip.copy(token)
        console.print(Panel(Text("Token copied to clipboard!", style="bold green"), border_style="green"))
    except Exception:
        console.print(Panel(
            f"[bold]Token:[/bold]\n{token}\n\n[bold]Authorization:[/bold] Bearer {token}",
            title="Authentication Token",
            border_style="blue",
        ))
    if user_info.get("preferred_username"):
        console.print(f"[cyan]User:[/cyan] [bold]{user_info['preferred_username']}[/bold]")


async def main() -> None:
    parser = argparse.ArgumentParser(description="SSO Authentication Tool", add_help=False)
    parser.add_argument("environment", nargs="?")
    parser.add_argument("user", nargs="?")
    parser.add_argument("-r", "--roles", action="store_true")
    parser.add_argument("--help", action="store_true")
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    if args.help:
        show_help()
        return

    if args.reset or args.setup:
        if args.reset:
            path = find_config_path()
            if os.path.exists(path):
                backup = backup_config(path)
                console.print(f"[dim]Backed up existing config to: {backup}[/dim]")
            run_setup_wizard(append=False)
        else:  # --setup: append to existing config
            run_setup_wizard(append=True)
        return

    # Auto-setup when no config exists
    if not os.path.exists(find_config_path()):
        console.print(Panel(
            "No config found. Starting setup wizard.",
            border_style="yellow",
        ))
        run_setup_wizard()
        return

    if args.environment and args.user:
        try:
            await _non_interactive(args.environment, args.user, roles=args.roles)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if not args.environment and not args.user:
        try:
            await _interactive()
        except Exception as e:
            console.print(Panel(f"[red]Authentication failed:[/red]\n{e}", border_style="red"))
            sys.exit(1)
        return

    print("Error: provide both environment and user, or neither.", file=sys.stderr)
    sys.exit(1)


def cli() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
        sys.exit(0)
