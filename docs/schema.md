# Esquema dos Dados — Referência de Campos

## STJ — Espelhos de Acórdãos (JSON mensal)

```json
[
  {
    "id_documento": "string",
    "numero_registro": "string",
    "numero_processo": "string",
    "classe": "string",
    "orgao_julgador": "string",
    "relator": "string",
    "data_julgamento": "YYYY-MM-DD",
    "data_publicacao": "YYYY-MM-DD",
    "ementa": "string (texto completo)",
    "ramo_direito": "string",
    "assunto": "string",
    "situacao": "string"
  }
]
```

**Valores observados em `ramo_direito`:**
- `DIREITO CIVIL`
- `DIREITO PROCESSUAL CIVIL E DO TRABALHO`
- `DIREITO DO CONSUMIDOR`
- `DIREITO DE FAMÍLIA`
- `DIREITO CONSTITUCIONAL`
- `DIREITO PENAL`
- `DIREITO TRIBUTÁRIO`
- `DIREITO ADMINISTRATIVO E OUTRAS MATÉRIAS DE DIREITO PÚBLICO`

---

## STJ — Precedentes Qualificados

### temas.csv

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id_tema` | int | Identificador do tema |
| `descricao_tema` | string | Tese jurídica do precedente |
| `tipo` | string | REPETITIVO / IAC / RECURSO ESPECIAL PARADIGMA |
| `situacao` | string | Afetado / Julgado / Suspenso |
| `ramo_direito` | string | Área do direito |
| `data_afetacao` | date | Data de afetação do tema |
| `data_julgamento` | date | Data do julgamento |

### processos.csv

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id_tema` | int | Referência ao tema (join com temas.csv) |
| `numero_processo` | string | Número do processo paradigma |
| `tribunal_origem` | string | Tribunal de onde veio o processo |
| `tipo_processo` | string | Paradigma / Sobrestado |
| `situacao` | string | Situação atual do processo |

---

## DataJud — Metadados Processuais (JSONL)

```jsonl
{"id": "...", "numeroProcesso": "0123456-78.2022.8.13.0000", "classe": {"codigo": 7, "nome": "Procedimento Comum"}, "sistema": {"codigo": 1, "nome": "PJe"}, "formato": {"codigo": 1, "nome": "Eletrônico"}, "tribunal": "TJMG", "dataHoraUltimaAtualizacao": "2024-03-15T10:30:00.000Z", "grau": "G1", "dataAjuizamento": "2022-06-01T00:00:00.000Z", "movimentos": [{"codigo": 26, "nome": "Distribuído", "dataHora": "2022-06-01T14:00:00.000Z", "complementosTabelados": [], "complemento": ""}], "assuntos": [{"codigo": 7780, "nome": "Dano Moral"}], "orgaoJulgador": {"codigo": 1, "nome": "1ª Vara Cível", "municipio": {"codigo": 3132, "nome": "Uberlândia"}}}
```

**Campos principais:**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `numeroProcesso` | string | Número CNJ (NNNNNNN-DD.AAAA.J.TT.OOOO) |
| `classe.codigo` | int | Código CNJ da classe processual |
| `classe.nome` | string | Nome da classe |
| `assuntos[].codigo` | int | Código CNJ do assunto |
| `assuntos[].nome` | string | Nome do assunto |
| `tribunal` | string | Sigla do tribunal (ex: TJMG) |
| `grau` | string | G1 (1º grau), G2 (2º grau), JE (juizado), SUP (superior) |
| `dataAjuizamento` | ISO 8601 | Data de ajuizamento |
| `orgaoJulgador.nome` | string | Vara/câmara julgadora |
| `orgaoJulgador.municipio.nome` | string | Município da vara |
| `movimentos[]` | array | Histórico de movimentações (código + data) |

---

## RulingBR (JSONL)

```jsonl
{"ementa": "...", "acordao": "...", "relatorio": "...", "voto": "...", "relator": "MINISTRO NOME", "classe": "ADI", "extrato": "...", "area": "CONSTITUCIONAL"}
```

**Valores de `area` relevantes para o recorte temático:**
- `CIVIL`
- `PROCESSUAL CIVIL`
- `CONSUMIDOR`
- `FAMÍLIA`

---

## Brazilian Court Decisions (Parquet)

```
process_number  | string
organ           | string
date            | string (YYYY-MM-DD)
judge           | string
summary         | string
decision_description | string
judgment_text   | string
label_binary    | int   (0=não provido, 1=provido)
label_ternary   | int   (0=não provido, 1=parcial, 2=provido)
unanimity       | string (unanime / não-unanime / não-informado)
```

---

## JurisTCU (Parquet)

```
id              | string
text            | string  (texto da decisão)
label           | string  (categoria da decisão TCU)
```
