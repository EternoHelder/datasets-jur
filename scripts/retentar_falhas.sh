#!/usr/bin/env bash
# =============================================================================
# retentar_falhas.sh
# Reprocessa URLs que falharam durante o download principal
#
# Uso:
#   chmod +x retentar_falhas.sh
#   ./retentar_falhas.sh [caminho_para_falhas.txt]
#
# O arquivo de falhas é gerado automaticamente em ~/dados_juridicos/falhas.txt
# =============================================================================

set -euo pipefail

FALHAS_FILE="${1:-${HOME}/dados_juridicos/falhas.txt}"
DESTINO_DIR="${HOME}/dados_juridicos/reprocessados"
LOG_FILE="${HOME}/dados_juridicos/reprocessados.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log() { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

if [[ ! -f "$FALHAS_FILE" ]]; then
    echo -e "${YELLOW}Nenhum arquivo de falhas encontrado em: ${FALHAS_FILE}${NC}"
    exit 0
fi

total=$(grep -c 'http' "$FALHAS_FILE" 2>/dev/null || echo 0)

if [[ $total -eq 0 ]]; then
    echo -e "${GREEN}Nenhuma falha pendente. Tudo OK.${NC}"
    exit 0
fi

log "Retentando ${total} download(s) com falha..."
mkdir -p "$DESTINO_DIR"

sucesso=0
falha=0

while IFS= read -r url; do
    [[ -z "$url" || "$url" == \#* ]] && continue

    nome=$(basename "$url")
    dest="${DESTINO_DIR}/${nome}"

    log "→ ${nome}"
    if curl -fsSL --retry 5 --retry-delay 10 \
            -H "User-Agent: juridico-downloader/1.0" \
            -o "$dest" "$url" 2>>"$LOG_FILE"; then
        echo -e "  ${GREEN}✔ OK${NC}"
        sucesso=$((sucesso + 1))
    else
        echo -e "  ${RED}✖ Ainda com falha${NC}"
        falha=$((falha + 1))
    fi

    sleep 2
done < "$FALHAS_FILE"

log "Concluído: ${sucesso} recuperados | ${falha} ainda com falha"

if [[ $falha -gt 0 ]]; then
    log "Arquivos ainda com falha — verifique manualmente o log: ${LOG_FILE}"
    exit 1
fi

exit 0
