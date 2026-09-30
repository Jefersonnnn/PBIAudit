# Início rápido

Use este guia para coletar os dados mínimos e gerar uma primeira auditoria.

## 1. Preparar o ambiente

```bash
git clone https://github.com/Jefersonnnn/PBIAudit.git
cd PBIAudit
poetry install
cp .env.example .env
```

Informe no `.env` a conexão PostgreSQL e as credenciais do service principal. Consulte o [guia de configuração](docs/CONFIG.md) para os requisitos de permissão.

## 2. Criar as tabelas

```bash
poetry run alembic upgrade head
```

## 3. Sincronizar os dados

```bash
poetry run pbi-governance sync-workspaces
poetry run pbi-governance sync-licenses
poetry run pbi-governance sync-activity-events 7
poetry run pbi-governance sync-usage-metrics
```

`sync-activity-events` aceita de 1 a 28 dias e coleta apenas visualizações de relatórios e dashboards.

## 4. Gerar a auditoria

```bash
poetry run pbi-governance license-report --inactive-days 30
poetry run pbi-governance export-report --output relatorio.html
```

Use `poetry run pbi-governance --help` para a lista completa de comandos.
