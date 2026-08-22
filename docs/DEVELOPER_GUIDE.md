# Developer Guide

## Ambiente

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements/dev.txt
pytest
```

## Criar modulo

1. Crie `modules/<module_id>/module.py`.
2. Defina uma classe que herde de `BaseModule`.
3. Preencha `ModuleMetadata`.
4. Implemente `validate` quando houver parametros.
5. Implemente `execute`.
6. Exporte `MODULE_CLASS`.
7. Adicione README do modulo e testes.

## Criar plugin

1. Crie `plugins/<plugin_id>/plugin.json`.
2. Preencha metadados completos.
3. Se houver codigo, crie uma classe que herde de `BasePlugin`.
4. Exporte `PLUGIN_CLASS`.
5. Teste descoberta, inicializacao e encerramento.

## Fluxo de contribuicao

1. Planejar a alteracao.
2. Implementar com baixo acoplamento.
3. Atualizar testes.
4. Rodar `pytest`.
5. Atualizar documentacao e `CHANGELOG.md`.

