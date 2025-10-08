#!/usr/bin/env python3
# script by airaacheisyaa
# instagram: @syaaikoo
# dilarang keras menyalahgunakan, segala resiko ditanggung sendiri ya kocak

import os
import subprocess
import textwrap
import sys
import pwd
import grp

# utility
def log(msg, status="INFO"):
    colors = {
        "INFO": "\033[94m[INFO]\033[0m",
        "OK": "\033[92m[OK]\033[0m",
        "WARN": "\033[93m[WARN]\033[0m",
        "ERROR": "\033[91m[ERROR]\033[0m"
    }
    print("{} {}".format(colors.get(status, "[?]"), msg))


def run_cmd(cmd, check=True, capture=False, as_user=None):
    # cmd: list
    if as_user and os.geteuid() == 0 and as_user != 'root':
        cmd = ['sudo', '-u', as_user] + cmd
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

# input
CRD_SSH_Code = input("masukin google crd tadi yang kamu salin : ").strip()
Pin = input("masukin pin minimal 6 digit (default 123456): ").strip() or "123456"

if len(Pin) < 6:
    log("pin minimal 6 digit astagfirullah!", "ERROR")
    sys.exit(1)

if os.geteuid() != 0:
    log("si kocakk udah dibilangin jalanin nih script pakai sudo!", "ERROR")
    sys.exit(1)

os.environ["DEBIAN_FRONTEND"] = "noninteractive"


SUDO_USER = os.environ.get('SUDO_USER') or None
if not SUDO_USER:
    for uname in os.listdir('/home'):
        if uname not in ('root',):
            SUDO_USER = uname
            break
if not SUDO_USER:
    SUDO_USER = 'nobody'

# ambil uid user 
def uid_gid_of(user):
    try:
        pw = pwd.getpwnam(user)
        return pw.pw_uid, pw.pw_gid
    except KeyError:
        return None, None

# ---------------------------------------------------------------------
# fungsi untuk menimpa ~/.bashrc user dengan konten yang diberikan
# ---------------------------------------------------------------------
def write_bashrc_for(user, content):
    """
    Tulis content ke ~user/.bashrc dan set ownership & permission.
    Returns True on success, False on failure.
    """
    uid, gid = uid_gid_of(user)
    if uid is None:
        log("user {} tidak ditemukan, lewati penulisan .bashrc".format(user), "WARN")
        return False
    try:
        home_dir = pwd.getpwnam(user).pw_dir
    except Exception as e:
        log("gagal dapatkan home dir untuk {}: {}".format(user, e), "ERROR")
        return False

    target_path = os.path.join(home_dir, ".bashrc")
    try:
        # gunakan textwrap.dedent untuk membersihkan indentation yang tidak perlu
        with open(target_path, "w", newline="\n") as f:
            f.write(textwrap.dedent(content))
        # chown file supaya user punya file tersebut
        try:
            os.chown(target_path, uid, gid)
        except PermissionError:
            # jika gagal chown (jarang), beri peringatan
            log("gagal chown {} ke {}:{} (permission denied)".format(target_path, uid, gid), "WARN")
        os.chmod(target_path, 0o644)
        log("~{} /.bashrc berhasil ditulis: {}".format(user, target_path), "OK")
        return True
    except Exception as e:
        log("gagal tulis {}: {}".format(target_path, e), "ERROR")
        return False

