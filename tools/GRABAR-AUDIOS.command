#!/bin/bash
#
#  Grabar las palabras de VOCAB BATTLE  ·  para Mac
#
#  Haz DOBLE CLIC en este archivo desde el Finder. No hay que escribir nada.
#
#  La primera vez tarda un poco mas porque prepara las herramientas.
#  Despues graba las 116 palabras (unos 10 minutos) y, si esta carpeta viene de
#  GitHub, los sube el solo.
#

set -u
cd "$(dirname "$0")/.." || exit 1

. "tools/_entorno.sh"

echo "==========================================================="
echo "   Grabando las palabras de VOCAB BATTLE"
echo "==========================================================="
echo
echo "Si aun no has oido las voces, cierra esto y haz doble clic antes en"
echo "ESCUCHAR-VOCES.command: tarda un minuto y te evita una grabacion"
echo "de diez minutos que no te guste."
echo

preparar_entorno || exit 1

echo
".venv-audio/bin/python" tools/build_words.py "$@"
ESTADO=$?
echo

if [ $ESTADO -ne 0 ]; then
  echo "La grabacion no ha terminado bien. Los mensajes de arriba dicen por que."
  echo "Puedes volver a hacer doble clic: continuara por donde se quedo."
  pausa
  exit $ESTADO
fi

if [ -d .git ] && command -v git >/dev/null 2>&1; then
  echo "Subiendo los audios a GitHub..."
  git add audio
  if git diff --staged --quiet; then
    echo "No habia audios nuevos que subir."
  elif git commit -q -m "Palabras de VOCAB BATTLE" && git push -q; then
    echo "LISTO. Los audios ya estan en GitHub y la aplicacion los usara sola."
  else
    echo "Los audios estan grabados en la carpeta  audio/  pero no he podido"
    echo "subirlos a GitHub. Puedes subirlos a mano desde la web del repositorio."
  fi
else
  echo "LISTO. Los audios estan en la carpeta  audio/"
  echo
  echo "Para publicarlos: entra en la pagina del repositorio en GitHub,"
  echo "pulsa 'Add file' > 'Upload files' y arrastra ahi la carpeta  audio/"
fi

pausa
