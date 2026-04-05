#!/usr/bin/env bash
# =============================================================================
# download_stj_academicos.sh
# Pipeline de download — STJ Dados Abertos + Corpora Acadêmicos
#
# Recorte temático: Direito Civil, Família, Consumidor, Processo Civil,
#                   Indenizações cíveis e de consumo (2ª Seção, 3ª e 4ª Turmas)
# Recorte temporal: Janeiro/2020 → Março/2026
#
# Uso:
#   chmod +x download_stj_academicos.sh
#   ./download_stj_academicos.sh
#
# Dependências: curl, wget, python3 (para HuggingFace), pip3
# =============================================================================

set -euo pipefail

# ─── Configurações ─────────────────────────────────────────────────────────
BASE_DIR="${HOME}/dados_juridicos"
LOG_FILE="${BASE_DIR}/download.log"
PARALLEL_JOBS=4          # downloads simultâneos
START_YEAR=2020
END_YEAR=2026
END_MONTH=3              # até março/2026

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ─── Funções utilitárias ────────────────────────────────────────────────────
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "$msg" | tee -a "$LOG_FILE"
}

ok()   { log "${GREEN}✔ $1${NC}"; }
warn() { log "${YELLOW}⚠ $1${NC}"; }
err()  { log "${RED}✖ $1${NC}"; }
info() { log "${BLUE}→ $1${NC}"; }

# Download com retry (3 tentativas, backoff exponencial)
download_file() {
    local url="$1"
    local dest="$2"
    local label="${3:-$dest}"

    if [[ -f "$dest" && -s "$dest" ]]; then
        warn "Já existe: $label — pulando"
        return 0
    fi

    mkdir -p "$(dirname "$dest")"

    local attempt=0
    while [[ $attempt -lt 3 ]]; do
        if curl -fsSL --retry 3 --retry-delay 5 \
                -H "User-Agent: juridico-downloader/1.0" \
                -o "$dest" "$url" 2>>"$LOG_FILE"; then
            ok "$label"
            return 0
        fi
        attempt=$((attempt + 1))
        warn "Tentativa $attempt falhou para: $label"
        sleep $((attempt * 5))
    done

    err "Falha após 3 tentativas: $label"
    echo "$url" >> "${BASE_DIR}/falhas.txt"
    return 1
}

# Verifica se data está no recorte temporal
data_no_recorte() {
    local ano=$1
    local mes=$2
    if [[ $ano -lt $START_YEAR ]]; then return 1; fi
    if [[ $ano -gt $END_YEAR ]]; then return 1; fi
    if [[ $ano -eq $END_YEAR && $mes -gt $END_MONTH ]]; then return 1; fi
    return 0
}

# ─── Inicialização ──────────────────────────────────────────────────────────
mkdir -p "$BASE_DIR"
: > "$LOG_FILE"
: > "${BASE_DIR}/falhas.txt"

log "============================================================"
log "  PIPELINE DE DOWNLOAD — DADOS JURÍDICOS"
log "  Período: ${START_YEAR}/01 → ${END_YEAR}/0${END_MONTH}"
log "  Destino: ${BASE_DIR}"
log "============================================================"

# ─── BLOCO 1: PRECEDENTES QUALIFICADOS (STJ) ────────────────────────────────
# Dataset estático: Recursos Repetitivos e IACs (temas e processos vinculados)
info "=== [1/4] PRECEDENTES QUALIFICADOS (STJ) ==="

PREC_DIR="${BASE_DIR}/stj/precedentes_qualificados"
mkdir -p "$PREC_DIR"

DATASET_ID_PREC="4238da2f-c07b-4c1a-b345-4402accacdcf"
BASE_STJ="https://dadosabertos.web.stj.jus.br/dataset/${DATASET_ID_PREC}/resource"

declare -A PREC_ARQUIVOS=(
    ["dicionario-temas.csv"]="d5e50514-6dba-4f1e-8557-94f135eae03b"
    ["temas.csv"]="df29da13-7d6b-41ba-ad96-cd1a5bbd191c"
    ["dicionario-processos.csv"]="162e58f0-01c1-4d91-94a4-664b4de81e79"
    ["processos.csv"]="7ed21202-0049-4fcb-aa7c-48d810d3c499"
)

for arquivo in "${!PREC_ARQUIVOS[@]}"; do
    resource_id="${PREC_ARQUIVOS[$arquivo]}"
    url="${BASE_STJ}/${resource_id}/download/${arquivo}"
    download_file "$url" "${PREC_DIR}/${arquivo}" "Precedentes: ${arquivo}"
