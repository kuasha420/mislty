#!/usr/bin/env bash
# ==============================================================================
# MisLTy Standalone Linux AppImage Packaging Recipe
# Purrfect Software Limited (PSL)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${SCRIPT_DIR}/dist"
APPDIR="${DIST_DIR}/MisLTy.AppDir"

echo "➔ Building MisLTy Portable Linux AppImage..."

# 1. Clean previous build artifacts
rm -rf "${APPDIR}" "${DIST_DIR}/mislty"

# 2. Build executable via PyInstaller if available
if command -v pyinstaller >/dev/null 2>&1; then
    echo "➔ Compiling binary via PyInstaller spec..."
    pyinstaller --noconfirm --clean "${SCRIPT_DIR}/mislty.spec"
else
    echo "➔ Note: pyinstaller not found in PATH; using direct launcher template."
fi

# 3. Assemble AppDir structure
echo "➔ Assembling AppDir structure at ${APPDIR}..."
mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/share/applications"
mkdir -p "${APPDIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${APPDIR}/usr/lib/mislty"

# Copy desktop and icon assets
cp "${SCRIPT_DIR}/deploy/mislty.desktop" "${APPDIR}/"
cp "${SCRIPT_DIR}/deploy/mislty.desktop" "${APPDIR}/usr/share/applications/"
cp "${SCRIPT_DIR}/deploy/icons/mislty.svg" "${APPDIR}/"
cp "${SCRIPT_DIR}/deploy/icons/mislty.svg" "${APPDIR}/usr/share/icons/hicolor/scalable/apps/"

# Copy binary or fallback Python bundle
if [ -f "${DIST_DIR}/mislty" ]; then
    cp "${DIST_DIR}/mislty" "${APPDIR}/usr/bin/mislty"
else
    cp -r "${SCRIPT_DIR}/src/mislty" "${APPDIR}/usr/lib/mislty/"
    cat << 'EOF' > "${APPDIR}/usr/bin/mislty"
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PYTHONPATH="${HERE}/../lib/mislty/mislty:${PYTHONPATH:-}"
exec python3 -m mislty.cli.main "$@"
EOF
    chmod +x "${APPDIR}/usr/bin/mislty"
fi

# 4. Create AppRun entrypoint
cat << 'EOF' > "${APPDIR}/AppRun"
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH:-}"
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
exec "${HERE}/usr/bin/mislty" "$@"
EOF
chmod +x "${APPDIR}/AppRun"

# 5. Build AppImage if appimagetool is present
if command -v appimagetool >/dev/null 2>&1; then
    echo "➔ Packaging into standalone MisLTy-x86_64.AppImage..."
    ARCH=x86_64 appimagetool "${APPDIR}" "${DIST_DIR}/MisLTy-x86_64.AppImage"
    echo "✔ Successfully generated ${DIST_DIR}/MisLTy-x86_64.AppImage"
else
    echo "➔ appimagetool not found; AppDir structure is prepared and fully portable at:"
    echo "  ${APPDIR}"
fi
