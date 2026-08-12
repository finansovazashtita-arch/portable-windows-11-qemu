#!/usr/bin/env bash
# start_qemu_linux.sh
# QEMU Launcher script for Windows 11 on Linux (with KVM acceleration).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration Paths
WIN11_ISO="${WIN11_ISO:-${SCRIPT_DIR}/Win11_x64.iso}"
AUTOUNATTEND_ISO="${AUTOUNATTEND_ISO:-${SCRIPT_DIR}/autounattend.iso}"
VIRTIO_ISO="${VIRTIO_ISO:-${SCRIPT_DIR}/virtio-win.iso}"
DISK_IMAGE="${DISK_IMAGE:-${SCRIPT_DIR}/windows11_portable.qcow2}"
MONITOR_SOCK="/tmp/qemu-monitor.sock"

# Auto-generate autounattend.iso if missing
if [ ! -f "${AUTOUNATTEND_ISO}" ]; then
    echo "[INFO] autounattend.iso missing. Generating..."
    "${SCRIPT_DIR}/create_autounattend_iso.sh"
fi

# Auto-generate disk image if missing
if [ ! -f "${DISK_IMAGE}" ]; then
    echo "[INFO] ${DISK_IMAGE} missing. Creating 64GB QCOW2 image..."
    "${SCRIPT_DIR}/create_qcow2_disk.sh" "${DISK_IMAGE}" "64G"
fi

# Build ISO drive flags
ISO_DRIVE_FLAGS=""
if [ -f "${WIN11_ISO}" ]; then
    echo "[INFO] Mounting Windows 11 Installer ISO: ${WIN11_ISO}"
    ISO_DRIVE_FLAGS="${ISO_DRIVE_FLAGS} -drive file=${WIN11_ISO},if=none,id=cdrom0,media=cdrom,readonly=on,file.locking=off -device ide-cd,drive=cdrom0,bus=ahci0.1,bootindex=0"
else
    echo "[WARNING] Windows 11 ISO not found at ${WIN11_ISO}. Booting from disk only."
fi

if [ -f "${AUTOUNATTEND_ISO}" ]; then
    echo "[INFO] Mounting Autounattend Bypass ISO: ${AUTOUNATTEND_ISO}"
    ISO_DRIVE_FLAGS="${ISO_DRIVE_FLAGS} -drive file=${AUTOUNATTEND_ISO},if=none,id=cdrom2,media=cdrom,readonly=on,file.locking=off -device ide-cd,drive=cdrom2,bus=ahci0.3"
fi

if [ -f "${VIRTIO_ISO}" ]; then
    echo "[INFO] Mounting VirtIO Drivers ISO: ${VIRTIO_ISO}"
    ISO_DRIVE_FLAGS="${ISO_DRIVE_FLAGS} -drive file=${VIRTIO_ISO},if=none,id=cdrom1,media=cdrom,readonly=on,file.locking=off -device ide-cd,drive=cdrom1,bus=ahci0.2,bootindex=2"
fi

echo "[INFO] Starting QEMU Windows 11 VM on Linux (KVM enabled)..."
exec qemu-system-x86_64 \
    -enable-kvm \
    -cpu host,migratable=on \
    -machine q35 \
    -m 4096 \
    -smp 4 \
    -device ahci,id=ahci0 \
    -drive file="${DISK_IMAGE}",format=qcow2,if=none,id=hd0,file.locking=off \
    -device ide-hd,drive=hd0,bus=ahci0.0,bootindex=1 \
    ${ISO_DRIVE_FLAGS} \
    -boot order=d \
    -netdev user,id=net0,hostfwd=tcp:127.0.0.1:3389-:3389,hostfwd=tcp:127.0.0.1:5678-:5678 \
    -device virtio-net-pci,netdev=net0 \
    -vga std \
    -usb \
    -device usb-tablet \
    -device usb-kbd \
    -vnc :1 \
    -monitor unix:"${MONITOR_SOCK}",server,nowait \
    -name "Portable Windows VM (OpenBalancer)"