done

# ─── BLOCO 2: ESPELHOS DE ACÓRDÃOS — TURMAS CÍVEIS ──────────────────────────
# 2ª Seção (Direito Privado), 3ª Turma e 4ª Turma
# Cobertura dos JSONs mensais: mai/2022 → fev/2026
# ZIP inicial contém histórico 2020-2022
info "=== [2/4] ESPELHOS DE ACÓRDÃOS — 2ª SEÇÃO / 3ª E 4ª TURMAS ==="

declare -A ESPELHOS=(
    # [nome_legível]="dataset_uuid:arquivo_zip_uuid"
    ["segunda-secao"]="a96a175b-a54b-4bfd-82b8-fcd7cc0200bc"
    ["terceira-turma"]="PLACEHOLDER_3T"   # UUID será resolvido via API abaixo
    ["quarta-turma"]="PLACEHOLDER_4T"
)

# Carrega UUIDs reais do arquivo coletado pelo browser_task anterior
# (stj_urls_relevantes.json gerado no workspace)
URLS_JSON="/home/user/workspace/stj_urls_relevantes.json"

download_espelhos_dataset() {
    local nome="$1"
    local dataset_slug="$2"
    local dir_destino="${BASE_DIR}/stj/espelhos/${nome}"
    mkdir -p "$dir_destino"

    info "Baixando espelhos: ${nome}"

    # Busca recursos via API CKAN
    local api_url="https://dadosabertos.web.stj.jus.br/api/3/action/package_show?id=${dataset_slug}"
    local api_resp
    api_resp=$(curl -fsSL --retry 3 "$api_url" 2>>"$LOG_FILE" || echo "")

    if [[ -z "$api_resp" ]]; then
        err "Não foi possível acessar a API CKAN para: ${nome}"
        return 1
    fi

    # Extrai recursos com Python (mais robusto que jq para JSON aninhado)
    python3 - <<PYEOF
import json, subprocess, os, sys

resp = json.loads('''${api_resp}'''.replace("'", "\\'"))
resources = resp.get('result', {}).get('resources', [])

base_dir = "${dir_destino}"
log_file = "${LOG_FILE}"
start_year = ${START_YEAR}
end_year = ${END_YEAR}
end_month = ${END_MONTH}

downloaded = 0
skipped = 0
failed = 0

for r in resources:
    name = r.get('name', r.get('url', '').split('/')[-1])
    url  = r.get('url', '')
    fmt  = r.get('format', '').upper()

    if not url:
        continue

    # Filtro temporal: extrai YYYYMM ou YYYYMMDD do nome
    import re
    m = re.search(r'(\d{4})(\d{2})', name)
    if m:
        ano, mes = int(m.group(1)), int(m.group(2))
        if ano < start_year or ano > end_year:
            continue
        if ano == end_year and mes > end_month:
            continue

    dest = os.path.join(base_dir, name if name.endswith(('.json', '.zip', '.csv')) else name + '.json')

    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        skipped += 1
        continue

    result = subprocess.run(
        ['curl', '-fsSL', '--retry', '3', '--retry-delay', '5',
         '-H', 'User-Agent: juridico-downloader/1.0',
         '-o', dest, url],
        capture_output=True
    )

    if result.returncode == 0:
        downloaded += 1
        print(f"  ✔ {name}")
    else:
        failed += 1
        print(f"  ✖ FALHA: {name} | {url}", file=sys.stderr)
        with open("${BASE_DIR}/falhas.txt", 'a') as f:
            f.write(url + '\n')

print(f"  → {nome}: {downloaded} baixados | {skipped} já existiam | {failed} falhas")
PYEOF
}

# Slugs reais dos datasets CKAN
download_espelhos_dataset "segunda-secao"  "espelhos-de-acordaos-segunda-secao"
download_espelhos_dataset "terceira-turma" "espelhos-de-acordaos-terceira-turma"
download_espelhos_dataset "quarta-turma"   "espelhos-de-acordaos-quarta-turma"

# ─── BLOCO 3: CORPORA ACADÊMICOS ────────────────────────────────────────────
info "=== [3/4] CORPORA ACADÊMICOS ==="

# 3A. RulingBR (STF 2011-2018 — referência histórica)
RULING_DIR="${BASE_DIR}/academico/rulingbr"
mkdir -p "$RULING_DIR"
info "Baixando RulingBR (STF 2011-2018)..."
download_file \
    "https://github.com/diego-feijo/rulingbr/raw/master/rulingbr-v1.2.tar.xz" \
    "${RULING_DIR}/rulingbr-v1.2.tar.xz" \
    "RulingBR v1.2 (tar.xz)"

