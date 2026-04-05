# datasets-jur

Pipeline de coleta e organização de dados jurídicos brasileiros em formato estruturado, voltado à construção de sistemas RAG, classificação de documentos e análise semântica de jurisprudência.

**Recorte temático:** Direito Civil · Família · Consumidor · Processo Civil · Indenizações cíveis e de consumo  
**Recorte temporal:** Janeiro/2020 → Março/2026  
**Fontes:** STJ Dados Abertos · DataJud/CNJ · Corpora Acadêmicos (HuggingFace · GitHub)

---

## Estrutura do repositório

```
datasets-jur/
├── scripts/
│   ├── download_stj_academicos.sh   # Download STJ + corpora acadêmicos
│   ├── download_datajud.py          # Coleta via API pública DataJud/CNJ
│   ├── retentar_falhas.sh           # Reprocessa downloads com falha
│   └── upload_to_dify.py            # Envia docs/dados como fonte no Dify
├── docs/
│   ├── fontes.md                    # Detalhamento de cada fonte de dados
│   ├── schema.md                    # Esquema dos campos por dataset
│   ├── datajud_classes.md           # Tabela de classes e assuntos CNJ utilizados
│   └── dify_integracao.md           # Guia de integração com o Dify (RAG)
├── dados/
│   ├── stj/
│   │   ├── espelhos/                # Acórdãos mensais por turma (JSON)
│   │   └── precedentes_qualificados/# Recursos Repetitivos e IACs (CSV)
│   ├── datajud/                     # Metadados processuais por tribunal (JSONL)
│   └── academico/
│       ├── rulingbr/                # STF 2011–2018 (JSONL)
│       ├── brazilian_court_decisions/# TJAL 2018–2019 (Parquet)
│       └── juristcu/                # TCU jurisprudência (Parquet)
└── README.md
```

> **Nota:** A pasta `dados/` está no `.gitignore`. Os arquivos de dados não são versionados — apenas os scripts e a documentação. Execute os scripts localmente para popular as pastas.

---

## Início rápido

### 1. Pré-requisitos

```bash
# Debian/Ubuntu/Xubuntu
sudo apt update && sudo apt install -y curl wget python3 python3-pip git

# Dependências Python
pip3 install requests tqdm datasets
```

### 2. Clonar o repositório

```bash
git clone https://github.com/EternoHelder/datasets-jur.git
cd datasets-jur
chmod +x scripts/*.sh
```

### 3. Download STJ + Corpora Acadêmicos

Não requer credenciais. Baixa diretamente dos portais públicos.

```bash
./scripts/download_stj_academicos.sh
```

O script cria automaticamente a pasta `~/dados_juridicos/` e organiza tudo lá.

### 4. Download DataJud (API CNJ)

