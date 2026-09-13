# FFmpeg

Couche d'exécution vidéo. Elle reçoit un plan de montage produit par `agent/` et applique les opérations de manière déterministe.

À terme :

- inspection des `.insv`/proxies `.lrv` ;
- génération de proxies ;
- découpe ;
- reframing 360° ;
- crop 9:16 ;
- vitesse ;
- mixage audio ;
- sous-titres ;
- encodage final ;
- validation du fichier exporté.

Les presets doivent être versionnés pour rendre les exports reproductibles.
