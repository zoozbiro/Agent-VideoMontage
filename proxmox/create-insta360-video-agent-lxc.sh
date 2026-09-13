#!/usr/bin/env bash
# ============================================================
# Insta360 Video Agent - Proxmox LXC Creator
# Proxmox VE 9.x / Debian 13
#
# Interactive creator inspired by Proxmox Community Scripts.
# Creates a dedicated unprivileged LXC and optionally passes
# through Intel renderD128 and an already-mounted NAS directory.
# This script never modifies or deletes existing CTs.
# ============================================================
set -Eeuo pipefail

APP_NAME="Insta360 Video Agent"
DEFAULT_HOSTNAME="video-agent"
DEFAULT_RAM=8192
DEFAULT_SWAP=2048
DEFAULT_DISK=32
DEFAULT_CORES=4
DEFAULT_BRIDGE="vmbr0"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
die(){ echo -e "${RED}ERREUR:${NC} $*" >&2; exit 1; }
info(){ echo -e "${BLUE}INFO:${NC} $*"; }
ok(){ echo -e "${GREEN}OK:${NC} $*"; }
warn(){ echo -e "${YELLOW}ATTENTION:${NC} $*"; }

require_root(){
  [[ $EUID -eq 0 ]] || die "Lancez ce script depuis le shell Proxmox en root."
  for cmd in pct pvesm pvesh pveam; do command -v "$cmd" >/dev/null || die "Commande $cmd introuvable."; done
}

get_next_id(){
  local id
  id="$(pvesh get /cluster/nextid 2>/dev/null || true)"
  [[ $id =~ ^[0-9]+$ ]] || id=200
  echo "$id"
}

choose_ctid(){
  local suggested="$(get_next_id)"
  while :; do
    read -r -p "CT ID [$suggested] : " CTID
    CTID="${CTID:-$suggested}"
    [[ $CTID =~ ^[0-9]+$ ]] || { warn "Le CT ID doit être numérique."; continue; }
    pct status "$CTID" >/dev/null 2>&1 && { warn "Le CT $CTID existe déjà."; continue; }
    break
  done
}

