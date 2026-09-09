#!/usr/bin/env bash
# ==============================================================================
# MisLTy: Build Offline MicroSD Deployment Bundle
# Purrfect Software Limited (PSL)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${1:-${SCRIPT_DIR}/dist/mislty-offline-bundle}"

echo "Building MisLTy offline bootstrap bundle in ${OUTPUT_DIR}..."
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}/deploy" "${OUTPUT_DIR}/config" "${OUTPUT_DIR}/src" "${OUTPUT_DIR}/bin"

# Copy installation scripts
cp "${SCRIPT_DIR}/deploy/install.sh" "${OUTPUT_DIR}/deploy/"
cp "${SCRIPT_DIR}/deploy/uninstall.sh" "${OUTPUT_DIR}/deploy/"
chmod +x "${OUTPUT_DIR}/deploy/"*.sh

# Create root-level autorun/installer symlink or script
cat << 'EOF' > "${OUTPUT_DIR}/INSTALL.sh"
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec sudo "${SCRIPT_DIR}/deploy/install.sh" "$@"
EOF
chmod +x "${OUTPUT_DIR}/INSTALL.sh"

# Copy configurations
cp -r "${SCRIPT_DIR}/config/"* "${OUTPUT_DIR}/config/"

# Copy binary wrappers
cp -r "${SCRIPT_DIR}/bin/"* "${OUTPUT_DIR}/bin/"

# Copy Python package source
cp -r "${SCRIPT_DIR}/src/mislty" "${OUTPUT_DIR}/src/"
cp "${SCRIPT_DIR}/pyproject.toml" "${OUTPUT_DIR}/"
cp "${SCRIPT_DIR}/README.md" "${OUTPUT_DIR}/"

echo "✔ Offline bundle created successfully at ${OUTPUT_DIR}."
