# Portable Windows 11 QEMU Virtual Machine

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: macOS | Linux](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux-brightgreen.svg)]()
[![QEMU Version](https://img.shields.io/badge/QEMU-v8.0%2B-orange.svg)]()

Automated, zero-config, portable Windows 11 virtual machine launcher for QEMU on macOS and Linux. Automatically bypasses Windows 11 hardware checks (TPM 2.0, Secure Boot, CPU, RAM, Storage Size) and network/online Microsoft account enforcement in Out-of-Box Experience (OOBE).

---

## 📋 Overview & Problem Resolution Summary

### The Problem
During initial Windows 11 setup on virtual drives, users frequently encounter disk partition errors such as:
> **"Windows 11 не може да се инсталира на диск 0 дял 3."** (*Windows 11 cannot be installed to Disk 0 Partition 3*)

Additionally, standard Windows 11 installer ISOs block installation on virtual machines lacking hardware TPM 2.0, Secure Boot, 64 GB disk space, or 4 GB+ RAM.

### Root Causes
1. **Disk Size & Partition Schema**: Windows 11 requires a minimum disk space of 52-64 GB. When installed on smaller VHDX/QCOW2 images (e.g. 40 GB), Windows Setup fails at partition creation.
2. **Hardware Requirement Checks**: WinPE verifies hardware compliance before allowing partition selection.
3. **Online Account Enforcement**: Windows 11 OOBE setup forces a network connection and Microsoft account login.

### The Solution Architecture
- **Dynamic 64 GB QCOW2 Storage**: Allocates a dynamic `windows11_portable.qcow2` image (starts at <10 MB, expands up to 64 GB on demand).
- **Automated WinPE Bypass ISO (`autounattend.iso`)**: Generates a secondary ISO containing `autounattend.xml`. During boot, WinPE automatically executes registry commands under `HKLM\SYSTEM\Setup\LabConfig` before compliance checks run:
  - `BypassTPMCheck = 1`
  - `BypassSecureBootCheck = 1`
  - `BypassRAMCheck = 1`
  - `BypassStorageCheck = 1`
  - `BypassCPUCheck = 1`
  - `BypassNRO = 1` (Bypasses network requirement, enabling local account setup)
- **AHCI SATA Controller Setup**: Configures ide-hd on `ahci0.0` for maximum compatibility across macOS and Linux hosts.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
Ensure `qemu` and ISO generation tools are installed:

#### On macOS:
```bash
brew install qemu
```

#### On Linux (Ubuntu / Debian / Fedora / Arch):
```bash
# Ubuntu / Debian
sudo apt update && sudo apt install qemu-system-x86 qemu-utils genisoimage

# Fedora
sudo dnf install qemu-system-x86 qemu-img genisoimage

# Arch Linux
sudo pacman -S qemu-desktop xorriso
```

### 2. Clone Repository
```bash
git clone https://github.com/finansovazashtita-arch/portable-windows-11-qemu.git
cd portable-windows-11-qemu
```

### 3. Add Windows 11 ISO
Place your official Windows 11 ISO in the project directory renamed to `Win11_x64.iso` (or set `WIN11_ISO=/path/to/your/iso`).

### 4. Launch the Virtual Machine

#### On macOS:
```bash
./start_qemu_mac.sh
```

#### On Linux:
```bash
./start_qemu_linux.sh
```

---

## ⚙️ Detailed Step-by-Step Technical Guide

### Step 1: Generating the Unattend Hardware Bypass ISO
`autounattend.xml` contains synchronous commands executed during the `windowsPE` configuration pass:
```xml
<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
    <settings pass="windowsPE">
        <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
            <RunSynchronous>
                <RunSynchronousCommand wcm:action="add">
                    <Order>1</Order>
                    <Path>cmd /c reg add HKLM\SYSTEM\Setup\LabConfig /v BypassTPMCheck /t REG_DWORD /d 1 /f</Path>
                </RunSynchronousCommand>
                <RunSynchronousCommand wcm:action="add">
                    <Order>2</Order>
                    <Path>cmd /c reg add HKLM\SYSTEM\Setup\LabConfig /v BypassSecureBootCheck /t REG_DWORD /d 1 /f</Path>
                </RunSynchronousCommand>
                <RunSynchronousCommand wcm:action="add">
                    <Order>3</Order>
                    <Path>cmd /c reg add HKLM\SYSTEM\Setup\LabConfig /v BypassRAMCheck /t REG_DWORD /d 1 /f</Path>
                </RunSynchronousCommand>
                <RunSynchronousCommand wcm:action="add">
                    <Order>4</Order>
                    <Path>cmd /c reg add HKLM\SYSTEM\Setup\LabConfig /v BypassStorageCheck /t REG_DWORD /d 1 /f</Path>
                </RunSynchronousCommand>
                <RunSynchronousCommand wcm:action="add">
                    <Order>5</Order>
                    <Path>cmd /c reg add HKLM\SYSTEM\Setup\LabConfig /v BypassCPUCheck /t REG_DWORD /d 1 /f</Path>
                </RunSynchronousCommand>
                <RunSynchronousCommand wcm:action="add">
                    <Order>6</Order>
                    <Path>cmd /c reg add HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\OOBE /v BypassNRO /t REG_DWORD /d 1 /f</Path>
                </RunSynchronousCommand>
            </RunSynchronous>
            <UserData>
                <AcceptEula>true</AcceptEula>
            </UserData>
        </component>
    </settings>
</unattend>
```

Build the ISO manually if needed:
```bash
./create_autounattend_iso.sh
```

### Step 2: Creating the Dynamic 64GB QCOW2 Hard Disk
```bash
./create_qcow2_disk.sh windows11_portable.qcow2 64G
```

### Step 3: Windows 11 Automated Setup Flow
1. Boot QEMU VM.
2. Windows Setup automatically loads `autounattend.xml` from secondary CD-ROM.
3. Select Language & Edition (e.g. Windows 11 Pro).
4. Unallocated 64.0 GB Disk 0 will display without hardware warnings.
5. Confirm installation onto Disk 0.
6. Installation completes file expansion (100%), reboots off disk, completes first-boot initialization, and enters OOBE.
7. In OOBE network screen, select **"I don't have internet"** (`Нямам интернет`) to create a local user account.

---

## 🧪 Isolated Environment Verification Suite

To verify that the project works out-of-the-box for open-source clients on a clean machine:
```bash
./test_isolated_environment.sh
```

Expected Output:
```text
==========================================================
      OPEN-SOURCE AUTOMATED ENVIRONMENT VERIFICATION     
==========================================================
[TEST 1/5] Validating autounattend.xml syntax...
  -> [PASSED] autounattend.xml contains all 6 required bypass directives.
[TEST 2/5] Testing ISO build script in isolated environment...
  -> [PASSED] Generated autounattend.iso (921600 bytes).
[TEST 3/5] Testing QCOW2 dynamic disk generation...
  -> [PASSED] Virtual disk generated: file format: qcow2
[TEST 4/5] Checking QEMU executable binary...
  -> [PASSED] Found QEMU binary: QEMU emulator version 11.0.3
[TEST 5/5] Checking launcher scripts permissions and syntax...
  -> [PASSED] Shell script syntax checks clean.
==========================================================
  [SUCCESS] All isolated environment tests PASSED!        
==========================================================
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
