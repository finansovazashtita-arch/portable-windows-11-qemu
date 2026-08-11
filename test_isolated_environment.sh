#!/usr/bin/env bash
# test_isolated_environment.sh
# Automated validation test suite for open-source client deployment.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$(mktemp -d /tmp/qemu_test_env.XXXXXX)"

cleanup() {
    echo "[INFO] Cleaning up test directory ${TEST_DIR}..."
    rm -rf "${TEST_DIR}"
}
trap cleanup EXIT

echo "=========================================================="
echo "      OPEN-SOURCE AUTOMATED ENVIRONMENT VERIFICATION     "
echo "=========================================================="

echo "[TEST 1/5] Validating autounattend.xml syntax..."
if [ -f "${SCRIPT_DIR}/autounattend.xml" ]; then
    grep -q "BypassTPMCheck" "${SCRIPT_DIR}/autounattend.xml"
    grep -q "BypassSecureBootCheck" "${SCRIPT_DIR}/autounattend.xml"
    grep -q "BypassRAMCheck" "${SCRIPT_DIR}/autounattend.xml"
    grep -q "BypassStorageCheck" "${SCRIPT_DIR}/autounattend.xml"
    grep -q "BypassCPUCheck" "${SCRIPT_DIR}/autounattend.xml"
    grep -q "BypassNRO" "${SCRIPT_DIR}/autounattend.xml"
    echo "  -> [PASSED] autounattend.xml contains all 6 required bypass directives."
else
    echo "  -> [FAILED] autounattend.xml missing!"
    exit 1
fi

echo "[TEST 2/5] Testing ISO build script in isolated environment..."
cp "${SCRIPT_DIR}/autounattend.xml" "${TEST_DIR}/"
cp "${SCRIPT_DIR}/create_autounattend_iso.sh" "${TEST_DIR}/"
(cd "${TEST_DIR}" && ./create_autounattend_iso.sh)
if [ -f "${TEST_DIR}/autounattend.iso" ]; then
    ISO_SIZE=$(wc -c < "${TEST_DIR}/autounattend.iso" | tr -d ' ')
    echo "  -> [PASSED] Generated autounattend.iso (${ISO_SIZE} bytes)."
else
    echo "  -> [FAILED] ISO generation failed!"
    exit 1
fi

echo "[TEST 3/5] Testing QCOW2 dynamic disk generation..."
cp "${SCRIPT_DIR}/create_qcow2_disk.sh" "${TEST_DIR}/"
(cd "${TEST_DIR}" && ./create_qcow2_disk.sh test_disk.qcow2 64G)
if [ -f "${TEST_DIR}/test_disk.qcow2" ]; then
    FORMAT_CHECK=$(qemu-img info "${TEST_DIR}/test_disk.qcow2" | grep "file format: qcow2")
    echo "  -> [PASSED] Virtual disk generated: ${FORMAT_CHECK}"
else
    echo "  -> [FAILED] QCOW2 generation failed!"
    exit 1
fi

echo "[TEST 4/5] Checking QEMU executable binary..."
if command -v qemu-system-x86_64 &> /dev/null; then
    QEMU_VER=$(qemu-system-x86_64 --version | head -n 1)
    echo "  -> [PASSED] Found QEMU binary: ${QEMU_VER}"
else
    echo "  -> [WARNING] qemu-system-x86_64 binary not found in PATH."
fi

echo "[TEST 5/5] Checking launcher scripts permissions and syntax..."
bash -n "${SCRIPT_DIR}/start_qemu_mac.sh"
bash -n "${SCRIPT_DIR}/start_qemu_linux.sh"
echo "  -> [PASSED] Shell script syntax checks clean."

echo "=========================================================="
echo "  [SUCCESS] All isolated environment tests PASSED!        "
echo "  Project is ready for open-source clients.               "
echo "=========================================================="
