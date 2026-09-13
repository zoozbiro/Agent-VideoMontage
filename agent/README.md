# Agent

Le cerveau du projet. Cette couche ne doit pas encoder directement la vidéo : elle produit des décisions de montage consommables par le moteur FFmpeg.

Exemples de décisions futures :

- quels segments conserver ;
- ordre des plans ;
- durée cible ;
- point de vue/reframing ;
- vitesse ;
- musique et synchronisation ;
- sous-titres ;
- profil de sortie.

La première implémentation peut rester simple : heuristiques + OpenCV + métadonnées, puis ajouter des modèles légers uniquement lorsque le besoin est démontré.
