#!/usr/bin/env bash
# create_qcow2_disk.sh
# Script to create a dynamic 64GB QCOW2 virtual hard disk for Windows 11 installation.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DISK_PATH="${1:-${SCRIPT_DIR}/windows11_portable.qcow2}"
DISK_SIZE="${2:-64G}"

if ! command -v qemu-img &> /dev/null; then
    echo "[ERROR] qemu-img is not installed or not in PATH."
    exit 1
fi

if [ -f "${DISK_PATH}" ]; then
    echo "[WARNING] Disk image ${DISK_PATH} already exists."
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "[INFO] Aborted disk creation."
        exit 0
    fi
fi

echo "[INFO] Creating ${DISK_SIZE} dynamic QCOW2 virtual disk at ${DISK_PATH}..."
qemu-img create -f qcow2 "${DISK_PATH}" "${DISK_SIZE}"
echo "[SUCCESS] Virtual disk ${DISK_PATH} created successfully!"