if [[ -f "${RULING_DIR}/rulingbr-v1.2.tar.xz" ]]; then
    info "Extraindo RulingBR..."
    tar -xJf "${RULING_DIR}/rulingbr-v1.2.tar.xz" -C "$RULING_DIR" 2>>"$LOG_FILE" \
        && ok "RulingBR extraído" \
        || warn "Falha na extração do RulingBR — verifique manualmente"
fi

# 3B. Brazilian Court Decisions (HuggingFace — TJAL 2018/2019)
BCD_DIR="${BASE_DIR}/academico/brazilian_court_decisions"
mkdir -p "$BCD_DIR"
info "Baixando Brazilian Court Decisions (HuggingFace)..."

for split in train validation test; do
    download_file \
        "https://huggingface.co/datasets/joelniklaus/brazilian_court_decisions/resolve/main/data/${split}-00000-of-00001.parquet" \
        "${BCD_DIR}/${split}.parquet" \
        "BrazilianCourtDecisions: ${split}"
done

# Fallback: tenta URL alternativa se parquet não existir
if [[ ! -s "${BCD_DIR}/train.parquet" ]]; then
    warn "Tentando URL alternativa para Brazilian Court Decisions..."
    python3 -c "
from datasets import load_dataset
import os
ds = load_dataset('joelniklaus/brazilian_court_decisions')
for split in ['train', 'validation', 'test']:
    ds[split].to_parquet('${BCD_DIR}/' + split + '.parquet')
    print(f'  ✔ {split}: {len(ds[split])} registros')
" 2>>"$LOG_FILE" || warn "datasets lib não instalada — rode: pip3 install datasets"
fi

# 3C. JurisTCU (HuggingFace — TCU jurisprudência selecionada)
TCU_DIR="${BASE_DIR}/academico/juristcu"
mkdir -p "$TCU_DIR"
info "Baixando JurisTCU (HuggingFace)..."

for split in train test; do
    download_file \
        "https://huggingface.co/datasets/LeandroRibeiro/JurisTCU/resolve/main/data/${split}-00000-of-00001.parquet" \
        "${TCU_DIR}/${split}.parquet" \
        "JurisTCU: ${split}"
done

# Fallback Python
if [[ ! -s "${TCU_DIR}/train.parquet" ]]; then
    warn "Tentando fallback Python para JurisTCU..."
    python3 -c "
from datasets import load_dataset
import os
ds = load_dataset('LeandroRibeiro/JurisTCU')
for split in ds.keys():
    ds[split].to_parquet('${TCU_DIR}/' + split + '.parquet')
    print(f'  ✔ {split}: {len(ds[split])} registros')
" 2>>"$LOG_FILE" || warn "Falha no fallback JurisTCU"
fi

# ─── BLOCO 4: RELATÓRIO FINAL ────────────────────────────────────────────────
info "=== [4/4] RELATÓRIO FINAL ==="

echo ""
log "============================================================"
log "  RESUMO DO DOWNLOAD"
log "============================================================"

# Conta arquivos por categoria
for categoria in "stj/precedentes_qualificados" "stj/espelhos/segunda-secao" \
                 "stj/espelhos/terceira-turma" "stj/espelhos/quarta-turma" \
                 "academico/rulingbr" "academico/brazilian_court_decisions" \
                 "academico/juristcu"; do
    dir="${BASE_DIR}/${categoria}"
    if [[ -d "$dir" ]]; then
        count=$(find "$dir" -type f | wc -l)
        size=$(du -sh "$dir" 2>/dev/null | cut -f1)
        ok "${categoria}: ${count} arquivo(s) | ${size}"
    fi
done

# Verifica falhas
falhas=$(wc -l < "${BASE_DIR}/falhas.txt" 2>/dev/null || echo 0)
if [[ $falhas -gt 0 ]]; then
    warn "${falhas} download(s) falharam — veja: ${BASE_DIR}/falhas.txt"
    warn "Para retentar apenas as falhas, execute:"
    warn "  while IFS= read -r url; do curl -fsSL -O \"\$url\"; done < ${BASE_DIR}/falhas.txt"
else
    ok "Nenhuma falha registrada."
fi

log "Log completo: ${LOG_FILE}"
log "Download concluído em: $(date '+%Y-%m-%d %H:%M:%S')"
