#!/bin/bash


#------------------------------------------------------------------------------
# INTRODUCTION
#------------------------------------------------------------------------------

# This script installs cbox-bot, its requirements, system updates, a systemd
# service unit, and the following scripts for system administration:
#
#   /usr/local/sbin/upgrade.sh
#   /usr/local/sbin/status.sh

# The installer targets Debian 9 Stretch running in a Proxmox LXC container.
# Don't forget to configure it


#------------------------------------------------------------------------------
# PROXMOX
#------------------------------------------------------------------------------

# After setting up a new container, use pct on the proxmox host to set the
# container to start at boot, and to set resource limits. Overkill example:
#
#   pct set ${vmid} --onboot 1 --cores 4 --cpulimit 4 --memory 4096

# To take snapshots:
#
#   pct shutdown ${vmid}
#   pct snapshot ${vmid} ${snapshot_name}
#   pct start ${vmid}

# To rollback:
#
#   pct shutdown ${vmid}
#   pct rollback ${vmid} ${snapshot_name}
#   pct start ${vmid}


#------------------------------------------------------------------------------
# DEPLOYMENT
#------------------------------------------------------------------------------

# To deploy this script:
#
#  # from your workstation:
#  scp install.sh root@target_host:/usr/local/sbin/install.sh
#  ssh root@target_host
#
#  # in target_host:
#  chmod 700 /usr/local/sbin/install.sh
#  install.sh


#------------------------------------------------------------------------------
# VARIABLES
#------------------------------------------------------------------------------

# Config
LANG="en_US.UTF-8"
TZ=America/Los_Angeles

# Debian
DEB_BASE_TARGET=stretch
DEB_COMPONENTS="main contrib non-free"
DEB_MIRROR=http://ftp.us.debian.org/debian
DEB_PKG_EXTRA="cron-apt curl htop sudo tree vim wget"
DEB_PKG_REQUIRED="git python2-dev virtualenv"

# Project
PROJECT_BRANCH=master
PROJECT_DIR=/opt/proj/cbox-bot
PROJECT_ENV=/opt/venv/cbox-bot
PROJECT_REPO=https://github.com/Golen87/cbox-bot.git
PROJECT_USER=chu

# Scripts
UPGRADE_SCRIPT=/usr/local/sbin/upgrade.sh
UPGRADE_LOG_COLOR=3
STATUS_SCRIPT=/usr/local/sbin/status.sh
STATUS_LOG_COLOR=6

# Logging
LOG_PREFIX="[install.sh]"
LOG_COLOR=0  # 0: white, 1: red, 2: green, 3: yellow, 4: blue, 5: purple, 6: cyan, ...
log() { tput setaf ${LOG_COLOR}; echo ${LOG_PREFIX} $@; tput sgr0;}


#------------------------------------------------------------------------------
# EARLY OUTS
#------------------------------------------------------------------------------

if [ 0 -ne `id -u` ]; then
    LOG_COLOR=1 log "This script requires root privileges to run, exiting."
    exit 1
fi

log "Welcome!"
echo "This script will install stuff to /opt, set it up to run with the new user '${PROJECT_USER}',"
echo "and give the root user an upgrade script here: ${UPGRADE_SCRIPT}"
read -p "It's mostly automated, but be on the lookout for prompts. Ready? [Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ -n $REPLY ]]; then
    exit 1
fi


#------------------------------------------------------------------------------
# SYSTEM SETUP
#------------------------------------------------------------------------------

log "Setting system language to ${LANG}"
grep ${LANG} /usr/share/i18n/SUPPORTED >> /etc/locale.gen
dpkg-reconfigure --frontend=noninteractive locales
update-locale LANG=${LANG}

log "Setting system timezone to ${TZ}"
echo ${TZ} > /etc/timezone
rm /etc/localtime
dpkg-reconfigure --frontend=noninteractive tzdata

