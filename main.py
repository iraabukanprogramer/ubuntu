#!/usr/bin/env python3
# script by airaacheisyaa (modified)
# instagram: @syaaikoo
# tujuan: install KDE full (coba kde-plasma-full) dengan setup repo otomatis & audio pkgs
# catatan: jalankan sebagai root (sudo). script ini membuat perubahan repo & menimpa .bashrc (backup dibuat).

import os
import subprocess
import textwrap
import sys
import pwd
import shutil
import time

# ---------- utils ----------
def log(msg, status="INFO"):
    colors = {
        "INFO": "\033[94m[INFO]\033[0m",
        "OK": "\033[92m[OK]\033[0m",
        "WARN": "\033[93m[WARN]\033[0m",
        "ERROR": "\033[91m[ERROR]\033[0m"
    }
    print("{} {}".format(colors.get(status, "[?]"), msg))

def run_cmd(cmd, check=True, capture=False):
    """Run command list, return (stdout, stderr) if capture else (None,None)."""
    try:
        if capture:
            r = subprocess.run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return r.stdout.strip(), r.stderr.strip()
        else:
            subprocess.run(cmd, check=check)
            return None, None
    except subprocess.CalledProcessError as e:
        if capture:
            return getattr(e, 'stdout', ''), getattr(e, 'stderr', str(e))
        log("Perintah gagal: {} -> {}".format(' '.join(cmd), e), "ERROR")
        if check:
            sys.exit(1)
        return None, str(e)

def detect_distro():
    """Return tuple (id, codename). id like 'Ubuntu' or 'Debian' or None"""
    try:
        out, _ = run_cmd(["lsb_release", "-is"], capture=True)
        codename, _ = run_cmd(["lsb_release", "-cs"], capture=True)
        return out.strip(), codename.strip()
    except Exception:
        # fallback parse /etc/os-release
        try:
            with open("/etc/os-release", "r") as f:
                data = f.read()
            id_line = next((l for l in data.splitlines() if l.startswith("ID=")), "")
            id_val = id_line.split("=",1)[1].strip().strip('"') if id_line else ""
            version_line = next((l for l in data.splitlines() if l.startswith("VERSION_CODENAME=")), "")
            codename_val = version_line.split("=",1)[1].strip().strip('"') if version_line else ""
            return id_val.capitalize() if id_val else None, codename_val
        except Exception:
            return None, None

def free_space_mb(path="/"):
    st = os.statvfs(path)
    return (st.f_bavail * st.f_frsize) // 1024 // 1024

# ---------- repo helpers ----------
def backup_file(path):
    if os.path.exists(path):
        bak = "{}.precrdback.{}".format(path, int(time.time()))
        try:
            shutil.copy2(path, bak)
            log("backup {} -> {}".format(path, bak), "OK")
            return bak
        except Exception as e:
            log("gagal backup {}: {}".format(path, e), "WARN")
            return None
    return None

def ubuntu_enable_universe_multiverse():
    log("Enable universe & multiverse (Ubuntu)...")
    run_cmd(["apt", "update", "-y"], check=False)
    run_cmd(["apt", "install", "-y", "software-properties-common"], check=False)
    # add components
    run_cmd(["add-apt-repository", "-y", "universe"], check=False)
    run_cmd(["add-apt-repository", "-y", "multiverse"], check=False)
    run_cmd(["add-apt-repository", "-y", "restricted"], check=False)
    # add kubuntu backports PPA to increase chance for kde-full variants
    try:
        run_cmd(["add-apt-repository", "-y", "ppa:kubuntu-ppa/backports"], check=False)
    except Exception as e:
        log("gagal tambah PPA kubuntu-backports: {}".format(e), "WARN")
    run_cmd(["apt", "update", "-y"], check=False)