Requer API key gratuita. Veja [como obter](#obtendo-a-api-key-do-datajud).

```bash
python3 scripts/download_datajud.py --api-key SUA_CHAVE_AQUI
```

---

## Fontes de dados

### STJ — Portal de Dados Abertos

| Dataset | Turmas cobertas | Formato | Período |
|---------|----------------|---------|---------|
| Espelhos de Acórdãos | 2ª Seção, 3ª Turma, 4ª Turma | JSON mensal + ZIP histórico | mai/2022 → atual |
| Precedentes Qualificados | Todas | CSV | Estático (atualizado periodicamente) |

**Turmas selecionadas e sua competência:**
- **2ª Seção** — Direito Privado em geral (Direito Civil, Família, Consumidor)
- **3ª Turma** — Direito Civil, Família, Processo Civil
- **4ª Turma** — Direito Civil, Consumidor, Contratos, Indenizações

Portal: [dadosabertos.web.stj.jus.br](https://dadosabertos.web.stj.jus.br/dataset/)

> **Cobertura 2020–2022:** Os JSONs mensais iniciam em maio/2022. Para o período anterior, o ZIP histórico de cada turma contém os acórdãos acumulados. Após extração, filtre pelo campo `data_publicacao`.

---

### DataJud — API Pública CNJ

Metadados processuais de todos os ramos da Justiça (TJ, TRF, TRT, STJ etc.), via Elasticsearch.

**Tribunais configurados por padrão:**

| Sigla | Tribunal |
|-------|---------|
| `tjmg` | Tribunal de Justiça de Minas Gerais |
| `tjsp` | Tribunal de Justiça de São Paulo |
| `tjgo` | Tribunal de Justiça de Goiás |
| `tjdf` | Tribunal de Justiça do Distrito Federal |
| `tjrj` | Tribunal de Justiça do Rio de Janeiro |
| `stj` | Superior Tribunal de Justiça |

**Classes processuais cobertas (código CNJ):**

| Código | Classe |
|--------|--------|
| 7 | Procedimento Comum |
| 436 | Procedimento do Juizado Especial Cível |
| 281 | Ação de Indenização por Dano Moral |
| 283 | Ação de Indenização por Dano Moral e Material |
| 275 | Ação de Reparação de Danos |
| 40 | Embargos à Execução |
| 156 | Cumprimento de Sentença |
| 198 | Ação de Alimentos |
| 14007 | Divórcio Consensual |
| 14008 | Divórcio Litigioso |
| 864 | Guarda e Responsabilidade |

Documentação da API: [datajud-wiki.cnj.jus.br](https://datajud-wiki.cnj.jus.br)

#### Obtendo a API Key do DataJud

1. Acesse [datajud-wiki.cnj.jus.br/api-publica/acesso](https://datajud-wiki.cnj.jus.br/api-publica/acesso)
2. Cadastre-se como desenvolvedor (gratuito)
3. Aguarde o e-mail com a chave (1–2 dias úteis)

---

### Corpora Acadêmicos

| Dataset | Fonte | Conteúdo | Período | Formato |
|---------|-------|----------|---------|---------|
| RulingBR | [GitHub](https://github.com/diego-feijo/rulingbr) | ~10 mil decisões do STF com ementa, acórdão, voto, relator e área | 2011–2018 | JSONL |
| Brazilian Court Decisions | [HuggingFace](https://huggingface.co/datasets/joelniklaus/brazilian_court_decisions) | ~4 mil decisões do TJAL com rótulos de julgamento | 2018–2019 | Parquet |
| JurisTCU | [HuggingFace](https://huggingface.co/datasets/LeandroRibeiro/JurisTCU) | ~16 mil decisões do TCU para Legal IR | variado | Parquet |

> Os corpora acadêmicos têm cobertura anterior a 2020, mas são valiosos como base de treino/referência para modelos de classificação e embeddings jurídicos.

---

## Uso avançado

### Filtrar tribunais e classes no DataJud

```bash
# Apenas TJMG e STJ, classes de indenização
python3 scripts/download_datajud.py \
    --api-key SUA_CHAVE \
    --tribunais tjmg stj \
    --classes 281 283 275 156

# Baixar e já consolidar em arquivo único por tribunal
python3 scripts/download_datajud.py \
    --api-key SUA_CHAVE \
    --consolidar
```

### Retentar downloads com falha

```bash
./scripts/retentar_falhas.sh
```

### Verificar integridade dos JSONs

```python
import json, glob

for f in glob.glob('dados/stj/espelhos/**/*.json', recursive=True):
    with open(f) as fh:
        try:
            data = json.load(fh)
            print(f"OK: {f} — {len(data)} registros")
        except json.JSONDecodeError as e:
            print(f"ERRO: {f} — {e}")
```

---

## Integração com o Dify (Knowledge Base)

O [Dify](https://dify.ai/) é uma plataforma open-source para construção de
aplicações LLM com suporte a RAG. Este repositório inclui um script para
enviar automaticamente a documentação e os dados coletados como base de
conhecimento no Dify.

### Pré-requisitos Dify

```bash
# Instalar o Dify localmente (Docker)
git clone https://github.com/langgenius/dify.git
cd dify/docker && cp .env.example .env && docker compose up -d
# Acesse http://localhost e crie uma conta
```

Obtenha a API Key em **Configurações → API Keys** (tipo Dataset).

### Enviar documentação para o Dify

```bash
# Apenas a documentação do repositório (README + docs/)
python3 scripts/upload_to_dify.py \
    --api-key SUA_CHAVE_DIFY \
    --base-url http://localhost/v1 \
    --apenas-docs
```

### Enviar dados coletados + documentação

```bash
# Primeiro colete os dados, depois envie tudo
python3 scripts/upload_to_dify.py \
    --api-key SUA_CHAVE_DIFY \
    --base-url http://localhost/v1
```

### Verificar antes de enviar (dry-run)

```bash
python3 scripts/upload_to_dify.py --api-key SUA_CHAVE_DIFY --dry-run
```

> Para o guia completo, veja [`docs/dify_integracao.md`](docs/dify_integracao.md).

---

## Próximos passos: pipeline RAG

Após o download, o fluxo sugerido para indexação:

```
dados/stj/espelhos/*.json
        │
        ▼
  Limpeza + Chunking (~512 tokens por chunk)
        │
        ▼
  Embeddings: rufimelo/Legal-BERTimbau-sts-large-ma-v3
        │
        ▼
  Vector DB: Chroma / Pinecone
        │
        ▼
  RAG com recuperação por similaridade + LLM
```

---

## Logs e monitoramento

| Arquivo | Conteúdo |
|---------|---------|
| `~/dados_juridicos/download.log` | Log completo do download STJ/acadêmicos |
| `~/dados_juridicos/datajud_download.log` | Log do DataJud por tribunal/classe |
| `~/dados_juridicos/falhas.txt` | URLs que falharam (para retentar) |

---

## Licença

Distribuído sob a licença presente no arquivo [LICENSE](LICENSE).  
Os dados coletados estão sujeitos às licenças e termos de uso de cada fonte original (STJ, CNJ, HuggingFace).