log "Setting APT target to Debian ${DEB_BASE_TARGET} (${DEB_COMPONENTS})"
mv /etc/apt/sources.list /etc/apt/sources.list.old
cat <<EOF > /etc/apt/sources.list
deb ${DEB_MIRROR} ${DEB_BASE_TARGET} ${DEB_COMPONENTS}
#deb ${DEB_MIRROR} ${DEB_BASE_TARGET}-backports ${DEB_COMPONENTS}
deb ${DEB_MIRROR} ${DEB_BASE_TARGET}-updates ${DEB_COMPONENTS}
deb http://security.debian.org ${DEB_BASE_TARGET}/updates ${DEB_COMPONENTS}
EOF

log "Upgrading Debian"
apt update
apt full-upgrade --yes
apt autoremove --yes

log "Installing packages"
apt install --yes ${DEB_PKG_REQUIRED} ${DEB_PKG_EXTRA}


#------------------------------------------------------------------------------
# PROJECT SETUP
#------------------------------------------------------------------------------

log "Cloning project and submodules"
git clone ${PROJECT_REPO} ${PROJECT_DIR} --branch ${PROJECT_BRANCH}

log "Creating python virtual environment"
virtualenv -p /usr/bin/python2 ${PROJECT_ENV}

log "Adding user ${PROJECT_USER}"
useradd -s /bin/bash -d ${PROJECT_DIR} ${PROJECT_USER}


#------------------------------------------------------------------------------
# SERVICES
#------------------------------------------------------------------------------

log "Installing systemd unit: cbox-bot.service"
cat << EOF > /etc/systemd/system/cbox-bot.service
[Unit]
Description=cbox-bot

[Service]
User=${PROJECT_USER}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_ENV}/bin/python src/bot.py

[Install]
WantedBy=multi-user.target
EOF

log "Enabling service"
systemctl daemon-reload
systemctl enable cbox-bot.service


#------------------------------------------------------------------------------
# SCRIPTS
#------------------------------------------------------------------------------

log "Installing $(basename ${STATUS_SCRIPT})"
cat <<EOF > ${STATUS_SCRIPT}
#!/bin/bash
systemctl --no-pager status cbox-bot.service
EOF
chmod 700 ${STATUS_SCRIPT}

log "Installing $(basename ${UPGRADE_SCRIPT})"
cat <<EOF > ${UPGRADE_SCRIPT}
#!/bin/bash

PROJECT_DIR=${PROJECT_DIR}
PROJECT_ENV=${PROJECT_ENV}
PROJECT_REMOTE=origin
PROJECT_BRANCH=${PROJECT_BRANCH}
git() { /usr/bin/git -C \${PROJECT_DIR} \$@; }

LOG_PREFIX="[$(basename ${UPGRADE_SCRIPT})]"
LOG_COLOR=${UPGRADE_LOG_COLOR}  # 0: white, 1: red, 2: green, 3: yellow, 4: blue, 5: purple, 6: cyan, ...
log() { tput setaf \${LOG_COLOR}; echo \${LOG_PREFIX} \$@; tput sgr0;}

if [ 0 -ne `id -u` ]; then
    log "This script requires root privileges to run, exiting."
    exit 1
fi

log "Upgrading Debian"
apt update
apt full-upgrade --yes
apt autoremove --yes

log "Activating virtualenv"
source \${PROJECT_ENV}/bin/activate

log "Pulling changes from \${PROJECT_REMOTE}/\${PROJECT_BRANCH}"
git pull \${PROJECT_REMOTE}/\${PROJECT_BRANCH}

log "Syncing pip requirements"
pip install -r \${PROJECT_DIR}/requirements.txt

log "Restarting cbox-bot.service"
systemctl restart cbox-bot.service

log "Running $(basename ${STATUS_SCRIPT})"
${STATUS_SCRIPT}
log 'Done!'
EOF
chmod 700 ${UPGRADE_SCRIPT}

log "Running $(basename ${UPGRADE_SCRIPT})"
${UPGRADE_SCRIPT}
log 'Done!'
