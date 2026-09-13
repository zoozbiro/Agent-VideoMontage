# Agent-VideoMontage — Proxmox

Création et préparation du conteneur Proxmox destiné à l'agent de montage vidéo automatique pour les rushs Insta360 X5.

## Matériel cible

Configuration initiale prévue pour :

- Intel Core i5-6600 — 4 cœurs / 4 threads
- 16 Go de RAM
- Intel HD Graphics 530
- Proxmox VE 9.x
- Synology DS214play comme stockage des rushs
- Environ 800 Go libres sur le Synology au moment de la conception

Le serveur Proxmox sert au **calcul et au traitement vidéo**. Le Synology sert principalement au **stockage des originaux et des exports**.

## Script

`create-insta360-video-agent-lxc.sh` crée un LXC Debian 13 dédié.

Il permet de choisir interactivement :

- CT ID
- stockage Proxmox du rootfs
- stockage du template Debian
- nombre de CPU
- RAM
- swap
- taille du rootfs
- hostname
- bridge réseau
- DHCP ou IP statique
- passage de l'iGPU Intel `/dev/dri/renderD128` si détecté
- bind mount optionnel d'un dossier déjà monté sur l'hôte Proxmox

Le script ne supprime aucun conteneur existant.

## Configuration recommandée

Pour le serveur actuel :

| Paramètre | Valeur recommandée |
|---|---:|
| CPU | 4 cores |
| RAM | 8192 MiB |
| Swap | 2048 MiB |
| Rootfs | 32 Go |
| OS | Debian 13 amd64 |
| LXC | Unprivileged |
| Features | `nesting=1,keyctl=1` |

Les valeurs proposées par défaut sont déjà celles-ci.

## Exécution

Depuis le **Shell du nœud Proxmox**, en root :

```bash
bash create-insta360-video-agent-lxc.sh
```

Le script télécharge automatiquement le dernier template Debian 13 standard amd64 disponible via `pveam` s'il n'est pas déjà présent.

## Stockage Synology

Deux architectures sont possibles.

### Recommandée

Garder les gros fichiers vidéo sur le Synology et utiliser le disque du LXC pour le système et les fichiers temporaires :

```text
Synology
└── video/
    ├── 01_RUSHS/
    │   └── X5/
    └── 03_EXPORT/

Proxmox LXC
└── /opt/video-agent/
    ├── app/
    ├── config/
    ├── logs/
    ├── work/
    └── tmp/
```

Le traitement pourra ensuite utiliser un partage NFS du Synology. Pour un bind mount, le partage doit être monté sur l'hôte Proxmox puis le chemin hôte peut être fourni au script.

Exemple :

```text
Hôte Proxmox : /mnt/bindmounts/video
LXC          : /mnt/video
```

Le script crée alors un `mp0` avec sauvegarde désactivée (`backup=0`) pour ce partage de données.

### Rootfs directement sur le Synology

Si le Synology est déclaré comme stockage Proxmox compatible `rootdir`, il peut être sélectionné comme stockage du rootfs pendant l'installation. Pour les performances vidéo, il reste préférable de garder le cache et le travail intensif sur un stockage local suffisamment rapide lorsque c'est possible.

## Intel HD 530 / VA-API

Si Proxmox expose :

```text
/dev/dri/renderD128
```

le script propose de le transmettre au LXC. Le conteneur installe `vainfo` et effectue un test VA-API au démarrage.

Cela prépare l'utilisation de l'accélération matérielle Intel par FFmpeg lorsque le codec et l'opération sont compatibles.

## Logiciels installés

Le script installe une base légère :

- FFmpeg
- Python 3
- Python venv / pip
- OpenCV Python
- VA-API / `vainfo`
- Git
- curl
- pciutils
- nano
- htop

Le moteur d'agent, l'analyse des rushs, le reframing 360°, la sélection intelligente et l'interface web seront ajoutés dans les étapes suivantes du projet.

## Philosophie du projet

Le serveur n'a pas vocation à faire tourner un gros modèle vidéo en permanence. L'architecture visée est :

```text
Insta360 X5
    ↓
Rushs originaux sur Synology
    ↓
Analyse/proxies
    ↓
Sélection des passages intéressants
    ↓
Décision de montage par l'agent
    ↓
Reframing 360°
    ↓
Montage FFmpeg
    ↓
Export 9:16
    ↓
Synology / 03_EXPORT
```

L'objectif de la première version est de transformer automatiquement des rushs X5 en un **Reel vertical 9:16**, avant d'ajouter progressivement la sélection IA, le cadrage automatique, la musique, les sous-titres et les différents styles de montage.

## Sécurité

Le script :

- ne supprime pas de CT ;
- vérifie que le CT ID choisi n'existe pas ;
- ne monte pas automatiquement un chemin système dangereux ;
- ne modifie pas les VM/LXC existants ;
- garde les rushs originaux hors du rootfs du conteneur.

Avant une utilisation en production, vérifier les sauvegardes du Synology et de la configuration Proxmox.
