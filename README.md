# Agent Video Montage

Agent local de montage vidéo automatisé pour rushs Insta360 X5, pensé pour tourner à faible coût sur un mini-serveur Proxmox et utiliser le NAS comme stockage source/archive.

## Objectif

Transformer progressivement un dossier de rushs Insta360 en exports verticaux prêts pour les réseaux sociaux :

```text
Insta360 X5
    ↓
Synology / rushs originaux
    ↓
Analyse + proxies
    ↓
Sélection des passages
    ↓
Décision de montage
    ↓
Reframing 360°
    ↓
FFmpeg / audio / sous-titres
    ↓
Export 9:16
    ↓
Synology / exports
```

## Structure

```text
Agent-VideoMontage/
├── agent/                 # Cerveau du montage : orchestration et décisions
│   ├── README.md
│   └── config.example.yaml
├── ffmpeg/                # Moteur vidéo : commandes, profils et presets
│   ├── README.md
│   └── presets/
├── scripts/               # Utilitaires d'exploitation
│   └── README.md
├── config/                # Configuration projet/documentation de configuration
│   ├── README.md
│   └── project.example.yaml
├── proxmox/               # Installation de l'environnement LXC
│   ├── create-insta360-video-agent-lxc.sh
│   └── README.md
├── docker/                # Réservé aux composants qui gagneront à être conteneurisés
│   └── README.md
└── README.md
```

## Déploiement Proxmox

Le créateur LXC est interactif et inspiré du fonctionnement des Proxmox Community Scripts : choix du CT ID, stockage rootfs, stockage du template, CPU/RAM, réseau, iGPU Intel et montage NAS optionnel.

Commande directe depuis le shell Proxmox root :

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/zoozbiro/Agent-VideoMontage/main/proxmox/create-insta360-video-agent-lxc.sh)"
```

Le script crée uniquement un nouveau LXC et ne supprime aucun conteneur existant.

## Architecture de stockage recommandée

- **Synology** : originaux Insta360 et exports durables.
- **LXC Proxmox** : code, configuration, logs et cache temporaire.
- **Montage NAS** : de préférence NFS monté sur l'hôte Proxmox puis bind-mounté dans le LXC.
- **Disques externes** : sauvegardes indépendantes.

## Matériel cible

Le projet est conçu pour rester raisonnable sur un CPU 4 cœurs ancien avec 16 Go de RAM. Il privilégie FFmpeg, OpenCV et des analyses légères plutôt que de gros modèles vidéo locaux.

L'iGPU Intel peut être exposé au LXC si `/dev/dri/renderD128` est disponible, puis validé avec `vainfo`.

## Principes du projet

1. Ne jamais toucher aux rushs originaux.
2. Travailler avec des proxies quand l'analyse le permet.
3. Séparer le moteur vidéo du cerveau de décision.
4. Garder toutes les opérations reproductibles par scripts/configuration.
5. Exporter vers un dossier distinct des sources.
6. Ajouter les fonctions progressivement : détection de scènes → sélection → reframing → tracking → rythme → sous-titres → profils sociaux.

## État

**Phase 1 — infrastructure LXC** : en place.

**Phase 2 — moteur de pipeline vidéo** : à construire.

**Phase 3 — agent de sélection et montage** : à construire.

**Phase 4 — automatisation complète et profils de rendu** : à construire.