# konten .bashrc yang diminta — gunakan raw string supaya backslashes tidak diinterpretasi
BASHRC_CONTENT = r"""
# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
HISTCONTROL=ignoreboth

# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
HISTSIZE=1000
HISTFILESIZE=2000

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will
# match all files and zero or more directories and subdirectories.
#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac

# uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt
#force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
        # We have color support; assume it's compliant with Ecma-48
        # (ISO/IEC-6429). (Lack of such support is extremely rare, and such
        # a case would tend to support setf rather than setaf.)
        color_prompt=yes
    else
        color_prompt=
    fi
fi

if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    #alias dir='dir --color=auto'
    #alias vdir='vdir --color=auto'

    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

# colored GCC warnings and errors
#export GCC_COLORS='error=01;31:warning=01;35:note=01:36:caret=01;32:locus=01:quote=01'

# some more ls aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi
# bash theme - partly inspired by https://github.com/ohmyzsh/ohmyzsh/blob/master/themes/robbyrussell.zsh-theme
__bash_prompt() {
    local userpart='`export XIT=$? \
        && [ ! -z "${GITHUB_USER:-}" ] && echo -n "\[\033[0;32m\]@${GITHUB_USER:-} " || echo -n "\[\033[0;32m\]\u " \
        && [ "$XIT" -ne "0" ] && echo -n "\[\033[1;31m\]➜" || echo -n "\[\033[0m\]➜"`'
    local gitbranch='`\
        if [ "$(git config --get devcontainers-theme.hide-status 2>/dev/null)" != 1 ] && [ "$(git config --get codespaces-theme.hide-status 2>/dev/null)" != 1 ]; then \
            export BRANCH="$(git --no-optional-locks symbolic-ref --short HEAD 2>/dev/null || git --no-optional-locks rev-parse --short HEAD 2>/dev/null)"; \
            if [ "${BRANCH:-}" != "" ]; then \
                echo -n "\[\033[0;36m\](\[\033[1;31m\]${BRANCH:-}" \
                && if [ "$(git config --get devcontainers-theme.show-dirty 2>/dev/null)" = 1 ] && \
                    git --no-optional-locks ls-files --error-unmatch -m --directory --no-empty-directory -o --exclude-standard ":/*" > /dev/null 2>&1; then \
                        echo -n " \[\033[1;33m\]✗"; \
                fi \
                && echo -n "\[\033[0;36m\]) "; \
            fi; \
        fi`'
    local lightblue='\[\033[1;34m\]'
    local removecolor='\[\033[0m\]'
    PS1="${userpart} ${lightblue}\w ${gitbranch}${removecolor}\$ "
    unset -f __bash_prompt
}
__bash_prompt
export PROMPT_DIRTRIM=4

# Check if the terminal is xterm
if [[ "$TERM" == "xterm" ]]; then
    # Function to set the terminal title to the current command
    preexec() {
        local cmd="${BASH_COMMAND}"
        echo -ne "\033]0;${USER}@${HOSTNAME}: ${cmd}\007"
    }

    # Function to reset the terminal title to the shell type after the command is executed
    precmd() {
        echo -ne "\033]0;${USER}@${HOSTNAME}: ${SHELL}\007"
    }

    # Trap DEBUG signal to call preexec before each command
    trap 'preexec' DEBUG

    # Append to PROMPT_COMMAND to call precmd before displaying the prompt
    PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND; }precmd"
fi
PS1='\[\e[1;32m\]\u@\h\[\e[0m\]:\[\e[1;34m\]\w\[\e[0m\] $ '
PS1='airaacheisyaa@ubuntu:\w $ '
PS1='\[\e[0;32m\]airaacheisyaa@ubuntu\[\e[0m\]:\[\e[0;34m\]\w\[\e[0m\] $ '
"""

# ---------------------------------------------------------------------
# NOTE: fungsi konfigurasi audio (fifo / pipe-sink) dihilangkan sesuai permintaan.
# namun paket audio penting akan tetap di-install supaya sound stack lengkap.
# ---------------------------------------------------------------------

