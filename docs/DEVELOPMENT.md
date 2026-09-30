# Desenvolvimento

## Ambiente local

```bash
poetry install
cp .env.example .env
poetry run alembic upgrade head
```

## Verificações

```bash
poetry run pytest
poetry run ruff check .
poetry run mypy src
```

Para executar um arquivo de teste:

```bash
poetry run pytest tests/unit/test_services.py
```

## Alterações

1. Crie uma branch a partir de `main`.
2. Atualize ou adicione testes que cubram o comportamento alterado.
3. Execute as verificações aplicáveis.
4. Abra um pull request com o motivo da alteração e como validá-la.

Evite incluir `.env`, logs, exports de relatório ou dados de auditoria nos commits.
