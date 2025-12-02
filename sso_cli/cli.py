"""CLI interface"""

import sys
import asyncio
import argparse
import logging
from typing import List
try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    # Fallback for Python < 3.8
    from importlib_metadata import version, PackageNotFoundError
import inquirer
from rich.console import Console
from rich.prompt import Prompt
from rich.text import Text

from .auth import SSOAuthenticator
from .utils import copy_to_clipboard

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
console = Console()


class ModernSelector:
    def __init__(self):
        self.console = Console()
    
    def select_from_list(self, title: str, options: List[str]) -> int:
        questions = [inquirer.List('choice', message=title, choices=options, carousel=True)]
        try:
            answers = inquirer.prompt(questions)
            if answers is None:
                self.console.print("\n[yellow]Exiting...[/yellow]")
                sys.exit(0)
            return options.index(answers['choice'])
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n[yellow]Exiting...[/yellow]")
            sys.exit(0)


def get_version():
    """Get the version of the installed package."""
    try:
        return version("sso-cli")
    except PackageNotFoundError:
        return "unknown"


def show_help():
    console.print()
    console.print("[bold green]SSO CLI[/bold green]\n")
    console.print("[bold]Commands:[/bold]")
    cmd1 = Text("  sso ")
    cmd1.append("[env]", style="dim")
    cmd1.append(" ")
    cmd1.append("[user]", style="dim")
    console.print(cmd1)
    cmd2 = Text("  sso ")
    cmd2.append("[env]", style="dim")
    cmd2.append(" ")
    cmd2.append("[user]", style="dim")
    cmd2.append(" -r, --roles")
    console.print(cmd2)
    console.print("  sso                                (interactive)")
    console.print("\n[bold]List:[/bold]")
    console.print("  sso -l, --list env")
    console.print("  sso -l, --list user")
    console.print("\n[bold]Remove:[/bold]")
    cmd3 = Text("  sso -d, --remove env ")
    cmd3.append("[env]", style="dim")
    console.print(cmd3)
    cmd4 = Text("  sso -d, --remove user ")
    cmd4.append("[env]", style="dim")
    cmd4.append(" ")
    cmd4.append("[user]", style="dim")
    console.print(cmd4)
    console.print("\n[bold]Options:[/bold]")
    console.print("  -h, --help                          Show help")
    console.print("  -v, --version                       Show version")
    console.print()


async def get_token_non_interactive(environment: str, user: str) -> str:
    authenticator = SSOAuthenticator()
    return await authenticator.get_token(environment, user)


async def get_user_roles_non_interactive(environment: str, user: str):
    authenticator = SSOAuthenticator()
    return await authenticator.get_user_roles(environment, user)


def resolve_environment(authenticator: SSOAuthenticator, env_arg: str) -> str:
    env_key = authenticator.find_environment_by_prefix(env_arg)
    if env_key:
        return env_key
    env_matches = authenticator.find_environments_by_prefix(env_arg)
    if len(env_matches) > 1:
        console.print(f"[red]Ambiguous environment '{env_arg}':[/red]")
        for match in env_matches:
            console.print(f"  {match}")
        sys.exit(1)
    return env_matches[0] if env_matches else env_arg


def resolve_user(authenticator: SSOAuthenticator, env_key: str, user_arg: str) -> str:
    user_key = authenticator.find_user_by_key(env_key, user_arg)
    if user_key:
        return user_key
    user_matches = authenticator.find_users_by_prefix(env_key, user_arg)
    if len(user_matches) > 1:
        console.print(f"[red]Ambiguous user '{user_arg}' in '{env_key}':[/red]")
        for key, display in user_matches:
            console.print(f"  {display} ({key})")
        sys.exit(1)
    return user_matches[0][0] if user_matches else user_arg


