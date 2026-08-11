#!/usr/bin/env bash
# create_autounattend_iso.sh
# Cross-platform script to build autounattend.iso containing WinPE hardware check bypasses.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
XML_SOURCE="${SCRIPT_DIR}/autounattend.xml"
OUTPUT_ISO="${SCRIPT_DIR}/autounattend.iso"
BUILD_DIR="$(mktemp -d /tmp/unattend_build.XXXXXX)"

cleanup() {
    rm -rf "${BUILD_DIR}"
}
trap cleanup EXIT

if [ ! -f "${XML_SOURCE}" ]; then
    echo "[ERROR] autounattend.xml not found at ${XML_SOURCE}"
    exit 1
fi

cp "${XML_SOURCE}" "${BUILD_DIR}/autounattend.xml"

echo "[INFO] Creating autounattend.iso..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    hdiutil makehybrid -iso -joliet -o "${OUTPUT_ISO}" "${BUILD_DIR}"
elif command -v mkisofs &> /dev/null; then
    mkisofs -J -r -o "${OUTPUT_ISO}" "${BUILD_DIR}"
elif command -v genisoimage &> /dev/null; then
    genisoimage -J -r -o "${OUTPUT_ISO}" "${BUILD_DIR}"
elif command -v xorrisofs &> /dev/null; then
    xorrisofs -J -r -o "${OUTPUT_ISO}" "${BUILD_DIR}"
else
    echo "[ERROR] No suitable ISO generation tool found (hdiutil, mkisofs, genisoimage, xorrisofs)."
    exit 1
fi

echo "[SUCCESS] Generated ${OUTPUT_ISO} successfully!"
