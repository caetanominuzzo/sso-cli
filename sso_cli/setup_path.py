"""Setup script to add Python scripts directory to PATH automatically."""

import os
import sys
import sysconfig
import platform
from pathlib import Path


def is_windows():
    """Check if running on Windows."""
    return platform.system() == 'Windows'


def get_shell_config_file():
    """Detect the shell config file based on the current shell and OS."""
    if is_windows():
        # Windows doesn't use shell config files, we'll use environment variables
        return None
    
    shell = os.environ.get('SHELL', '')
    
    if 'zsh' in shell:
        return Path.home() / '.zshrc'
    elif 'bash' in shell:
        # Check for .bash_profile first (macOS), then .bashrc
        bash_profile = Path.home() / '.bash_profile'
        if bash_profile.exists():
            return bash_profile
        return Path.home() / '.bashrc'
    elif 'fish' in shell:
        return Path.home() / '.config' / 'fish' / 'config.fish'
    else:
        # Default to .zshrc for macOS, .bashrc for Linux
        if platform.system() == 'Darwin':
            return Path.home() / '.zshrc'
        return Path.home() / '.bashrc'


def get_scripts_path():
    """Get the Python scripts directory."""
    if is_windows():
        # On Windows, scripts are in Scripts, not bin
        try:
            import site
            user_base = site.getuserbase()
            scripts_path = os.path.join(user_base, 'Scripts')
            if os.path.exists(scripts_path):
                return scripts_path
        except Exception:
            pass
        # Fallback
        return sysconfig.get_path('scripts')
    else:
        # Unix-like systems
        try:
            import site
            user_base = site.getuserbase()
            scripts_path = os.path.join(user_base, 'bin')
            if os.path.exists(scripts_path):
                return scripts_path
        except Exception:
            pass
        # Fallback to sysconfig
        return sysconfig.get_path('scripts')


def setup_path_windows(scripts_path):
    """Setup PATH on Windows."""
    try:
        import winreg
        
        # Get current user PATH
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Environment',
                0,
                winreg.KEY_READ | winreg.KEY_WRITE
            )
        except PermissionError:
            print("⚠️  Insufficient permissions to modify PATH via registry")
            print(f"💡 Manually add this to your PATH environment variable:")
            print(f"   {scripts_path}")
            return False
        
        try:
            current_path, _ = winreg.QueryValueEx(key, 'Path')
        except FileNotFoundError:
            current_path = ''
        
        # Check if already in PATH
        paths = [p.strip() for p in current_path.split(os.pathsep) if p.strip()]
        if scripts_path in paths:
            print(f"✅ PATH already configured (Windows)")
            winreg.CloseKey(key)
            return True
        
        # Add to PATH
        new_path = current_path + os.pathsep + scripts_path if current_path else scripts_path
        try:
            winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)
            winreg.CloseKey(key)
            
            print(f"✅ Added {scripts_path} to PATH (Windows)")
            print("📝 Please restart your terminal for changes to take effect")
            return True
        except Exception as e:
            winreg.CloseKey(key)
            raise e
        
    except ImportError:
        # winreg not available (shouldn't happen on Windows, but just in case)
        print(f"⚠️  Could not modify PATH automatically (Windows)")
        print(f"💡 Manually add this to your PATH environment variable:")
        print(f"   {scripts_path}")
        return False
    except Exception as e:
        print(f"❌ Failed to update PATH (Windows): {e}")
        print(f"💡 Manually add this to your PATH environment variable:")
        print(f"   {scripts_path}")
        print("\n   Or use PowerShell (as Administrator):")
        print(f"   [Environment]::SetEnvironmentVariable('Path', $env:Path + ';{scripts_path}', 'User')")
        return False


def setup_path_unix(scripts_path, config_file):
    """Setup PATH on Unix-like systems (macOS, Linux)."""
    path_export = f'export PATH="{scripts_path}:$PATH"'
    
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already configured
        if scripts_path in content:
            if path_export in content or f'"{scripts_path}' in content:
                print(f"✅ PATH already configured in {config_file}")
                return True
    
    # Add to config file
    try:
        with open(config_file, 'a', encoding='utf-8') as f:
            f.write(f'\n# Added by sso-cli\n{path_export}\n')
        print(f"✅ Added {scripts_path} to PATH in {config_file}")
        print(f"📝 Run: source {config_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to update {config_file}: {e}")
        print(f"💡 Manually add this line to {config_file}:")
        print(f"   {path_export}")
        return False


def setup_path():
    """Add Python scripts directory to PATH."""
    scripts_path = get_scripts_path()
    
    if not scripts_path or not os.path.exists(scripts_path):
        print(f"⚠️  Scripts directory not found: {scripts_path}")
        return False
    
    if is_windows():
        return setup_path_windows(scripts_path)
    else:
        config_file = get_shell_config_file()
        if not config_file:
            print("⚠️  Could not determine shell config file")
            return False
        return setup_path_unix(scripts_path, config_file)


if __name__ == '__main__':
    setup_path()

