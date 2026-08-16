#!/usr/bin/env bash
# start_qemu_tails.sh
# Специален QEMU стартер за Tails OS (с проверка за нужните пакети и KVM)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Проверка дали имаме администраторски права
if [ "$EUID" -ne 0 ]; then
  echo "[ВНИМАНИЕ] За да инсталираме QEMU и заредим KVM в Tails, са нужни администраторски права."
  echo "Опитвам се да стартирам със sudo..."
  exec sudo bash "$0" "$@"
fi

# 2. Инсталиране на QEMU, ако липсва
if ! command -v qemu-system-x86_64 &> /dev/null; then
    echo "[INFO] qemu-system-x86_64 не е намерен. Започвам инсталация..."
    apt-get update
    apt-get install -y qemu-system-x86 qemu-utils
else
    echo "[INFO] QEMU вече е инсталиран."
fi

# 3. Зареждане на KVM модулите
echo "[INFO] Зареждане на KVM модулите..."
modprobe kvm || echo "[ВНИМАНИЕ] Не мога да заредя kvm модула."
modprobe kvm_intel 2>/dev/null || true
modprobe kvm_amd 2>/dev/null || true

if [ ! -c /dev/kvm ]; then
    echo "[ГРЕШКА] /dev/kvm не съществува. Хардуерната виртуализация не работи."
    echo "Уверете се, че виртуализацията е включена в BIOS-а на вашия Asus Vivobook!"
    # Продължаваме, но QEMU вероятно ще гръмне
fi

# Configuration Paths
WIN11_ISO="${WIN11_ISO:-${SCRIPT_DIR}/Win11_x64.iso}"
AUTOUNATTEND_ISO="${AUTOUNATTEND_ISO:-${SCRIPT_DIR}/autounattend.iso}"
VIRTIO_ISO="${VIRTIO_ISO:-${SCRIPT_DIR}/virtio-win.iso}"
DISK_IMAGE="${DISK_IMAGE:-${SCRIPT_DIR}/windows11_portable.qcow2}"
MONITOR_SOCK="/tmp/qemu-monitor.sock"

# Auto-generate autounattend.iso if missing
if [ ! -f "${AUTOUNATTEND_ISO}" ]; then
    echo "[INFO] autounattend.iso липсва. Генериране..."
    bash "${SCRIPT_DIR}/create_autounattend_iso.sh"
fi

# Auto-generate disk image if missing
if [ ! -f "${DISK_IMAGE}" ]; then
    echo "[INFO] ${DISK_IMAGE} липсва. Създаване на 64GB QCOW2 образ..."
    bash "${SCRIPT_DIR}/create_qcow2_disk.sh" "${DISK_IMAGE}" "64G"
fi

# Build ISO drive flags
ISO_DRIVE_FLAGS=""
if [ -f "${WIN11_ISO}" ]; then
    echo "[INFO] Монтиране на Windows 11 Installer ISO: ${WIN11_ISO}"
    ISO_DRIVE_FLAGS="${ISO_DRIVE_FLAGS} -drive file=${WIN11_ISO},if=none,id=cdrom0,media=cdrom,readonly=on,file.locking=off -device ide-cd,drive=cdrom0,bus=ahci0.1,bootindex=0"
fi

if [ -f "${AUTOUNATTEND_ISO}" ]; then
    echo "[INFO] Монтиране на Autounattend Bypass ISO: ${AUTOUNATTEND_ISO}"
    ISO_DRIVE_FLAGS="${ISO_DRIVE_FLAGS} -drive file=${AUTOUNATTEND_ISO},if=none,id=cdrom2,media=cdrom,readonly=on,file.locking=off -device ide-cd,drive=cdrom2,bus=ahci0.3"
fi

if [ -f "${VIRTIO_ISO}" ]; then
    echo "[INFO] Монтиране на VirtIO Drivers ISO: ${VIRTIO_ISO}"
    ISO_DRIVE_FLAGS="${ISO_DRIVE_FLAGS} -drive file=${VIRTIO_ISO},if=none,id=cdrom1,media=cdrom,readonly=on,file.locking=off -device ide-cd,drive=cdrom1,bus=ahci0.2,bootindex=2"
fi

echo "[INFO] Стартиране на QEMU Windows 11 VM... (С намалена RAM на 3GB за Tails OS)"
exec qemu-system-x86_64 \
    -enable-kvm \
    -cpu host,migratable=on \
    -machine q35 \
    -m 3072 \
    -smp 4 \
    -device ahci,id=ahci0 \
    -drive file="${DISK_IMAGE}",format=qcow2,if=none,id=hd0,file.locking=off \
    -device ide-hd,drive=hd0,bus=ahci0.0,bootindex=1 \
    ${ISO_DRIVE_FLAGS} \
    -boot order=d \
    -netdev user,id=net0 \
    -device virtio-net-pci,netdev=net0 \
    -vga std \
    -usb \
    -device usb-tablet \
    -device usb-kbd \
    -vnc :1 \
    -monitor unix:"${MONITOR_SOCK}",server,nowait \
    -name "Portable Windows VM (Tails OS)"