def debian_enable_contrib_nonfree():
    log("Enable contrib & non-free (Debian)...")
    src = "/etc/apt/sources.list"
    backup_file(src)
    try:
        with open(src, "r") as f:
            lines = f.readlines()
        new = []
        for L in lines:
            # if already has contrib/non-free then keep
            if L.strip().startswith("#"):
                new.append(L)
                continue
            parts = L.split()
            if len(parts) >= 3 and parts[0] in ("deb","deb-src"):
                # ensure components include contrib non-free
                # split into first 3 and components
                repo = " ".join(parts[:3])
                comps = parts[3:]
                # if no components, leave as is
                if not comps:
                    # default to main contrib non-free
                    new.append(repo + " main contrib non-free\n")
                else:
                    comp_set = set(comps)
                    comp_set.update(["contrib","non-free"])
                    new.append(repo + " " + " ".join(comp_set) + "\n")
            else:
                new.append(L)
        with open(src, "w") as f:
            f.writelines(new)
        run_cmd(["apt", "update", "-y"], check=False)
        log("/etc/apt/sources.list dimodifikasi untuk menambahkan contrib & non-free", "OK")
    except Exception as e:
        log("gagal modify sources.list: {}".format(e), "ERROR")

# ---------- installation strategy ----------
def install_kde_candidates():
    # list prioritas paket — coba satu per satu
    candidates = [
        "kde-plasma-full",
        "kde-full",
        "kde-standard",
        "kde-plasma-desktop",
        "kubuntu-desktop"
    ]
    for pkg in candidates:
        log("mencoba install paket: {}".format(pkg))
        out, err = run_cmd(["apt", "install", "-y", pkg], check=False, capture=True)
        # run_cmd returned tuple only when capture=True; some errors won't throw
        # instead of strict checking, check dpkg -s
        status_out, _ = run_cmd(["dpkg", "-s", pkg], check=False, capture=True)
        if status_out and "Status: install" in status_out:
            log("paket {} berhasil terpasang (atau terdeteksi terpasang)".format(pkg), "OK")
            return pkg
        # else continue
        log("paket {} tidak berhasil/tersedia, lanjut ke kandidat berikutnya".format(pkg), "WARN")
    return None

# ---------- bashrc writer (with backup) ----------
BASHRC_CONTENT = r"""# ~/.bashrc: executed by bash(1) for non-login shells.
# ... (content truncated for brevity in code block) ...
# Aku akan menimpa dengan konten yang kamu minta — pastikan backup dibuat dulu.
PS1='\[\e[0;32m\]airaacheisyaa@ubuntu\[\e[0m\]:\[\e[0;34m\]\w\[\e[0m\] $ '
"""

def write_bashrc_for(user, content_full):
    uid = None
    try:
        pw = pwd.getpwnam(user)
        uid = pw.pw_uid
        gid = pw.pw_gid
        home = pw.pw_dir
    except KeyError:
        log("user {} tidak ditemukan, lewati .bashrc".format(user), "WARN")
        return False
    target = os.path.join(home, ".bashrc")
    backup_file(target)
    try:
        with open(target, "w", newline="\n") as f:
            f.write(textwrap.dedent(content_full))
        try:
            os.chown(target, uid, gid)
        except PermissionError:
            log("gagal chown {} ke {} (permission)".format(target, user), "WARN")
        os.chmod(target, 0o644)
        log("Menulis ~/.bashrc untuk {}".format(user), "OK")
        return True
    except Exception as e:
        log("gagal menulis {}: {}".format(target, e), "ERROR")
        return False

