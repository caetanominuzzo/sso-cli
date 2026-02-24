#!/bin/bash
# Increment version and publish sso-cli to public PyPI
# Usage: ./bump_and_publish.sh [patch|minor|major]
#   patch: 1.0.0 -> 1.0.1 (default)
#   minor: 1.0.0 -> 1.1.0
#   major: 1.0.0 -> 2.0.0

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Get current version from pyproject.toml
CURRENT_VERSION=$(grep '^version = ' pyproject.toml | head -1 | cut -d '"' -f2 | tr -d '\n\r')

if [ -z "$CURRENT_VERSION" ]; then
    echo -e "${RED}❌ Error: Could not find version in pyproject.toml${NC}"
    exit 1
fi

# Parse version parts
IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR="${VERSION_PARTS[0]}"
MINOR="${VERSION_PARTS[1]}"
PATCH="${VERSION_PARTS[2]}"

# Determine bump type (default: patch)
BUMP_TYPE="${1:-patch}"

# Calculate new version
case "$BUMP_TYPE" in
    major)
        NEW_MAJOR=$((MAJOR + 1))
        NEW_VERSION="${NEW_MAJOR}.0.0"
        ;;
    minor)
        NEW_MINOR=$((MINOR + 1))
        NEW_VERSION="${MAJOR}.${NEW_MINOR}.0"
        ;;
    patch)
        NEW_PATCH=$((PATCH + 1))
        NEW_VERSION="${MAJOR}.${MINOR}.${NEW_PATCH}"
        ;;
    *)
        echo -e "${RED}❌ Error: Invalid bump type '$BUMP_TYPE'${NC}"
        echo "Usage: $0 [patch|minor|major]"
        echo "  patch: $CURRENT_VERSION -> ${MAJOR}.${MINOR}.$((PATCH + 1)) (default)"
        echo "  minor: $CURRENT_VERSION -> ${MAJOR}.$((MINOR + 1)).0"
        echo "  major: $CURRENT_VERSION -> $((MAJOR + 1)).0.0"
        exit 1
        ;;
esac

echo -e "${BLUE}📦 Version Bump & Publish${NC}"
echo ""
echo -e "Current version: ${YELLOW}$CURRENT_VERSION${NC}"
echo -e "Bump type:       ${YELLOW}$BUMP_TYPE${NC}"
echo -e "New version:     ${GREEN}$NEW_VERSION${NC}"
echo ""

# Confirm
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}❌ Cancelled${NC}"
    exit 0
fi

# Update version in pyproject.toml
echo -e "${YELLOW}📝 Updating version in pyproject.toml...${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
else
    # Linux
    sed -i "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
fi
echo -e "${GREEN}✅ Updated to version $NEW_VERSION${NC}"

# Call publish.sh with the new version
echo ""
echo -e "${BLUE}🚀 Publishing...${NC}"
echo ""
./publish.sh "$NEW_VERSION"

# Show reinstall instructions
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Published successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📥 To install/upgrade the new version:${NC}"
echo ""
echo -e "  ${BLUE}pip install --upgrade sso-cli${NC}"
echo ""
echo -e "${YELLOW}🔍 Verify installation:${NC}"
echo ""
echo -e "  ${BLUE}pip show sso-cli${NC}"
echo ""
echo -e "${YELLOW}🧪 Test the new version:${NC}"
echo ""
echo -e "  ${BLUE}sso --help${NC}"
echo ""