# main class
class CRDRootKDE:
    def __init__(self):
        self.install_requirements()
        self.install_crd()
        self.install_kde_full_with_audio()
        self.ensure_run_user_for_root()
        self.configure_crd_session()
        # tulis .bashrc untuk SUDO_USER dan root
        write_bashrc_for(SUDO_USER, BASHRC_CONTENT)
        write_bashrc_for("root", BASHRC_CONTENT)
        self.finish()

    @staticmethod
    def install_requirements():
        log("update repository & install dependency dasar...")
        run_cmd(["apt", "update", "-y"])
        # paket util dasar
        run_cmd(["apt", "install", "-y", "wget", "curl", "sudo", "lsb-release"], check=False)
        log("dependency dasar terpasang", "OK")

    @staticmethod
    def install_crd():
        log("install chrome remote desktop...")
        run_cmd(["wget", "-q", "https://dl.google.com/linux/direct/chrome-remote-desktop_current_amd64.deb"])
        subprocess.run(["dpkg", "--install", "chrome-remote-desktop_current_amd64.deb"], check=False)
        run_cmd(["apt", "install", "-y", "--fix-broken"]) 
        log("chrome remote desktop udah terpasang", "OK")

    @staticmethod
    def install_kde_full_with_audio():
        log("install kde plasma full dan paket audio lengkap (akan memakan banyak ruang & waktu)...")
        # paket KDE full
        kde_pkgs = ["kde-plasma-full", "dbus-x11", "dbus-user-session"]
        # paket audio penting / umum: pulseaudio, pipewire (optional), alsa utils, pavucontrol, libs
        audio_pkgs = [
            "pulseaudio", "pulseaudio-utils", "pavucontrol",
            "alsa-utils", "alsa-base", "alsa-oss", "libasound2", "libasound2-plugins",
            "libpulse0", "pipewire", "pipewire-pulse"
        ]
        # gabungkan
        pkgs = kde_pkgs + audio_pkgs
        # jalankan apt install sekali supaya lebih efisien
        cmd = ["apt", "install", "-y"] + pkgs
        run_cmd(cmd, check=False)
        log("instalasi KDE full + paket audio sudah dijalankan (cek output apt untuk status).", "OK")
        log("Catatan: bila ada paket yang ditahan/konflik, jalankan 'apt update' lalu 'apt install -y kde-plasma-full' manual.", "WARN")

    @staticmethod
    def ensure_run_user_for_root():
        run_user_dir = "/run/user/0"
        if not os.path.exists(run_user_dir):
            os.makedirs(run_user_dir, exist_ok=True)
            os.chown(run_user_dir, 0, 0)
            os.chmod(run_user_dir, 0o700)
            log("folder /run/user/0 dibuat untuk session user", "OK")
        else:
            log("/run/user/0 udah ada", "INFO")

    @staticmethod
    def configure_crd_session():
        log("menulis /etc/chrome-remote-desktop-session (kde user session)...")
        session_script = textwrap.dedent("""\
        #!/bin/bash
        export XDG_RUNTIME_DIR=/run/user/0
        if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
          eval $(dbus-launch --sh-syntax --exit-with-session)
        fi
        # default session untuk KDE Plasma X11
        exec /usr/bin/startplasma-x11
        """)
        with open('/etc/chrome-remote-desktop-session', 'w') as f:
            f.write(session_script)
        os.chmod('/etc/chrome-remote-desktop-session', 0o755)
        log("session kde user ditulis", "OK")

    @staticmethod
    def finish():
        log("restart service dbus & chrome-remote-desktop...")
        os.system("systemctl daemon-reload || true")
        os.system("service dbus restart || true")
        os.system("service chrome-remote-desktop restart || true")

        if CRD_SSH_Code:
            log("jalankan host-setup chrome remote desktop...")
            # root akses
            if SUDO_USER and SUDO_USER != 'nobody':
                os.system("sudo -u {} {} --pin={}".format(SUDO_USER, CRD_SSH_Code, Pin))
            else:
                os.system("{} --pin={}".format(CRD_SSH_Code, Pin))
        else:
            log("auth code CRD gak ada, dilewati", "WARN")

        print("\n\033[92m✅ RDP KDE Plasma (full) siap diakses via Chrome Remote Desktop!\033[0m")
        print("CATATAN: kalau CRD gk muncul, tunggu 1-5 menit karna lagi booting.")
        print("kalo tetap gak muncul, ketikin: sudo service chrome-remote-desktop restart")

# eksekusi
if __name__ == "__main__":
    CRDRootKDE()