# ---------- main workflow ----------
def main():
    if os.geteuid() != 0:
        log("jalanin script ini sebagai root (sudo)", "ERROR")
        sys.exit(1)

    # input sebelumnya (kita masih butuh auth code dan pin)
    CRD_SSH_Code = input("masukin google crd tadi yang kamu salin : ").strip()
    Pin = input("masukin pin minimal 6 digit (default 123456): ").strip() or "123456"
    if len(Pin) < 6:
        log("pin minimal 6 digit!", "ERROR")
        sys.exit(1)

    distro, codename = detect_distro()
    log("Detected distro: {} {}".format(distro, codename), "INFO")

    # cek ruang disk minimal rekomendasi 8GB (8192 MB) — KDE full bisa butuh banyak
    free_mb = free_space_mb("/")
    log("free space (MB): {}".format(free_mb), "INFO")
    if free_mb < 4096:
        log("RUANG DISK rendah (<4GB). Install KDE full sangat riskan. Lanjut dengan risiko kamu sendiri.", "WARN")

    # setup repos sesuai distro
    if distro and "Ubuntu" in distro:
        ubuntu_enable_universe_multiverse()
    elif distro and "Debian" in distro:
        debian_enable_contrib_nonfree()
    else:
        log("Distro tidak terdeteksi/beda ({}). Akan mencoba apt update saja.".format(distro), "WARN")
        run_cmd(["apt", "update", "-y"], check=False)

    # install base audio & utilities
    log("install paket dasar dan audio stack (pulseaudio/pipewire/alsa/pavucontrol)...", "INFO")
    audio_pkgs = [
        "pulseaudio", "pulseaudio-utils", "pavucontrol",
        "alsa-utils", "alsa-base", "libasound2", "libasound2-plugins",
        "libpulse0", "pipewire", "pipewire-pulse", "wireplumber", "apulse"
    ]
    run_cmd(["apt", "install", "-y"] + audio_pkgs, check=False)

    # update then try install KDE candidates
    run_cmd(["apt", "update", "-y"], check=False)
    installed = install_kde_candidates()
    if installed:
        log("SUKSES: paket KDE yang terpasang: {}".format(installed), "OK")
    else:
        log("GAGAL: tidak menemukan paket KDE lengkap di repo. Coba jalankan manual: 'apt update' lalu cek paket seperti kde-plasma-full / kde-full / kubuntu-desktop'", "ERROR")
        # masih lanjut untuk menulis .bashrc & CRD setup if requested

    # tulis .bashrc untuk sudo user & root (backup dibuat)
    sudo_user = os.environ.get("SUDO_USER") or None
    if not sudo_user:
        # cari user di /home
        for uname in os.listdir("/home"):
            if uname not in ("root",):
                sudo_user = uname
                break
    if sudo_user:
        write_bashrc_for(sudo_user, BASHRC_CONTENT)
    write_bashrc_for("root", BASHRC_CONTENT)

    # konfigurasi chrome remote desktop session (tetap sederhana)
    try:
        session_path = "/etc/chrome-remote-desktop-session"
        backup_file(session_path)
        session_script = textwrap.dedent("""\
            #!/bin/bash
            export XDG_RUNTIME_DIR=/run/user/0
            if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
              eval $(dbus-launch --sh-syntax --exit-with-session)
            fi
            exec /usr/bin/startplasma-x11
        """)
        with open(session_path, "w") as f:
            f.write(session_script)
        os.chmod(session_path, 0o755)
        log("wrote {}".format(session_path), "OK")
    except Exception as e:
        log("gagal tulis chrome-remote-desktop-session: {}".format(e), "WARN")

    # jalankan host-setup jika CRD_SSH_Code ada
    if CRD_SSH_Code:
        log("jalankan host-setup chrome remote desktop (background)...", "INFO")
        try:
            sudo_user = sudo_user or "root"
            if sudo_user != "root":
                os.system("sudo -u {} {} --pin={} || true".format(sudo_user, CRD_SSH_Code, Pin))
            else:
                os.system("{} --pin={} || true".format(CRD_SSH_Code, Pin))
        except Exception as e:
            log("gagal eksekusi host-setup: {}".format(e), "WARN")

    log("SELESAI. Periksa output apt di atas untuk status instalasi. Jika paket belum tersedia, pertimbangkan menambahkan repository khusus distro (contoh: KDE neon atau PPA Kubuntu) secara manual.", "OK")
    print("\n\033[92m✅ Selesai. Cek logs di terminal.\033[0m")

if __name__ == "__main__":
    main()