async def show_roles(authenticator: SSOAuthenticator, env_key: str, user_key: str):
    console.print(f"[yellow]Fetching roles...[/yellow]")
    try:
        roles_data = await authenticator.get_user_roles(env_key, user_key)
        console.print()
        console.print("[bold green]Roles[/bold green]\n")
        if roles_data["jwt"]:
            console.print("[bold]JWT Token:[/bold]")
            console.print("\n".join([f"  • {r}" for r in roles_data["jwt"]]))
        if roles_data["userinfo"]:
            if roles_data["jwt"]:
                console.print()
            console.print("[bold]UserInfo Endpoint:[/bold]")
            console.print("\n".join([f"  • {r}" for r in roles_data["userinfo"]]))
        if not roles_data["jwt"] and not roles_data["userinfo"]:
            console.print("[yellow]No roles[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


async def show_token(authenticator: SSOAuthenticator, env_key: str, user_key: str):
    console.print(f"[yellow]Authenticating...[/yellow]")
    try:
        token = await authenticator.get_token(env_key, user_key)
        console.print()
        if copy_to_clipboard(token):
            console.print("[bold green]Token copied![/bold green]")
        else:
            console.print(f"[bold]Token:[/bold]\n{token}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


async def main_async():
    parser = argparse.ArgumentParser(description="SSO CLI", add_help=False)
    parser.add_argument('environment', nargs='?', help='Environment')
    parser.add_argument('user', nargs='?', help='User')
    parser.add_argument('-r', '--roles', action='store_true', help='List roles')
    parser.add_argument('-l', '--list', metavar='TYPE', help='List: env/envs or user/users')
    parser.add_argument('-d', '--remove', nargs='+', metavar=('TYPE', 'ID'), help='Remove: env <id> or user <env> <user>')
    parser.add_argument('-h', '--help', action='store_true', help='Show help')
    parser.add_argument('-v', '--version', action='store_true', help='Show version')
    
    args = parser.parse_args()
    
    if args.help:
        show_help()
        return
    
    if args.version:
        print(f"sso-cli {get_version()}")
        return
    
    if args.list:
        list_type = args.list.lower()
        authenticator = SSOAuthenticator()
        
        if list_type in ['env', 'envs', 'environment', 'environments']:
            envs = authenticator.get_environments()
            if not envs:
                console.print("[dim]No environments configured[/dim]")
            else:
                for env_key, config in envs.items():
                    sso_url = config.get("sso_url", "")
                    realm = config.get("realm", "")
                    console.print(f"{env_key}: {sso_url}/realms/{realm}")
        
        elif list_type in ['user', 'users']:
            all_users = authenticator.config.get("users", {})
            if not all_users:
                console.print("[dim]No users configured[/dim]")
            else:
                for env_key, users in all_users.items():
                    if users:
                        console.print(f"\n{env_key}:")
                        for user_key, config in users.items():
                            email = config.get("email")
                            client_id = config.get("client_id")
                            auth_type = config.get("auth_type", "password")
                            display = email or client_id or user_key
                            console.print(f"  {user_key}: {display} ({auth_type})")
        else:
            console.print(f"[red]Invalid list type: {args.list}[/red]")
            console.print("Use: env/envs or user/users")
            sys.exit(1)
        return
    
    if args.remove:
        if len(args.remove) < 2:
            console.print("[red]Usage: sso -d <type> <id>[/red]")
            console.print("  sso -d env <env_id>")
            console.print("  sso -d user <env_id> <user_id>")
            sys.exit(1)
        
        remove_type = args.remove[0].lower()
        authenticator = SSOAuthenticator()
        
        if remove_type in ['env', 'envs', 'environment', 'environments']:
            env_id = args.remove[1]
            if authenticator.remove_environment(env_id):
                console.print(f"[green]Environment '{env_id}' removed[/green]")
            else:
                console.print(f"[red]Environment '{env_id}' not found[/red]")
                sys.exit(1)
        
        elif remove_type in ['user', 'users']:
            if len(args.remove) < 3:
                console.print("[red]Usage: sso -d user <env_id> <user_id>[/red]")
                sys.exit(1)
            env_id = args.remove[1]
            user_id = args.remove[2]
            actual_key = authenticator.find_user_by_key(env_id, user_id)
            if not actual_key:
                actual_key = user_id
            if authenticator.remove_user(env_id, actual_key):
                console.print(f"[green]User '{actual_key}' removed from '{env_id}'[/green]")
            else:
                console.print(f"[red]User '{user_id}' not found in '{env_id}'[/red]")
                sys.exit(1)
        else:
            console.print(f"[red]Invalid remove type: {remove_type}[/red]")
            console.print("Use: env/envs or user/users")
            sys.exit(1)
        return
    
    if args.environment and args.user:
        authenticator = SSOAuthenticator()
        env_key = resolve_environment(authenticator, args.environment)
        user_key = resolve_user(authenticator, env_key, args.user)
        try:
            if args.roles:
                roles_data = await get_user_roles_non_interactive(env_key, user_key)
                if roles_data["jwt"]:
                    print("JWT Token:")
                    for role in roles_data["jwt"]:
                        print(f"  {role}")
                if roles_data["userinfo"]:
                    if roles_data["jwt"]:
                        print()
                    print("UserInfo Endpoint:")
                    for role in roles_data["userinfo"]:
                        print(f"  {role}")
            else:
                token = await get_token_non_interactive(env_key, user_key)
                print(token)
            return
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    if args.environment and not args.user:
        console.print()
        console.print("[bold green]SSO CLI[/bold green]\n")
        authenticator = SSOAuthenticator()
        env_key = resolve_environment(authenticator, args.environment)
        if env_key not in authenticator.get_environments():
            authenticator.create_environment(env_key)
        env_users = authenticator.get_available_users_for_environment(env_key)
        if not env_users:
            console.print("[dim]No users. Creating first user...[/dim]\n")
            selected_user = Prompt.ask("User key")
        else:
            selector = ModernSelector()
            user_options = []
            for user_key, config in env_users.items():
                display = config.get("email") or config.get("client_id") or user_key
                user_options.append(display)
            user_choice = selector.select_from_list("User", user_options)
            selected_user = list(env_users.keys())[user_choice]
        if args.roles:
            await show_roles(authenticator, env_key, selected_user)
        else:
            await show_token(authenticator, env_key, selected_user)
        return
    
    if not args.environment and not args.user:
        console.print()
        console.print("[bold green]SSO CLI[/bold green]\n")
        authenticator = SSOAuthenticator()
        selector = ModernSelector()
        envs = authenticator.get_environments()
        
        if not envs:
            console.print("[dim]First use: creating environment...[/dim]\n")
            env_key = Prompt.ask("Environment key", default=args.environment if args.environment else None)
            authenticator.create_environment(env_key)
            selected_env = env_key
        else:
            if args.environment:
                selected_env = resolve_environment(authenticator, args.environment)
                if selected_env not in envs:
                    authenticator.create_environment(selected_env)
            else:
                env_options = [env_key for env_key in envs.keys()]
                env_choice = selector.select_from_list("Environment", env_options)
                selected_env = list(envs.keys())[env_choice]
        
        env_users = authenticator.get_available_users_for_environment(selected_env)
        if not env_users:
            console.print("[dim]No users. Creating first user...[/dim]\n")
            selected_user = Prompt.ask("User key", default=args.user if args.user else None)
        else:
            if args.user:
                selected_user = resolve_user(authenticator, selected_env, args.user)
            else:
                user_options = []
                for user_key, config in env_users.items():
                    display = config.get("email") or config.get("client_id") or user_key
                    user_options.append(display)
                user_choice = selector.select_from_list("User", user_options)
                selected_user = list(env_users.keys())[user_choice]
        
        if args.roles:
            await show_roles(authenticator, selected_env, selected_user)
        else:
            await show_token(authenticator, selected_env, selected_user)
        return
    
    print("Error: Need both env and user", file=sys.stderr)
    sys.exit(1)


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye[/yellow]")
        sys.exit(0)

