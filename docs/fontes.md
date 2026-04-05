# Fontes de Dados — Detalhamento

## 1. STJ — Portal de Dados Abertos

**URL:** https://dadosabertos.web.stj.jus.br/dataset/  
**Tecnologia:** CKAN (API REST)  
**Formatos:** JSON, CSV, ZIP  
**Atualização:** Mensal (espelhos) / Periódica (precedentes)

### Datasets utilizados

#### 1.1 Espelhos de Acórdãos

Acórdãos selecionados por cada Seção/Turma cuja ementa traz novidade ou relevância de tese jurídica.

| Dataset CKAN | Slug | Competência |
|-------------|------|-------------|
| Espelhos — 2ª Seção | `espelhos-de-acordaos-segunda-secao` | Direito Privado |
| Espelhos — 3ª Turma | `espelhos-de-acordaos-terceira-turma` | Direito Civil, Família, Processo Civil |
| Espelhos — 4ª Turma | `espelhos-de-acordaos-quarta-turma` | Direito Civil, Consumidor, Contratos |

**Estrutura dos arquivos JSON mensais:**

Cada arquivo `YYYYMMDD.json` é uma lista de objetos com os seguintes campos (conforme dicionário oficial):

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id_documento` | string | Identificador único do acórdão |
| `numero_registro` | string | Número de registro interno |
| `numero_processo` | string | Número do processo (ex: REsp 1234567/MG) |
| `classe` | string | Classe processual (REsp, AgInt, HC...) |
| `orgao_julgador` | string | Turma ou Seção julgadora |
| `relator` | string | Nome do Ministro relator |
| `data_julgamento` | date | Data do julgamento |
| `data_publicacao` | date | Data de publicação no DJe |
| `ementa` | string | Texto da ementa do acórdão |
| `ramo_direito` | string | Área do direito (CIVIL, PROCESSUAL CIVIL...) |
| `assunto` | string | Assunto(s) CNJ do processo |
| `situacao` | string | Situação do acórdão |

**Nomenclatura dos arquivos:**
- `YYYYMMDD.zip` — arquivo histórico acumulado até a data indicada
- `YYYYMMDD.json` — acórdãos do mês de referência (último dia do mês)
- `dicionario-espelhodoacordao.csv` — dicionário de dados oficial

#### 1.2 Precedentes Qualificados

Recursos Repetitivos, IACs (Incidente de Assunção de Competência) e outros precedentes vinculantes.

**Arquivos:**

| Arquivo | Descrição |
|---------|-----------|
| `temas.csv` | Teses jurídicas dos precedentes com situação e ramo |
| `processos.csv` | Processos vinculados a cada tema, com tribunal de origem |
| `dicionario-temas.csv` | Dicionário de dados dos temas |
| `dicionario-processos.csv` | Dicionário de dados dos processos |

---

## 2. DataJud — API Pública CNJ

**URL base:** `https://api-publica.datajud.cnj.jus.br`  
**Tecnologia:** Elasticsearch (query DSL via POST)  
**Formato:** JSON (JSONL no armazenamento)  
**Base legal:** Resolução CNJ 331/2020 · Portaria 160/2020

### Campos retornados por processo

| Campo | Descrição |
|-------|-----------|
| `numeroProcesso` | Número CNJ do processo |
| `classe.codigo` | Código da classe processual (Tabela CNJ) |
| `classe.nome` | Nome da classe |
| `assuntos[]` | Lista de assuntos com código e nome |
| `orgaoJulgador` | Órgão julgador |
| `tribunal` | Sigla do tribunal |
| `grau` | Grau de jurisdição (G1, G2, JE...) |
| `dataAjuizamento` | Data de ajuizamento |
| `dataHoraUltimaAtualizacao` | Última movimentação |
| `movimentos[]` | Histórico de movimentações processuais |

### Endpoint por tribunal

```
POST https://api-publica.datajud.cnj.jus.br/api_publica_{sigla_tribunal}/_search
Authorization: ApiKey {sua_chave}
Content-Type: application/json
```

### Limitações

- Não entrega texto integral de sentenças ou acórdãos
- Processos em segredo de justiça são filtrados automaticamente
- Rate limit: respeitar intervalo entre requisições (configurado como 1.5s no script)
- Máximo de 10.000 resultados por query (paginação necessária para volumes maiores)

---

## 3. RulingBR

**URL:** https://github.com/diego-feijo/rulingbr  
**Formato:** JSONL (`rulingbr-v1.2.tar.xz`)  
**Período:** 2011–2018  
**Tribunal:** STF (Supremo Tribunal Federal)  
**Volume:** ~10 mil decisões

### Campos disponíveis

| Campo | Descrição |
|-------|-----------|
| `ementa` | Texto da ementa |
| `acordao` | Texto integral do acórdão |
| `relatorio` | Relatório do processo |
| `voto` | Voto do relator |
| `relator` | Ministro relator |
| `classe` | Classe processual (ADI, RE, HC...) |
| `extrato` | Extrato da ata de julgamento |
| `area` | Área do direito (CIVIL, CONSTITUCIONAL, TRABALHISTA...) |

> O campo `area` permite filtrar diretamente por ramo jurídico, facilitando a seleção de decisões relevantes para RAG cível/processual.

---

## 4. Brazilian Court Decisions

**URL:** https://huggingface.co/datasets/joelniklaus/brazilian_court_decisions  
**Formato:** Parquet (splits: train/validation/test)  
**Período:** 2018–2019  
**Tribunal:** TJAL (Tribunal de Justiça de Alagoas)  
**Volume:** ~4 mil decisões

### Campos disponíveis

| Campo | Descrição |
|-------|-----------|
| `process_number` | Número do processo |
| `organ` | Órgão julgador |
| `date` | Data de publicação |
| `judge` | Juiz/relator |
| `summary` | Ementa |
| `decision_description` | Dispositivo da decisão |
| `judgment_text` | Texto do julgamento |
| `label_binary` | Rótulo binário (procedente/improcedente) |
| `label_ternary` | Rótulo ternário (procedente/parcial/improcedente) |
| `unanimity` | Unanimidade da decisão |

---

## 5. JurisTCU

**URL:** https://huggingface.co/datasets/LeandroRibeiro/JurisTCU  
**Formato:** Parquet (splits: train/test)  
**Tribunal:** TCU (Tribunal de Contas da União)  
**Volume:** ~16 mil decisões  
**Uso principal:** Legal Information Retrieval (IR/busca semântica)

> Embora focado em controle externo e gestão fiscal, é útil para benchmarking de modelos de busca jurídica em português.
