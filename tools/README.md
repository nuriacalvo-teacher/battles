# Audio de las palabras · VOCAB BATTLE

## El problema

El reto **"Listen & write"** dicta una palabra con la voz del navegador, y esa
voz no es la misma en cada aparato:

| Dispositivo | Qué voz sale de fábrica | Cómo suena |
|---|---|---|
| Mac con Chrome o Edge | voces de Google / Microsoft | bien |
| Mac con Safari | voz **compacta** de Apple | metálica |
| iPhone / iPad | voz **compacta** de Apple | metálica |
| Android | Google TTS | bien |
| Windows | voces de Microsoft | de correcto a muy bien |
| **Linux / Vitalinux** | **normalmente ninguna** | **el reto ni aparece** |

En los equipos sin ninguna voz instalada el reto se desactivaba entero: los
alumnos no podían jugarlo.

Con las palabras grabadas, **todos los equipos oyen lo mismo** y el reto
funciona en todas partes, Vitalinux incluido.

## Primero: elige la voz y óyela

### Comparar todas las voces disponibles

- **En el Mac:** doble clic en `tools/COMPARAR-VOCES.command`.
- **Online:** pestaña **Actions** → *Grabar las palabras del juego* →
  **Run workflow**, marcando **comparativa**. Descarga *voces-para-escuchar*
  desde la página de la ejecución.

Genera un MP3 con todas las voces británicas e irlandesas leyendo lo mismo,
cada una diciendo antes su nombre.

### Escribir tu elección

Abre `tools/voces.txt`:

```
voz = en-GB-SoniaNeural
```

Si te equivocas escribiendo el nombre, el programa avisa antes de grabar y
lista las válidas.

### Oír tu elección

- **En el Mac:** doble clic en `tools/ESCUCHAR-VOCES.command`.
- **Online:** **Run workflow** marcando **muestra**.

Unas cuantas palabras reales del banco con la voz elegida. No toca el juego.

## Cómo grabar las palabras

### Opción A · online, sin instalar nada

1. Pestaña **Actions** del repositorio.
2. **Grabar las palabras del juego** en la columna de la izquierda.
3. **Run workflow** → **Run workflow**, sin marcar ninguna casilla.

Tarda unos 10 minutos y sube las palabras él solo. Puedes cerrar el navegador.

> Si falla al subir: **Settings → Actions → General → Workflow permissions →
> Read and write permissions**. Se toca una sola vez.

### Opción B · en el Mac, con doble clic

Botón verde **Code** → **Download ZIP**, descomprimir, y doble clic en
`tools/GRABAR-AUDIOS.command`. Si macOS lo bloquea, el aviso sale en
**Ajustes del Sistema → Privacidad y seguridad → Abrir igualmente**.

### Opción C · desde el terminal

```bash
python3 -m venv .venv-audio
.venv-audio/bin/pip install edge-tts
.venv-audio/bin/python tools/build_words.py
git add audio && git commit -m "Palabras grabadas" && git push
```

### En los tres casos

**No hay que tocar `index.html`.** El juego busca `audio/manifest.json` al
arrancar: si existe usa las grabaciones, y si no, sigue usando la voz del
navegador, como antes.

Son 116 palabras, unos 7 minutos de audio y unos 3 MB.

## Qué se graba, exactamente

Dos ficheros por palabra:

- `ankle.mp3` — la frase de entrada, la palabra, y la palabra otra vez. Es lo
  que suena al empezar el reto.
- `ankle-solo.mp3` — solo la palabra. Es el botón *"Play the word again"*.

La frase de entrada se elige entre cuatro (*Listen carefully*, *Here is your
word*, *Are you ready?*, *Your word is:*) y es siempre la misma para cada
palabra, pero distinta entre palabras, para que la clase no oiga cuatro veces
seguidas la misma fórmula.

Se graba un poco más despacio de lo normal (`-8%`), porque es un dictado.

## Las palabras que escribe el profesor

Las que añades a mano en **"My word list"** no se pueden grabar por adelantado,
así que esas siguen usando la voz del navegador. En un equipo sin ninguna voz
instalada no se podrán dictar: el juego lo avisa y simplemente no les asigna el
reto "Listen & write", les da otro.

Si quieres que una palabra tuya también esté grabada, añádela al banco de
`index.html` y vuelve a lanzar la grabación.

## Si cambias o añades palabras al banco

```bash
.venv-audio/bin/python tools/build_words.py --only ankle elbow
```

O relanza el flujo de Actions: solo graba lo que falta, salvo que marques
**force**.
