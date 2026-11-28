#!/usr/bin/env bash
# Simula en local el job compose del CI con el doble de prueba de Ollama
# (infra/ci/README.md), sin tocar el Ollama real del anfitrión.
#
# Requiere el esqueleto arriba (infra/scripts/esqueleto.sh arriba).
# Al terminar, aunque falle o se interrumpa, restaura el señuelo con el
# Ollama real y detiene el doble (trap).
#
# Código de salida: el de las pruebas y comprobaciones; 3 si además no se pudo
# restaurar el señuelo con el Ollama real (el entorno quedó sin recuperar).
#
# Variables: PUERTO_DOBLE (11435), PYTEST (~/.venvs/umbra-int/bin/pytest).
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$RAIZ"
PUERTO="${PUERTO_DOBLE:-11435}"
PYTEST="${PYTEST:-$HOME/.venvs/umbra-int/bin/pytest}"
COMPOSE=(docker compose -f infra/docker-compose.yml)
TEXTO="[doble de prueba de Ollama: respuesta fija del CI]"
URL_REAL="OLLAMA_URL=http://host.docker.internal:11434"
LOG=/tmp/ollama_doble.log
DOBLE=""

esperar_listo() {
  local c=""
  for _ in $(seq 1 24); do
    c=$(curl -s --max-time 5 -o /tmp/listo.json -w '%{http_code}' http://127.0.0.1:8002/listo)
    [ "$c" = 200 ] && { echo "  /listo [200] $(cat /tmp/listo.json)"; return 0; }
    sleep 5
  done
  echo "  /listo [$c] $(cat /tmp/listo.json 2>/dev/null)" >&2
  return 1
}

restaurar() {
  local codigo=$? restaurado=1 url
  trap - EXIT INT TERM HUP
  echo "--- Restaurando el señuelo con el Ollama real"
  env -u OLLAMA_URL "${COMPOSE[@]}" up -d --wait senuelo >/dev/null 2>&1 \
    || { echo "  No se pudo recrear el señuelo" >&2; restaurado=0; }
  [ -n "$DOBLE" ] && kill "$DOBLE" 2>/dev/null
  url=$("${COMPOSE[@]}" exec -T senuelo env 2>/dev/null | grep '^OLLAMA_URL=')
  echo "  ${url:-OLLAMA_URL no disponible}"
  [ "$url" = "$URL_REAL" ] || { echo "  El señuelo no volvió al Ollama real (:11434)" >&2; restaurado=0; }
  esperar_listo || { echo "  El señuelo no quedó listo con el Ollama real: revisar Ollama" >&2; restaurado=0; }
  if [ "$restaurado" = 0 ]; then
    echo "  ENTORNO SIN RESTAURAR: ver la recuperación manual en infra/ci/README.md" >&2
    exit 3
  fi
  exit "$codigo"
}

curl -fsS --max-time 3 http://127.0.0.1:8001/salud >/dev/null \
  || { echo "El esqueleto no está arriba: infra/scripts/esqueleto.sh arriba" >&2; exit 2; }

trap restaurar EXIT
trap 'exit 130' INT TERM HUP

echo "--- Doble de prueba de Ollama en el puerto $PUERTO"
python3 infra/ci/ollama_doble.py --puerto "$PUERTO" > "$LOG" 2>&1 &
DOBLE=$!
for _ in $(seq 1 30); do
  v=$(curl -fsS --max-time 2 "http://127.0.0.1:$PUERTO/api/version" 2>/dev/null) && break
  sleep 1
done
echo "  $v"
echo "${v:-}" | grep -q 'doble de prueba' || { echo "  En el puerto $PUERTO no responde el doble" >&2; exit 1; }

echo "--- Señuelo apuntando al doble"
export OLLAMA_URL="http://host.docker.internal:$PUERTO"
"${COMPOSE[@]}" up -d --wait senuelo >/dev/null 2>&1 || { echo "  No se pudo recrear el señuelo" >&2; exit 1; }
esperar_listo || exit 1

echo "--- Las 7 pruebas de integración"
"$PYTEST" infra/pruebas -q -p no:cacheprovider
resultado=$?

echo "--- Aislamiento respecto al Ollama real (OBS-18)"
url=$("${COMPOSE[@]}" exec -T senuelo env | grep '^OLLAMA_URL=')
generaciones=$(grep -c 'generate keep_alive' "$LOG")
ultimo=$("${COMPOSE[@]}" exec -T postgres psql -U umbra -d umbra_registro -At \
  -c "select detalle->>'respuesta' from eventos where tipo='respuesta_senuelo' order by id desc limit 1")
echo "  $url"
echo "  generaciones atendidas por el doble: $generaciones"
echo "  último evento 4: $ultimo"
if [ "$url" = "OLLAMA_URL=http://host.docker.internal:$PUERTO" ] && [ "$generaciones" -gt 0 ] && [ "$ultimo" = "$TEXTO" ]; then
  echo "  OK: el flujo usó solo el doble"
else
  echo "  FALLO: no se puede asegurar que se usó solo el doble" >&2
  resultado=1
fi
exit "$resultado"
