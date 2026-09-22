# Carpeta de audio

Aquí van las palabras grabadas del reto "Listen & write".

Se generan desde la pestaña **Actions** → *Grabar las palabras del juego* →
**Run workflow**, o con doble clic en `tools/GRABAR-AUDIOS.command`.

Contenido después de generarlas:

- `<palabra>.mp3` — frase de entrada + palabra + palabra (el dictado).
- `<palabra>-solo.mp3` — solo la palabra (el botón *Play the word again*).
- `manifest.json` — índice de todas, con sus duraciones.

El juego busca `manifest.json` al arrancar. **Si esta carpeta está vacía no
pasa nada**: se usa la voz del navegador, como antes.

Ver `tools/README.md` para los detalles.
