#!/usr/bin/env python3
"""
upload_to_dify.py
Envia a documentação e os dados coletados deste repositório como fonte de
conhecimento (Knowledge Base) no Dify.

O Dify é uma plataforma open-source para construção de aplicações LLM com
suporte a RAG.  Este script utiliza a API de Knowledge Base do Dify para:

  1. Criar um dataset (base de conhecimento) no Dify
  2. Enviar os arquivos Markdown de documentação
  3. Enviar os arquivos de dados (JSON, JSONL, CSV) coletados pelos scripts
     de download

Uso:
  pip3 install requests tqdm
  python3 scripts/upload_to_dify.py \
      --api-key DIFY_API_KEY \
      --base-url http://localhost/v1

Variáveis de ambiente aceitas (alternativa aos flags):
  DIFY_API_KEY   — chave de API do Dify
  DIFY_BASE_URL  — URL base da API (ex: http://localhost/v1)

Referência da API:
  https://docs.dify.ai/guides/knowledge-base/maintain-dataset-via-api
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("Instale as dependências: pip3 install requests tqdm")
    sys.exit(1)

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# ─── Configurações ────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DADOS_DIR = Path.home() / "dados_juridicos"
LOG_FILE = Path.home() / "dados_juridicos" / "dify_upload.log"

# Extensões suportadas pelo Dify para upload de arquivo
EXTENSOES_SUPORTADAS = {".md", ".txt", ".json", ".jsonl", ".csv", ".pdf"}

# Tamanho máximo por arquivo que o Dify aceita (15 MB por padrão)
MAX_FILE_SIZE = 15 * 1024 * 1024

DATASET_NAME = "Datasets Jurídicos — Direito Civil BR"
DATASET_DESCRIPTION = (
    "Dados jurídicos brasileiros estruturados para RAG: "
    "acórdãos STJ, metadados DataJud/CNJ, e corpora acadêmicos. "
    "Recorte: Direito Civil, Família, Consumidor, Processo Civil. "
    "Período: Jan/2020 → Mar/2026."
)

SLEEP_BETWEEN = 1.0  # segundos entre uploads (respeita rate limit)


# ─── Logging ──────────────────────────────────────────────────────────────────
def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linha = f"[{ts}] [{level}] {msg}"
    print(linha)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


# ─── Setup da sessão HTTP ────────────────────────────────────────────────────
def setup_session(api_key: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "datasets-jur-uploader/1.0",
    })
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# ─── Funções da API Dify ─────────────────────────────────────────────────────
def criar_dataset(session: requests.Session, base_url: str) -> str:
    """Cria um dataset (knowledge base) no Dify e retorna o ID."""
    url = f"{base_url}/datasets"
    payload = {
        "name": DATASET_NAME,
        "description": DATASET_DESCRIPTION,
        "permission": "all_team_members",
    }

    resp = session.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    dataset_id = data["id"]
    log(f"Dataset criado: {dataset_id} ({DATASET_NAME})")
    return dataset_id


def listar_datasets(session: requests.Session, base_url: str) -> list:
    """Lista datasets existentes no Dify."""
    url = f"{base_url}/datasets"
    resp = session.get(url, params={"page": 1, "limit": 100}, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])


def encontrar_dataset_existente(
    session: requests.Session, base_url: str
) -> str | None:
    """Verifica se já existe um dataset com o mesmo nome."""
    datasets = listar_datasets(session, base_url)
    for ds in datasets:
        if ds.get("name") == DATASET_NAME:
            log(f"Dataset existente encontrado: {ds['id']}")
            return ds["id"]
    return None


def upload_arquivo(
    session: requests.Session,
    base_url: str,
    dataset_id: str,
    caminho: Path,
) -> bool:
    """Envia um arquivo para o dataset Dify via endpoint de upload."""
    if caminho.stat().st_size > MAX_FILE_SIZE:
        log(f"Arquivo muito grande ({caminho.stat().st_size} bytes): {caminho}", "WARN")
        return False

    if caminho.suffix not in EXTENSOES_SUPORTADAS:
        log(f"Extensão não suportada ({caminho.suffix}): {caminho}", "WARN")
        return False

    url = f"{base_url}/datasets/{dataset_id}/document/create-by-file"

    # Regras de segmentação — configuração padrão 'automatic'
    data = {
        "data": json.dumps({
            "indexing_technique": "high_quality",
            "process_rule": {"mode": "automatic"},
        }),
    }

    with open(caminho, "rb") as f:
        files = {"file": (caminho.name, f)}
        resp = session.post(url, data=data, files=files, timeout=120)

    if resp.status_code in (200, 201):
        log(f"  ✔ {caminho.name}")
        return True

    log(f"  ✖ Falha ({resp.status_code}): {caminho.name} — {resp.text[:200]}", "ERROR")
    return False


def upload_texto(
    session: requests.Session,
    base_url: str,
    dataset_id: str,
    nome: str,
    texto: str,
) -> bool:
    """Cria um documento no dataset a partir de texto puro."""
    url = f"{base_url}/datasets/{dataset_id}/document/create-by-text"
    payload = {
        "name": nome,
        "text": texto,
        "indexing_technique": "high_quality",
        "process_rule": {"mode": "automatic"},
    }

    resp = session.post(url, json=payload, timeout=60)
    if resp.status_code in (200, 201):
        log(f"  ✔ {nome} (texto)")
        return True

    log(f"  ✖ Falha ({resp.status_code}): {nome} — {resp.text[:200]}", "ERROR")
    return False


# ─── Coleta de arquivos ──────────────────────────────────────────────────────
def coletar_docs_repo() -> list[Path]:
    """Coleta arquivos Markdown do repositório (documentação)."""
    arquivos = []

    # README.md
    readme = REPO_ROOT / "README.md"
    if readme.exists():
        arquivos.append(readme)

    # docs/*.md
    docs_dir = REPO_ROOT / "docs"
    if docs_dir.exists():
        arquivos.extend(sorted(docs_dir.glob("*.md")))

    return arquivos


def coletar_dados(tipos: list[str] | None = None) -> list[Path]:
    """Coleta arquivos de dados em ~/dados_juridicos/ para upload."""
    if not DADOS_DIR.exists():
        log(f"Diretório de dados não encontrado: {DADOS_DIR}", "WARN")
        log("Execute primeiro os scripts de download.", "WARN")
        return []

    extensoes = tipos or [".json", ".jsonl", ".csv"]
    arquivos = []

    for ext in extensoes:
        for f in sorted(DADOS_DIR.rglob(f"*{ext}")):
            if f.stat().st_size <= MAX_FILE_SIZE and f.stat().st_size > 0:
                arquivos.append(f)

    return arquivos


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description=(
            "Envia documentação e dados deste repositório como fonte de "
            "conhecimento (Knowledge Base) no Dify"
        ),
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("DIFY_API_KEY"),
        help=(
            "Chave de API do Dify (Dataset API Key). "
            "Alternativa: variável de ambiente DIFY_API_KEY"
        ),
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DIFY_BASE_URL", "http://localhost/v1"),
        help=(
            "URL base da API Dify (ex: http://localhost/v1). "
            "Alternativa: variável de ambiente DIFY_BASE_URL"
        ),
    )
    parser.add_argument(
        "--dataset-id",
        default=None,
        help=(
            "ID de um dataset existente no Dify. "
            "Se omitido, cria um novo ou reutiliza existente com mesmo nome."
        ),
    )
    parser.add_argument(
        "--apenas-docs",
        action="store_true",
        help="Envia apenas a documentação do repositório (README + docs/)",
    )
    parser.add_argument(
        "--apenas-dados",
        action="store_true",
        help="Envia apenas os arquivos de dados coletados",
    )
    parser.add_argument(
        "--tipos",
        nargs="+",
        default=None,
        help="Extensões de dados a enviar (ex: .json .jsonl .csv). Padrão: todas",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas lista os arquivos que seriam enviados, sem upload",
    )
    args = parser.parse_args()

    if not args.api_key:
        parser.error(
            "API key obrigatória. Use --api-key ou defina DIFY_API_KEY."
        )

    base_url = args.base_url.rstrip("/")
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    log("=" * 60)
    log("  UPLOAD PARA DIFY — KNOWLEDGE BASE")
    log(f"  Dify URL: {base_url}")
    log(f"  Repositório: {REPO_ROOT}")
    log(f"  Dados: {DADOS_DIR}")
    log("=" * 60)

    # Coleta de arquivos
    docs = [] if args.apenas_dados else coletar_docs_repo()
    dados = [] if args.apenas_docs else coletar_dados(args.tipos)
    todos = docs + dados

    if not todos:
        log("Nenhum arquivo encontrado para upload.", "WARN")
        sys.exit(1)

    log(f"Arquivos encontrados: {len(docs)} doc(s) + {len(dados)} dado(s)")

    if args.dry_run:
        log("─── Modo dry-run — arquivos que seriam enviados: ───")
        for f in todos:
            tamanho = f.stat().st_size
            log(f"  {f} ({tamanho:,} bytes)")
        log(f"Total: {len(todos)} arquivo(s)")
        return

    session = setup_session(args.api_key)

    # Criar ou reutilizar dataset
    dataset_id = args.dataset_id
    if not dataset_id:
        dataset_id = encontrar_dataset_existente(session, base_url)
    if not dataset_id:
        dataset_id = criar_dataset(session, base_url)

    log(f"Dataset ID: {dataset_id}")

    # Upload de arquivos
    sucesso = 0
    falha = 0

    iterable = tqdm(todos, desc="Upload") if HAS_TQDM else todos

    for arquivo in iterable:
        try:
            ok = upload_arquivo(session, base_url, dataset_id, arquivo)
            if ok:
                sucesso += 1
            else:
                falha += 1
        except Exception as e:
            log(f"  ✖ Erro inesperado: {arquivo.name} — {e}", "ERROR")
            falha += 1

        time.sleep(SLEEP_BETWEEN)

    # Relatório final
    log("")
    log("=" * 60)
    log("  RESUMO DO UPLOAD")
    log(f"  Enviados: {sucesso}")
    log(f"  Falhas:   {falha}")
    log(f"  Dataset:  {dataset_id}")
    log(f"  Log:      {LOG_FILE}")
    log("=" * 60)

    if falha > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
