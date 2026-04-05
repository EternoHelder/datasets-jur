# Integração com o Dify — Guia Completo

Este guia explica como importar a documentação e os dados deste repositório
como **fonte de conhecimento (Knowledge Base)** no
[Dify](https://dify.ai/) — uma plataforma open-source para construção de
aplicações LLM com suporte a RAG.

---

## O que é o Dify?

O Dify é uma plataforma que permite criar aplicações baseadas em LLM
(chatbots, assistentes, pipelines de RAG) usando uma interface visual.
Ele suporta a criação de **bases de conhecimento** (Knowledge Bases) que
alimentam as respostas do modelo com dados especializados — ideal para o
domínio jurídico.

**Por que usar o Dify com este repositório?**

- Os acórdãos, metadados e corpora acadêmicos são indexados
  automaticamente pelo Dify
- O Dify faz chunking, embedding e armazenamento vetorial dos documentos
- Você pode criar um chatbot jurídico com RAG em minutos

---

## Pré-requisitos

1. **Instância do Dify** — rodando localmente (Docker) ou na nuvem
2. **API Key do Dify** — obtida nas configurações da instância
3. **Python 3.8+** com `requests` e `tqdm` instalados
4. **Dados coletados** — execute primeiro os scripts de download

### Instalar o Dify localmente (Docker)

```bash
git clone https://github.com/langgenius/dify.git
cd dify/docker
cp .env.example .env
docker compose up -d
```

Acesse `http://localhost` e crie uma conta de administrador.

### Obter a API Key do Dify

1. Acesse **Configurações → API Keys** no painel do Dify
2. Crie uma nova chave de API do tipo **Dataset**
3. Copie a chave gerada

---

## Uso rápido

### Enviar apenas a documentação (README + docs/)

```bash
python3 scripts/upload_to_dify.py \
    --api-key SUA_CHAVE_DIFY \
    --base-url http://localhost/v1 \
    --apenas-docs
```

### Enviar documentação + dados coletados

```bash
# Primeiro, colete os dados
./scripts/download_stj_academicos.sh
python3 scripts/download_datajud.py --api-key SUA_CHAVE_DATAJUD

# Depois, envie tudo para o Dify
python3 scripts/upload_to_dify.py \
    --api-key SUA_CHAVE_DIFY \
    --base-url http://localhost/v1
```

### Enviar apenas dados específicos

```bash
# Apenas JSONs e CSVs
python3 scripts/upload_to_dify.py \
    --api-key SUA_CHAVE_DIFY \
    --tipos .json .csv

# Apenas JSONL (DataJud)
python3 scripts/upload_to_dify.py \
    --api-key SUA_CHAVE_DIFY \
    --apenas-dados --tipos .jsonl
```

### Verificar arquivos antes de enviar (dry-run)

```bash
python3 scripts/upload_to_dify.py \
    --api-key SUA_CHAVE_DIFY \
    --dry-run
```

---

## Variáveis de ambiente

Em vez de passar flags na linha de comando, você pode definir:

```bash
export DIFY_API_KEY="sua-chave-aqui"
export DIFY_BASE_URL="http://localhost/v1"

# Agora basta:
python3 scripts/upload_to_dify.py --apenas-docs
```

---

## Opções do script

| Flag               | Descrição                                               |
| ------------------ | ------------------------------------------------------- |
| `--api-key`        | Chave de API do Dify (ou `DIFY_API_KEY`)                |
| `--base-url`       | URL base da API Dify (ou `DIFY_BASE_URL`)               |
| `--dataset-id`     | ID de dataset existente (reutilizar em vez de criar)    |
| `--apenas-docs`    | Envia apenas README.md e arquivos em `docs/`            |
| `--apenas-dados`   | Envia apenas os arquivos de dados coletados             |
| `--tipos`          | Filtra extensões de dados (ex: `.json .csv`)            |
| `--dry-run`        | Lista arquivos sem enviar                               |

---

## Como funciona internamente

```
scripts/upload_to_dify.py
        │
        ├── 1. Coleta arquivos do repositório (docs/ + README.md)
        ├── 2. Coleta dados em ~/dados_juridicos/ (JSON, JSONL, CSV)
        ├── 3. Cria (ou reutiliza) um dataset no Dify via API
        └── 4. Envia cada arquivo via POST /datasets/{id}/document/create-by-file
                │
                ▼
          Dify processa automaticamente:
            • Segmentação (chunking) do texto
            • Geração de embeddings
            • Indexação vetorial
                │
                ▼
          Pronto para uso em aplicações RAG
```

---

## Após o upload

No painel do Dify você pode:

1. **Verificar o dataset** em **Knowledge → Datasets**
2. **Criar um chatbot** que usa o dataset como contexto
3. **Ajustar a segmentação** (tamanho dos chunks, overlap)
4. **Configurar o modelo de embedding** (recomendamos um modelo multilíngue
   ou jurídico como `rufimelo/Legal-BERTimbau-sts-large-ma-v3`)

---

## Solução de problemas

| Problema | Solução |
|----------|---------|
| `401 Unauthorized` | Verifique a API key do Dify |
| `413 Request Entity Too Large` | Arquivo > 15 MB — use dados menores ou ajuste `MAX_FILE_SIZE` |
| `Nenhum arquivo encontrado` | Execute os scripts de download primeiro |
| `Conexão recusada` | Verifique se o Dify está rodando e a URL está correta |
| Extensão não suportada | O script aceita: `.md`, `.txt`, `.json`, `.jsonl`, `.csv`, `.pdf` |

---

## Referências

- [Dify — Documentação oficial](https://docs.dify.ai/)
- [Dify — API de Knowledge Base](https://docs.dify.ai/guides/knowledge-base/maintain-dataset-via-api)
- [Dify — GitHub](https://github.com/langgenius/dify)
