
#!/usr/bin/env bash
# Umbra · arranque del esqueleto de punta a punta (issue #14).
# Uso: infra/scripts/esqueleto.sh {arriba|estado|abajo|reiniciar-datos|logs [servicio]}
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE=(docker compose -f "$RAIZ/infra/docker-compose.yml")

uso() {
  echo "Uso: $0 {arriba|estado|abajo|reiniciar-datos|logs [servicio]}" >&2
  exit 2
}

case "${1:-}" in
  arriba)
    "${COMPOSE[@]}" up -d --build --wait --wait-timeout 180
    "${COMPOSE[@]}" ps
    echo

    echo "Verificando detector..."
    curl -fsS http://127.0.0.1:8001/salud && echo

    echo "Verificando señuelo..."
    curl -fsS http://127.0.0.1:8002/salud && echo

    echo "Detector: http://127.0.0.1:8001/docs"
    echo "Señuelo:  http://127.0.0.1:8002/docs"
    ;;
  estado)
    "${COMPOSE[@]}" ps
    ;;
  abajo)
    "${COMPOSE[@]}" down
    ;;
  reiniciar-datos)
    # Borra el volumen de PostgreSQL: el esquema se vuelve a aplicar al subir.
    read -r -p "Esto borra todas las sesiones registradas en el esqueleto. ¿Continuar? [s/N] " r
    [[ "$r" == "s" || "$r" == "S" ]] || { echo "Cancelado."; exit 0; }
    "${COMPOSE[@]}" down -v
    ;;
  logs)
    shift
    "${COMPOSE[@]}" logs -f --tail=100 "$@"
    ;;
  *)
    uso
    ;;
esac
