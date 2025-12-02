"""Post-installation hook to setup PATH automatically."""

import sys
import subprocess


def post_install():
    """Run after package installation to setup PATH."""
    try:
        # Import and run setup_path
        from .setup_path import setup_path
        setup_path()
        print("\n✨ sso-cli installed successfully!")
        print("💡 If 'sso' command is not found, run: sso-setup-path")
        print("   Or manually source your shell config file.")
    except Exception as e:
        print(f"⚠️  Could not auto-configure PATH: {e}")
        print("💡 Run 'sso-setup-path' manually to configure PATH")


if __name__ == '__main__':
    post_install()

