#!/usr/bin/env python3
"""
download_datajud.py
Coleta metadados processuais via API Pública do DataJud (CNJ)

Recorte temático:
  Classes: Procedimento Comum Cível, Ação de Indenização, Embargos à Execução,
           Cumprimento de Sentença, Ação de Reparação de Danos,
           Procedimento do CDC (Código de Defesa do Consumidor),
           Divórcio, Alimentos, Guarda, Ação de Família

Recorte temporal: 01/01/2020 → 31/03/2026

Uso:
  pip3 install requests tqdm
  python3 download_datajud.py --api-key SUA_CHAVE_AQUI

Obtendo a API key:
  Acesse https://datajud-wiki.cnj.jus.br/api-publica/acesso
  Registre-se como desenvolvedor e solicite a chave.

Documentação da API: https://datajud-wiki.cnj.jus.br
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
BASE_DIR = Path.home() / "dados_juridicos" / "datajud"
LOG_FILE = Path.home() / "dados_juridicos" / "datajud_download.log"

API_BASE = "https://api-publica.datajud.cnj.jus.br"

# Tribunais alvo — foco em direito cível/família/consumidor
# Ajuste conforme sua necessidade
TRIBUNAIS = [
    "tjmg",   # Tribunal de Justiça de Minas Gerais
    "tjsp",   # Tribunal de Justiça de São Paulo
    "tjgo",   # Tribunal de Justiça de Goiás
    "tjdf",   # Tribunal de Justiça do Distrito Federal
    "tjrj",   # Tribunal de Justiça do Rio de Janeiro
    "stj",    # Superior Tribunal de Justiça
]

# Códigos de classes processuais (Tabela CNJ)
# Referência: https://www.cnj.jus.br/sgt/consulta_publica_classes.php
CLASSES_ALVO = {
    7: "Procedimento Comum",
    436: "Procedimento do Juizado Especial Cível",
    281: "Ação de Indenização por Dano Moral",
    275: "Ação de Reparação de Danos",
    283: "Ação de Indenização por Dano Moral e Material",
    40: "Embargos à Execução",
    156: "Cumprimento de Sentença",
    198: "Ação de Alimentos",
    14007: "Divórcio Consensual",
    14008: "Divórcio Litigioso",
    864: "Guarda e Responsabilidade",
    31: "Ação de Despejo",
    155: "Execução de Título Extrajudicial",
}

# Assuntos CNJ — Direito Civil, Consumidor, Família
ASSUNTOS_ALVO = {
    # Direito Civil / Indenizações
    7778: "Responsabilidade Civil",
    7780: "Dano Moral",
    7781: "Dano Material",
    7782: "Dano Estético",
    10009: "Indenização por Dano ao Consumidor",
    # Direito do Consumidor
    6230: "Responsabilidade do Fornecedor",
    6233: "Práticas Abusivas",
    6223: "Vícios do Produto",
    6224: "Vícios do Serviço",
    # Processo Civil
    10250: "Cumprimento de Sentença",
    10249: "Execução de Título Judicial",
    # Direito de Família
    7660: "Alimentos",
    7659: "Divórcio",
    7663: "Guarda",
    7672: "Família — Indenização",
}

DATAS = {
    "inicio": "2020-01-01",
    "fim": "2026-03-31",
}

PAGE_SIZE = 100     # máximo permitido pela API
MAX_PAGES = 500     # limite de segurança por tribunal/classe
SLEEP_BETWEEN = 1.5 # segundos entre requisições (respeita rate limit)

# ─── Setup ───────────────────────────────────────────────────────────────────
def setup_session(api_key: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "Authorization": f"ApiKey {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "juridico-downloader/1.0",
    })
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linha = f"[{ts}] [{level}] {msg}"
    print(linha)
    with open(LOG_FILE, "a") as f:
        f.write(linha + "\n")


# ─── Funções de consulta ──────────────────────────────────────────────────────
def buscar_processos(
    session: requests.Session,
    tribunal: str,
    classe_codigo: int = None,
    assunto_codigo: int = None,
    pagina: int = 1,
) -> dict:
    """
    Consulta a API DataJud com filtros de classe, assunto e período.
    Retorna o JSON da resposta.
    """
    endpoint = f"{API_BASE}/api_publica_{tribunal}/_search"

    # Monta query ElasticSearch
    must = [
        {
            "range": {
                "dataAjuizamento": {
                    "gte": DATAS["inicio"],
                    "lte": DATAS["fim"],
                }
            }
        }
    ]

    if classe_codigo:
        must.append({"term": {"classe.codigo": classe_codigo}})

    if assunto_codigo:
        must.append({"term": {"assuntos.codigo": assunto_codigo}})

    query = {
        "size": PAGE_SIZE,
        "from": (pagina - 1) * PAGE_SIZE,
        "query": {"bool": {"must": must}},
        "_source": [
            "id",
            "numeroProcesso",
            "classe",
            "sistema",
            "formato",
            "tribunal",
            "dataHoraUltimaAtualizacao",
            "grau",
            "dataAjuizamento",
            "movimentos",
            "assuntos",
            "orgaoJulgador",
        ],
    }

    try:
        resp = session.post(endpoint, json=query, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            log("API key inválida ou expirada", "ERROR")
            sys.exit(1)
        elif e.response.status_code == 404:
            log(f"Tribunal não encontrado: {tribunal}", "WARN")
            return {}
        log(f"Erro HTTP {e.response.status_code} para {tribunal}", "ERROR")
        return {}
    except Exception as e:
        log(f"Erro na requisição: {e}", "ERROR")
        return {}


def salvar_pagina(dados: list, tribunal: str, classe: str, pagina: int):
    """Salva uma página de resultados em JSONL."""
    dir_out = BASE_DIR / tribunal / classe.replace(" ", "_")
    dir_out.mkdir(parents=True, exist_ok=True)

    arquivo = dir_out / f"pagina_{pagina:04d}.jsonl"
    with open(arquivo, "w", encoding="utf-8") as f:
        for processo in dados:
            f.write(json.dumps(processo, ensure_ascii=False) + "\n")

    return arquivo


def coletar_tribunal_classe(
    session: requests.Session,
    tribunal: str,
    classe_codigo: int,
    classe_nome: str,
):
    """Coleta todos os processos de um tribunal+classe, paginando."""
    log(f"Iniciando: [{tribunal.upper()}] {classe_nome} (código {classe_codigo})")

    total_coletado = 0
    pagina = 1

    while pagina <= MAX_PAGES:
        resp = buscar_processos(session, tribunal, classe_codigo=classe_codigo, pagina=pagina)
        hits = resp.get("hits", {})
        total_geral = hits.get("total", {}).get("value", 0)
        registros = hits.get("hits", [])

        if not registros:
            break

        dados = [r.get("_source", {}) for r in registros]
        arquivo = salvar_pagina(dados, tribunal, classe_nome, pagina)
        total_coletado += len(dados)

        log(
            f"  [{tribunal.upper()}] {classe_nome} | "
            f"pág {pagina} | {total_coletado}/{total_geral} registros"
        )

        if total_coletado >= total_geral:
            break

        pagina += 1
        time.sleep(SLEEP_BETWEEN)

    log(f"  Concluído: {total_coletado} processos salvos para {tribunal}/{classe_nome}")
    return total_coletado


def consolidar_jsonl(tribunal: str):
    """Une todos os JSONL de um tribunal em um único arquivo."""
    dir_tribunal = BASE_DIR / tribunal
    if not dir_tribunal.exists():
        return

    arquivo_final = BASE_DIR / f"{tribunal}_completo.jsonl"
    count = 0

    with open(arquivo_final, "w", encoding="utf-8") as fout:
        for jsonl in sorted(dir_tribunal.rglob("*.jsonl")):
            with open(jsonl, "r", encoding="utf-8") as fin:
                for linha in fin:
                    fout.write(linha)
                    count += 1

    log(f"Consolidado: {arquivo_final} ({count} processos)")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Download de metadados processuais via DataJud API (CNJ)"
    )
    parser.add_argument(
        "--api-key",
        required=True,
        help="Chave de API do DataJud (obtenha em https://datajud-wiki.cnj.jus.br/api-publica/acesso)",
    )
    parser.add_argument(
        "--tribunais",
        nargs="+",
        default=TRIBUNAIS,
        help=f"Tribunais a consultar. Padrão: {' '.join(TRIBUNAIS)}",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        type=int,
        default=list(CLASSES_ALVO.keys()),
        help="Códigos de classe processual a filtrar (Tabela CNJ)",
    )
    parser.add_argument(
        "--consolidar",
        action="store_true",
        help="Após o download, une os JSONL por tribunal em um arquivo único",
    )
    parser.add_argument(
        "--apenas-consolidar",
        action="store_true",
        help="Pula o download e apenas consolida os arquivos já baixados",
    )
    args = parser.parse_args()

    BASE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    log("=" * 60)
    log("  DOWNLOAD DATAJUD — METADADOS PROCESSUAIS")
    log(f"  Período: {DATAS['inicio']} → {DATAS['fim']}")
    log(f"  Tribunais: {', '.join(args.tribunais)}")
    log(f"  Classes: {len(args.classes)} tipos processuais")
    log(f"  Destino: {BASE_DIR}")
    log("=" * 60)

    if args.apenas_consolidar:
        for tribunal in args.tribunais:
            consolidar_jsonl(tribunal)
        return

    session = setup_session(args.api_key)

    # Teste de conectividade
    log("Verificando conectividade com a API DataJud...")
    resp_teste = buscar_processos(session, args.tribunais[0], pagina=1)
    if not resp_teste:
        log("Falha na conexão. Verifique sua API key e conectividade.", "ERROR")
        log("Documentação: https://datajud-wiki.cnj.jus.br/api-publica/acesso", "ERROR")
        sys.exit(1)
    log("Conectividade OK.")

    total_geral = 0
    for tribunal in args.tribunais:
        log(f"\n{'─'*40}")
        log(f"Tribunal: {tribunal.upper()}")
        for codigo in args.classes:
            nome = CLASSES_ALVO.get(codigo, f"Classe_{codigo}")
            try:
                n = coletar_tribunal_classe(session, tribunal, codigo, nome)
                total_geral += n
            except KeyboardInterrupt:
                log("Interrompido pelo usuário.", "WARN")
                sys.exit(0)
            except Exception as e:
                log(f"Erro inesperado em {tribunal}/{nome}: {e}", "ERROR")

        if args.consolidar:
            consolidar_jsonl(tribunal)

    log("\n" + "=" * 60)
    log(f"  TOTAL COLETADO: {total_geral} processos")
    log(f"  Log: {LOG_FILE}")
    log("=" * 60)


if __name__ == "__main__":
    main()
