#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_words.py · graba las palabras del banco de VOCAB BATTLE.

Por que existe
--------------
El reto "Listen & write" dicta una palabra con la voz del navegador, y esa voz
no es la misma en cada aparato: en un iPhone recien sacado de la caja suena
metalica, y en Linux muchas veces no hay ninguna voz instalada, con lo que el
reto ni siquiera se puede jugar. Este script graba las palabras una sola vez,
con una voz britanica neuronal, y a partir de ahi todos los equipos de la clase
oyen exactamente lo mismo.

Uso
---
    pip install edge-tts
    python3 tools/build_words.py

Deja los ficheros en audio/ junto con audio/manifest.json. La aplicacion detecta
ese manifest sola: si esta, usa las grabaciones; si no, sigue usando la voz del
navegador. Las palabras que el profesor escribe a mano en "My word list" no se
pueden grabar por adelantado: esas siguen usando la voz del navegador.

Opciones utiles
---------------
    --only ankle elbow          graba solo esas palabras
    --force                     regraba aunque ya existan
    --demo                      una muestra corta, para oir la voz
    --audition                  comparativa con todas las voces disponibles
    --list-voices               lista las voces britanicas
"""

import argparse
import asyncio
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INDEX = os.path.join(ROOT, "index.html")
AUDIO_DIR = os.path.join(ROOT, "audio")
VOICES_FILE = os.path.join(HERE, "voces.txt")

# Voz por defecto. Se puede cambiar en tools/voces.txt sin tocar este fichero.
VOICE = "en-GB-SoniaNeural"

# Frase de entrada, para que la palabra no caiga a secas. Se elige siempre la
# misma para cada palabra, pero distinta entre palabras, asi la clase no oye
# cuatro veces seguidas la misma formula.
CARRIERS = ["Listen carefully.", "Here is your word.", "Are you ready?", "Your word is:"]
RATE = "-8%"          # un pelin mas lento que lo normal: es un dictado
GAP = 0.45            # silencio entre la frase de entrada y la palabra


def load_voice_config():
    """Lee tools/voces.txt, si existe, para cambiar la voz sin tocar el codigo."""
    global VOICE
    if not os.path.exists(VOICES_FILE):
        return
    for line in io.open(VOICES_FILE, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key.strip().lower() == "voz" and val.strip():
            VOICE = val.strip()


# ---------------------------------------------------------------------------
# 1 · leer las palabras de index.html
# ---------------------------------------------------------------------------
class JsLiteral(object):
    """Lector minimo de literales JavaScript: objetos con clave sin comillas,
    cadenas, numeros, true/false/null, comentarios y comas sobrantes."""

    def __init__(self, text):
        self.s = text
        self.i = 0

    def error(self, msg):
        line = self.s.count("\n", 0, self.i) + 1
        raise ValueError("%s (linea %d)" % (msg, line))

    def skip(self):
        while self.i < len(self.s):
            c = self.s[self.i]
            if c in " \t\r\n":
                self.i += 1
            elif self.s.startswith("/*", self.i):
                end = self.s.find("*/", self.i + 2)
                self.i = len(self.s) if end < 0 else end + 2
            elif self.s.startswith("//", self.i):
                end = self.s.find("\n", self.i)
                self.i = len(self.s) if end < 0 else end + 1
            else:
                return

    def value(self):
        self.skip()
        if self.i >= len(self.s):
            self.error("fin de fichero inesperado")
        c = self.s[self.i]
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c in "\"'":
            return self.string()
        if self.s.startswith("true", self.i):
            self.i += 4
            return True
        if self.s.startswith("false", self.i):
            self.i += 5
            return False
        if self.s.startswith("null", self.i):
            self.i += 4
            return None
        m = re.match(r"-?\d+(\.\d+)?([eE][-+]?\d+)?", self.s[self.i:])
        if not m:
            self.error("valor no reconocido: %r" % self.s[self.i:self.i + 20])
        self.i += m.end()
        txt = m.group(0)
        return float(txt) if ("." in txt or "e" in txt or "E" in txt) else int(txt)

    def string(self):
        quote = self.s[self.i]
        self.i += 1
        out = []
        while True:
            if self.i >= len(self.s):
                self.error("cadena sin cerrar")
            c = self.s[self.i]
            if c == "\\":
                nxt = self.s[self.i + 1]
                self.i += 2
                if nxt == "u":
                    out.append(chr(int(self.s[self.i:self.i + 4], 16)))
                    self.i += 4
                else:
                    out.append({"n": "\n", "t": "\t", "r": "\r", "b": "\b",
                                "f": "\f", "0": "\0"}.get(nxt, nxt))
            elif c == quote:
                self.i += 1
                return "".join(out)
            else:
                out.append(c)
                self.i += 1

    def arr(self):
        self.i += 1                      # [
        out = []
        while True:
            self.skip()
            if self.s[self.i] == "]":
                self.i += 1
                return out
            out.append(self.value())
            self.skip()
            if self.s[self.i] == ",":
                self.i += 1
            elif self.s[self.i] != "]":
                self.error("se esperaba , o ]")

    def obj(self):
        self.i += 1                      # {
        out = {}
        while True:
            self.skip()
            if self.s[self.i] == "}":
                self.i += 1
                return out
            if self.s[self.i] in "\"'":
                key = self.string()
            else:
                m = re.match(r"[A-Za-z_$][A-Za-z0-9_$]*", self.s[self.i:])
                if not m:
                    self.error("clave no reconocida")
                key = m.group(0)
                self.i += m.end()
            self.skip()
            if self.s[self.i] != ":":
                self.error("se esperaba : tras la clave %r" % key)
            self.i += 1
            out[key] = self.value()
            self.skip()
            if self.s[self.i] == ",":
                self.i += 1
            elif self.s[self.i] != "}":
                self.error("se esperaba , o }")



def read_topics():
    src = io.open(INDEX, encoding="utf-8").read()
    marca = "const TOPICS = ["
    start = src.find(marca)
    if start < 0:
        raise SystemExit("No encuentro 'const TOPICS = [' en index.html")
    reader = JsLiteral(src)
    reader.i = start + len("const TOPICS = ")
    return reader.arr()


def bank_words():
    """Las palabras que el juego puede dictar: la respuesta correcta de cada
    pregunta del banco, sin repetir y en el orden en que aparecen."""
    out, seen = [], set()
    for topic in read_topics():
        for q in topic.get("qs") or []:
            word = (q[1] or [""])[0]
            key = word.strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append((key, word, topic.get("id", "")))
    return out


def slug(word):
    s = re.sub(r"[^a-z0-9]+", "-", word.strip().lower()).strip("-")
    return s or hashlib.md5(word.encode("utf-8")).hexdigest()[:10]


def carrier_for(word):
    digest = hashlib.md5(word.encode("utf-8")).hexdigest()
    return CARRIERS[int(digest[:8], 16) % len(CARRIERS)]


# ---------------------------------------------------------------------------
# 2 · MP3 sin dependencias externas: duracion y silencio
# ---------------------------------------------------------------------------
BITRATES_V1 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
BITRATES_V2 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
RATES = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}


def mp3_frames(data):
    """Recorre las tramas MPEG Layer III. Devuelve (offset, tamano, muestras,
    frecuencia). Se salta ID3 y cualquier basura entre tramas."""
    i = 0
    if data[:3] == b"ID3":
        size = 0
        for b in data[6:10]:
            size = (size << 7) | (b & 0x7F)
        i = 10 + size
    n = len(data)
    while i + 4 <= n:
        if data[i] != 0xFF or (data[i + 1] & 0xE0) != 0xE0:
            i += 1
            continue
        version = (data[i + 1] >> 3) & 0x03      # 3=MPEG1 2=MPEG2 0=MPEG2.5
        layer = (data[i + 1] >> 1) & 0x03        # 1 = Layer III
        if version == 1 or layer != 1:
            i += 1
            continue
        br_index = (data[i + 2] >> 4) & 0x0F
        sr_index = (data[i + 2] >> 2) & 0x03
        padding = (data[i + 2] >> 1) & 0x01
        if br_index in (0, 15) or sr_index == 3:
            i += 1
            continue
        rate = RATES[version][sr_index]
        bitrate = (BITRATES_V1 if version == 3 else BITRATES_V2)[br_index] * 1000
        samples = 1152 if version == 3 else 576
        size = (samples // 8) * bitrate // rate + padding
        if size < 4 or i + size > n:
            break
        yield i, size, samples, rate
        i += size


def mp3_info(data):
    """(duracion en segundos, frecuencia de muestreo)."""
    total, rate = 0, 24000
    for _, _, samples, sr in mp3_frames(data):
        total += samples
        rate = sr
    return (total / float(rate) if rate else 0.0), rate


def silence_mp3(seconds, rate=24000):
    """Tramas MPEG-2 Layer III mono vacias: se decodifican como silencio y se
    pueden pegar delante o detras de cualquier MP3 de la misma frecuencia."""
    sr_index = {22050: 0, 24000: 1, 16000: 2}.get(rate)
    if sr_index is None:                          # frecuencia rara: sin silencio
        return b""
    bitrate = 32000
    frame_len = (576 // 8) * bitrate // rate      # 96 bytes a 24 kHz
    header = bytes([
        0xFF,
        0b11110011,                               # MPEG2 · Layer III · sin CRC
        (4 << 4) | (sr_index << 2),               # 32 kbps · frecuencia · sin padding
        0b11000000,                               # mono
    ])
    frame = header + b"\x00" * (frame_len - 4)
    count = int(round(seconds / (576.0 / rate)))
    return frame * max(0, count)



# ---------------------------------------------------------------------------
# 3 · sintesis
# ---------------------------------------------------------------------------
async def synth(text, voice):
    import edge_tts
    chunks = []
    communicate = edge_tts.Communicate(text, voice, rate=RATE)
    async for item in communicate.stream():
        if item["type"] == "audio":
            chunks.append(item["data"])
    if not chunks:
        raise RuntimeError("edge-tts no devolvio audio para la voz %s" % voice)
    return b"".join(chunks)


async def build_word(key, word, force, existing):
    """Dos ficheros por palabra:
         <slug>.mp3       frase de entrada + palabra + palabra (el dictado)
         <slug>-solo.mp3  solo la palabra (el boton 'Play the word again')"""
    base = slug(key)
    dictado = os.path.join(AUDIO_DIR, base + ".mp3")
    solo = os.path.join(AUDIO_DIR, base + "-solo.mp3")
    if (not force and existing and os.path.exists(dictado) and os.path.exists(solo)
            and existing.get("f") == base + ".mp3"):
        return existing

    palabra = await synth(word + ".", VOICE)
    rate = mp3_info(palabra)[1]
    entrada = await synth(carrier_for(key), VOICE)
    hueco = silence_mp3(GAP, rate)
    completo = entrada + hueco + palabra + hueco + palabra

    with open(dictado, "wb") as fh:
        fh.write(completo)
    with open(solo, "wb") as fh:
        fh.write(palabra)
    return {
        "f": base + ".mp3", "d": round(mp3_info(completo)[0], 2),
        "s": base + "-solo.mp3", "ds": round(mp3_info(palabra)[0], 2),
    }


async def build_demo():
    """Muestra corta, para oir la voz antes de grabar las 116 palabras."""
    ejemplos = [w for _, w, _ in bank_words()][:4] or ["champion"]
    if not os.path.isdir(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)
    print("Grabando una muestra con la voz %s...\n" % VOICE)
    piezas, rate = [], 24000
    for word in ejemplos:
        print("  %s" % word)
        entrada = await synth(carrier_for(word.lower()), VOICE)
        palabra = await synth(word + ".", VOICE)
        rate = mp3_info(palabra)[1]
        hueco = silence_mp3(GAP, rate)
        if piezas:
            piezas.append(silence_mp3(0.9, rate))
        piezas.append(entrada + hueco + palabra + hueco + palabra)
    out = os.path.join(AUDIO_DIR, "muestra-voces.mp3")
    with open(out, "wb") as fh:
        fh.write(b"".join(piezas))
    print("\nMuestra lista: %s  (%d segundos)" % (out, round(mp3_info(b"".join(piezas))[0])))
    print("Escuchala. Si te convence, graba todas las palabras; si no, cambia")
    print("la voz en tools/voces.txt. Este fichero no afecta al juego.")
    return 0


SAMPLE_LINE = ("Listen carefully. Champion. Champion. Now write the word you have just heard.")


async def build_audition(locales):
    """Un solo MP3 con todas las voces disponibles leyendo lo mismo."""
    import edge_tts
    voices = [v for v in await edge_tts.list_voices()
              if any(v["Locale"].startswith(loc) for loc in locales)]
    voices.sort(key=lambda v: (v["Locale"], v["Gender"], v["ShortName"]))
    if not voices:
        print("No he encontrado ninguna voz para: %s" % ", ".join(locales), file=sys.stderr)
        return 1
    if not os.path.isdir(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)
    print("Grabando una comparativa con %d voces...\n" % len(voices))
    piezas, elapsed, rate = [], 0.0, 24000
    for v in voices:
        short = v["ShortName"]
        label = short.split("-")[-1].replace("Neural", "")
        print("  %d:%02d  %-30s %s" % (elapsed // 60, elapsed % 60, short, v["Gender"]))
        try:
            audio = await synth("%s. %s" % (label, SAMPLE_LINE), short)
        except Exception as exc:                        # noqa: BLE001
            print("        (fallo: %s)" % exc)
            continue
        seconds, rate = mp3_info(audio)
        if piezas:
            gap = silence_mp3(0.9, rate)
            piezas.append(gap)
            elapsed += mp3_info(gap)[0]
        piezas.append(audio)
        elapsed += seconds
    out = os.path.join(AUDIO_DIR, "comparativa-voces.mp3")
    with open(out, "wb") as fh:
        fh.write(b"".join(piezas))
    print("\nComparativa lista: %s  (%d min %02d s)" % (out, elapsed // 60, elapsed % 60))
    print("\nApunta la que mas te guste y escribe su nombre en tools/voces.txt.")
    return 0


async def check_voice(name):
    import edge_tts
    try:
        catalog = {v["ShortName"] for v in await edge_tts.list_voices()}
    except Exception:                                   # noqa: BLE001
        return True
    if name in catalog:
        return True
    print("\nLa voz '%s' de tools/voces.txt no existe.\n" % name, file=sys.stderr)
    print("Disponibles para ingles britanico e irlandes:\n", file=sys.stderr)
    for n in sorted(v for v in catalog if v.startswith("en-GB") or v.startswith("en-IE")):
        print("    %s" % n, file=sys.stderr)
    return False


async def main_async(args):
    if args.list_voices:
        import edge_tts
        for v in await edge_tts.list_voices():
            if v["Locale"].startswith("en-GB") or v["Locale"].startswith("en-IE"):
                print("%-30s %-8s %s" % (v["ShortName"], v["Gender"], v["Locale"]))
        return 0

    load_voice_config()
    if args.audition:
        return await build_audition(args.locales)
    if not await check_voice(VOICE):
        return 1
    if args.demo:
        return await build_demo()

    if not os.path.isdir(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)

    words = bank_words()
    if args.only:
        wanted = set(w.strip().lower() for w in args.only)
        words = [w for w in words if w[0] in wanted]
        missing = wanted - set(w[0] for w in words)
        if missing:
            print("No estan en el banco: %s" % ", ".join(sorted(missing)), file=sys.stderr)
            return 1

    manifest_path = os.path.join(AUDIO_DIR, "manifest.json")
    entries = {}
    if os.path.exists(manifest_path):
        try:
            entries = json.load(io.open(manifest_path, encoding="utf-8")).get("words", {})
        except ValueError:
            entries = {}

    print("Grabando %d palabras con la voz %s...\n" % (len(words), VOICE))
    fallos = 0
    for idx, (key, word, topic) in enumerate(words, 1):
        print("  [%3d/%3d] %-24s %-8s" % (idx, len(words), word, topic), end="", flush=True)
        try:
            entries[key] = await build_word(key, word, args.force, entries.get(key))
            print("  ->  %.1f s" % entries[key]["d"])
        except Exception as exc:                        # noqa: BLE001
            fallos += 1
            print("  ->  ERROR: %s" % exc)
            if args.stop_on_error:
                return 1

    with io.open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump({"version": 1, "voice": VOICE, "words": entries},
                  fh, ensure_ascii=False, indent=1, sort_keys=True)
    total = sum(e["d"] for e in entries.values())
    print("\nListo: %d palabras · %d min %02d s de audio" %
          (len(entries), total // 60, total % 60))
    if fallos:
        print("Con %d fallos. Vuelve a lanzarlo: continua por donde iba." % fallos)
    print("Manifest: %s" % manifest_path)
    return 1 if fallos else 0


def main():
    ap = argparse.ArgumentParser(description="Graba las palabras de VOCAB BATTLE con edge-tts.")
    ap.add_argument("--only", nargs="+", metavar="PALABRA", help="graba solo estas palabras")
    ap.add_argument("--force", action="store_true", help="regraba aunque ya exista")
    ap.add_argument("--demo", action="store_true", help="graba solo una muestra corta")
    ap.add_argument("--audition", action="store_true", help="comparativa con todas las voces")
    ap.add_argument("--locales", nargs="+", default=["en-GB", "en-IE"], metavar="LOCALE",
                    help="acentos de la comparativa (por defecto en-GB en-IE)")
    ap.add_argument("--list-voices", action="store_true", help="lista las voces britanicas")
    ap.add_argument("--stop-on-error", action="store_true", help="para en el primer fallo")
    args = ap.parse_args()
    try:
        import edge_tts                                # noqa: F401
    except ImportError:
        print("Falta edge-tts. Instalalo con:  pip install edge-tts", file=sys.stderr)
        return 1
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