choose_root_storage(){
  mapfile -t STORAGES < <(pvesm status --content rootdir 2>/dev/null | awk 'NR>1 && $1!="" && $3=="active" {print $1}')
  ((${#STORAGES[@]})) || die "Aucun stockage actif compatible rootdir."
  echo; echo "=== Stockage du disque du LXC ==="; pvesm status --content rootdir 2>/dev/null || true; echo
  local i=1; for s in "${STORAGES[@]}"; do echo "  $i) $s"; ((i++)); done
  while :; do
    read -r -p "Choisir le stockage rootfs [1-${#STORAGES[@]}] : " n
    [[ $n =~ ^[0-9]+$ ]] && ((n>=1 && n<=${#STORAGES[@]})) && break
    warn "Choix invalide."
  done
  ROOT_STORAGE="${STORAGES[$((n-1))]}"
}

choose_template_storage(){
  mapfile -t STORAGES < <(pvesm status --content vztmpl 2>/dev/null | awk 'NR>1 && $1!="" && $3=="active" {print $1}')
  ((${#STORAGES[@]})) || die "Aucun stockage actif avec contenu vztmpl."
  echo; echo "=== Stockage du template Debian ==="; pvesm status --content vztmpl 2>/dev/null || true; echo
  local i=1; for s in "${STORAGES[@]}"; do echo "  $i) $s"; ((i++)); done
  while :; do
    read -r -p "Choisir le stockage template [1-${#STORAGES[@]}] : " n
    [[ $n =~ ^[0-9]+$ ]] && ((n>=1 && n<=${#STORAGES[@]})) && break
    warn "Choix invalide."
  done
  TEMPLATE_STORAGE="${STORAGES[$((n-1))]}"
}

get_debian_template(){
  info "Recherche du dernier template Debian 13 amd64..."
  mapfile -t TEMPLATES < <(pveam available --section system 2>/dev/null | awk '$2 ~ /^debian-13-standard_.*_amd64\.tar\.(gz|xz|zst)$/ {print $2}' | sort -V)
  ((${#TEMPLATES[@]})) || die "Aucun template Debian 13 amd64 trouvé via pveam."
  TEMPLATE_NAME="${TEMPLATES[-1]}"
  TEMPLATE_PATH="${TEMPLATE_STORAGE}:vztmpl/${TEMPLATE_NAME}"
  if pveam list "$TEMPLATE_STORAGE" 2>/dev/null | grep -Fq "$TEMPLATE_NAME"; then
    ok "Template déjà présent : $TEMPLATE_NAME"; return
  fi
  info "Téléchargement : $TEMPLATE_NAME"
  pveam download "$TEMPLATE_STORAGE" "$TEMPLATE_NAME"
  ok "Template téléchargé."
}

ask_resources(){
  echo; echo "=== Ressources ==="
  read -r -p "CPU / cores [$DEFAULT_CORES] : " CORES; CORES="${CORES:-$DEFAULT_CORES}"; [[ $CORES =~ ^[0-9]+$ ]] || CORES=$DEFAULT_CORES
  read -r -p "RAM en MiB [$DEFAULT_RAM] : " RAM; RAM="${RAM:-$DEFAULT_RAM}"; [[ $RAM =~ ^[0-9]+$ ]] || RAM=$DEFAULT_RAM
  read -r -p "SWAP en MiB [$DEFAULT_SWAP] : " SWAP; SWAP="${SWAP:-$DEFAULT_SWAP}"; [[ $SWAP =~ ^[0-9]+$ ]] || SWAP=$DEFAULT_SWAP
  read -r -p "Taille rootfs en Go [$DEFAULT_DISK] : " DISK; DISK="${DISK:-$DEFAULT_DISK}"; [[ $DISK =~ ^[0-9]+$ ]] || DISK=$DEFAULT_DISK
}

ask_hostname(){ read -r -p "Hostname [$DEFAULT_HOSTNAME] : " HOSTNAME; HOSTNAME="${HOSTNAME:-$DEFAULT_HOSTNAME}"; }

ask_password(){
  echo; echo "=== Mot de passe root du LXC ==="
  while :; do
    read -r -s -p "Mot de passe : " PASSWORD; echo
    read -r -s -p "Confirmer : " PASSWORD2; echo
    [[ -n $PASSWORD ]] || { warn "Mot de passe vide."; continue; }
    [[ $PASSWORD == "$PASSWORD2" ]] && break
    warn "Les mots de passe ne correspondent pas."
  done
}

choose_network(){
  echo; echo "=== Réseau ==="; echo "1) DHCP"; echo "2) IP statique"
  read -r -p "Choix [1] : " NET_MODE; NET_MODE="${NET_MODE:-1}"
  read -r -p "Bridge [$DEFAULT_BRIDGE] : " BRIDGE_INPUT; BRIDGE="${BRIDGE_INPUT:-$DEFAULT_BRIDGE}"
  if [[ $NET_MODE == 2 ]]; then
    read -r -p "Adresse IPv4/CIDR (ex. 192.168.1.50/24) : " IPADDR
    read -r -p "Gateway IPv4 : " GATEWAY
    [[ -n $IPADDR && -n $GATEWAY ]] || die "IP et gateway obligatoires."
    NET_CONFIG="name=eth0,bridge=${BRIDGE},ip=${IPADDR},gw=${GATEWAY}"
  else
    NET_CONFIG="name=eth0,bridge=${BRIDGE},ip=dhcp"
  fi
}

ask_igpu(){
  IGPU_ENABLED=0
  if [[ -e /dev/dri/renderD128 ]]; then
    echo; echo "=== Intel iGPU ==="; echo "Détecté : /dev/dri/renderD128"
    read -r -p "Activer le passage de l'iGPU au LXC ? [O/n] : " answer; answer="${answer:-O}"
    [[ $answer =~ ^[OoYy]$ ]] && IGPU_ENABLED=1
  else
    warn "/dev/dri/renderD128 non trouvé. iGPU non configuré."
  fi
}

ask_bind_mount(){
  BIND_ENABLED=0; BIND_HOST=""; BIND_CT=""
  echo; echo "=== Dossier NAS optionnel ==="
  echo "Le chemin doit déjà être monté sur l'hôte Proxmox (NFS/SMB/etc.)."
  read -r -p "Chemin hôte à monter (vide = aucun) : " BIND_HOST
  [[ -z $BIND_HOST ]] && return
  [[ -d $BIND_HOST ]] || die "Le chemin n'existe pas : $BIND_HOST"
  case "$BIND_HOST" in /|/etc|/usr|/var|/bin|/sbin|/lib|/lib64|/boot|/proc|/sys|/dev) die "Chemin système refusé.";; esac
  read -r -p "Chemin dans le LXC [/mnt/video] : " BIND_CT; BIND_CT="${BIND_CT:-/mnt/video}"
  BIND_ENABLED=1
}

show_summary(){
  echo; echo "============================================================"; echo " RÉSUMÉ"; echo "============================================================"
  echo " CT ID          : $CTID"; echo " Hostname       : $HOSTNAME"; echo " Rootfs storage : $ROOT_STORAGE"; echo " Rootfs size    : ${DISK}G"
  echo " Template       : $TEMPLATE_STORAGE"; echo " CPU            : $CORES cores"; echo " RAM            : ${RAM} MiB"; echo " SWAP           : ${SWAP} MiB"
  echo " Réseau         : $NET_CONFIG"; echo " iGPU Intel     : $([[ $IGPU_ENABLED == 1 ]] && echo OUI || echo NON)"
  [[ $BIND_ENABLED == 1 ]] && { echo " Bind host      : $BIND_HOST"; echo " Bind LXC       : $BIND_CT"; } || echo " Bind NAS       : NON"
  echo "============================================================"; echo
}

create_container(){
  info "Création du LXC $CTID..."
  pct create "$CTID" "$TEMPLATE_PATH" \
    --hostname "$HOSTNAME" --ostype debian --arch amd64 --unprivileged 1 \
    --rootfs "${ROOT_STORAGE}:${DISK}" --cores "$CORES" --memory "$RAM" --swap "$SWAP" \
    --net0 "$NET_CONFIG" --features "nesting=1,keyctl=1" --onboot 1 --start 0 \
    --password "$PASSWORD" --tags "video-agent" \
    --description "Insta360 Video Agent - LXC dédié au montage vidéo automatisé"

  if [[ $IGPU_ENABLED == 1 ]]; then pct set "$CTID" -dev0 /dev/dri/renderD128,mode=0666; fi
  if [[ $BIND_ENABLED == 1 ]]; then pct set "$CTID" -mp0 "${BIND_HOST},mp=${BIND_CT},backup=0"; fi
  ok "LXC $CTID créé."
}

prepare_container(){
  info "Démarrage du LXC..."; pct start "$CTID"; sleep 5
  info "Installation des prérequis vidéo..."
  pct exec "$CTID" -- bash -lc 'export DEBIAN_FRONTEND=noninteractive; apt-get update && apt-get install -y --no-install-recommends ca-certificates curl git ffmpeg python3 python3-venv python3-pip python3-opencv vainfo pciutils nano htop'
  pct exec "$CTID" -- bash -lc 'mkdir -p /opt/video-agent/{app,config,logs,work,tmp}; chmod 755 /opt/video-agent; echo "Video Agent workspace ready." > /opt/video-agent/README.txt'
  if [[ $IGPU_ENABLED == 1 ]]; then
    echo; info "Test VA-API..."
    pct exec "$CTID" -- bash -lc 'vainfo --display drm --device /dev/dri/renderD128 2>&1 || true; echo; ls -la /dev/dri/ 2>/dev/null || true'
  fi
  ok "Prérequis installés."
}

main(){
  require_root
  echo; echo "============================================================"; echo " $APP_NAME"; echo "============================================================"
  warn "Le script crée un nouveau LXC et ne supprime aucun CT existant."; echo
  choose_ctid; choose_root_storage; choose_template_storage; get_debian_template
  ask_resources; ask_hostname; ask_password; choose_network; ask_igpu; ask_bind_mount; show_summary
  read -r -p "Créer le LXC avec ces paramètres ? [o/N] : " CONFIRM
  [[ $CONFIRM =~ ^[OoYy]$ ]] || { echo "Annulé."; exit 0; }
  create_container
  read -r -p "Démarrer et installer les prérequis vidéo maintenant ? [O/n] : " PREPARE; PREPARE="${PREPARE:-O}"
  [[ $PREPARE =~ ^[OoYy]$ ]] && prepare_container
  local ip="$(pct exec "$CTID" -- hostname -I 2>/dev/null | awk '{print $1}' || true)"
  echo; echo "============================================================"; echo -e "${GREEN} LXC VIDEO AGENT PRÊT ${NC}"; echo "============================================================"
  echo "CT ID       : $CTID"; echo "Hostname    : $HOSTNAME"; echo "IP détectée : ${ip:-non détectée}"; echo "Console     : pct enter $CTID"; echo "Workspace   : /opt/video-agent"
  echo "============================================================"
}

main "$@"
