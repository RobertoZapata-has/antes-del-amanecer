# Antes del amanecer

Una noche adentro de *La noche estrellada* (Vincent van Gogh, 1889). Aventura gráfica corta en 3D para el celular: entrás por la ventana del cuarto de Vincent en Saint-Rémy y tenés que llegar a la estrella de la mañana antes de que amanezca.

Jugalo en: https://robertozapata-has.github.io/antes-del-amanecer/

- Arrastrá para mirar, tocá el suelo para caminar y tocá las luces para hablar.
- En el cel, el botón del celular (arriba a la derecha) activa el giroscopio para mirar moviéndolo.

- Caminás en primera persona por un pueblo de calles angostas, faroles y vecinos pintados. El botón del mapa (o la tecla M) muestra a dónde ir.

El pueblo se genera con Blender (`blender/build_village.py`, se corre con el módulo `bpy`) y se exporta a `village.glb` + `layout.json`. El juego usa Three.js (r128) con un filtro de óleo y un cielo de pinceladas.
