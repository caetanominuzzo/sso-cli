#!/bin/bash
# Publish sso-cli to public PyPI only
# Usage: ./publish.sh [version]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration (public PyPI only)
PUBLIC_PYPI_SERVER="${PUBLIC_PYPI_SERVER:-https://upload.pypi.org/legacy/}"
PUBLIC_PYPI_USERNAME="${PUBLIC_PYPI_USERNAME:-}"
PUBLIC_PYPI_PASSWORD="${PUBLIC_PYPI_PASSWORD:-}"
PYPI_API_TOKEN="${PYPI_API_TOKEN:-${PYPI_ORG_TOKEN:-}}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${GREEN}🚀 Publishing sso-cli to public PyPI${NC}"
echo ""

# Check if version is provided
if [ -n "$1" ]; then
    VERSION="$1"
    echo -e "${YELLOW}📌 Using provided version: $VERSION${NC}"
    
    # Update version in pyproject.toml
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
    else
        # Linux
        sed -i "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
    fi
    echo -e "${GREEN}✅ Updated version in pyproject.toml${NC}"
else
    # Extract version from pyproject.toml
    VERSION=$(grep '^version = ' pyproject.toml | head -1 | cut -d '"' -f2 | tr -d '\n\r')
    echo -e "${YELLOW}📌 Using version from pyproject.toml: $VERSION${NC}"
fi

# Check for credentials (prefer API token)
if [ -n "$PYPI_API_TOKEN" ]; then
    PUBLIC_PYPI_USERNAME="__token__"
    PUBLIC_PYPI_PASSWORD="$PYPI_API_TOKEN"
fi

if [ -z "$PUBLIC_PYPI_USERNAME" ] || [ -z "$PUBLIC_PYPI_PASSWORD" ]; then
    echo -e "${RED}❌ Error: set PYPI_API_TOKEN or PUBLIC_PYPI_USERNAME/PUBLIC_PYPI_PASSWORD${NC}"
    echo ""
    echo "Recommended (API token):"
    echo "  export PYPI_API_TOKEN=pypi-..."
    echo ""
    echo "Alternative (user/password):"
    echo "  export PUBLIC_PYPI_USERNAME=__token__"
    echo "  export PUBLIC_PYPI_PASSWORD=pypi-..."
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python found: $(python3 --version)${NC}"

# Install/upgrade build tools
echo ""
echo -e "${YELLOW}📦 Installing build tools...${NC}"
python3 -m pip install --upgrade pip --quiet
python3 -m pip install --upgrade build twine --quiet

# Clean previous builds
echo ""
echo -e "${YELLOW}🧹 Cleaning previous builds...${NC}"
rm -rf dist/ build/ *.egg-info
echo -e "${GREEN}✅ Cleaned${NC}"

# Verify package structure
echo ""
echo -e "${YELLOW}🔍 Verifying package structure...${NC}"
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ pyproject.toml not found!${NC}"
    exit 1
fi

if [ ! -d "sso_cli" ]; then
    echo -e "${RED}❌ sso_cli/ package not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Package structure verified${NC}"

# Build package
echo ""
echo -e "${YELLOW}🔨 Building package (version $VERSION)...${NC}"
export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring
python3 -m build

if [ ! -d "dist" ] || [ -z "$(ls -A dist)" ]; then
    echo -e "${RED}❌ Build failed - dist/ directory is empty${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Build successful${NC}"
echo ""
echo "Built files:"
ls -lh dist/

# Publish to public PyPI
echo ""
echo -e "${YELLOW}📤 Uploading to public PyPI ($PUBLIC_PYPI_SERVER)...${NC}"
TWINE_USERNAME="$PUBLIC_PYPI_USERNAME" \
TWINE_PASSWORD="$PUBLIC_PYPI_PASSWORD" \
python3 -m twine upload --repository-url "$PUBLIC_PYPI_SERVER" dist/* --verbose

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ Public upload failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Successfully published sso-cli v$VERSION to public PyPI${NC}"
echo ""
echo "Install from public:"
echo "  pip install --upgrade sso-cli"
echo ""
echo "Then configure sso_config.yaml and run:"
echo "  sso"

