#!/usr/bin/env bash
# Build a standalone binary using PyInstaller.
#
# Usage:
#   ./scripts/build.sh            # build for current platform
#
# Output:
#   dist/b2b-data-bridge          (macOS/Linux)
#   dist/b2b-data-bridge.exe      (Windows)
#   dist/b2b-data-bridge-bundle/  (ready-to-ship folder with config template)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Building B2B Data Bridge standalone binary ==="
echo ""

# 1. Ensure pyinstaller is installed
if ! python -m PyInstaller --version &>/dev/null; then
    echo "[*] Installing PyInstaller..."
    pip install pyinstaller
fi

# 2. Clean previous builds
rm -rf build/ dist/

# 3. Run PyInstaller
echo "[*] Running PyInstaller..."
python -m PyInstaller b2b-data-bridge.spec --noconfirm

# 4. Create a distribution bundle
BUNDLE_DIR="dist/b2b-data-bridge-bundle"
mkdir -p "$BUNDLE_DIR/config"

# Copy the binary
if [[ -f dist/b2b-data-bridge ]]; then
    cp dist/b2b-data-bridge "$BUNDLE_DIR/"
elif [[ -f dist/b2b-data-bridge.exe ]]; then
    cp dist/b2b-data-bridge.exe "$BUNDLE_DIR/"
fi

# Copy sample config
cp config/settings.yaml "$BUNDLE_DIR/config/settings.yaml"
cp .env.example "$BUNDLE_DIR/.env.example"

# Copy sample files
if [[ -d samples ]]; then
    cp -r samples "$BUNDLE_DIR/samples"
fi

echo ""
echo "=== Build complete ==="
echo ""
echo "Distribution bundle: $BUNDLE_DIR/"
echo ""
echo "Contents:"
ls -la "$BUNDLE_DIR/"
echo ""
echo "To deliver to client:"
echo "  1. ZIP the bundle:  cd dist && zip -r b2b-data-bridge-bundle.zip b2b-data-bridge-bundle/"
echo "  2. Send the ZIP to the client"
echo "  3. Client unzips, edits config/settings.yaml, and runs ./b2b-data-bridge outbound"
