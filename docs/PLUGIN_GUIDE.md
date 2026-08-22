# Plugin Guide

Plugins sao extensoes opcionais carregadas a partir de `plugins/`.

## Manifesto minimo

```json
{
  "enabled": true,
  "entrypoint": "plugin.py",
  "class_name": "PLUGIN_CLASS",
  "metadata": {
    "id": "example_plugin",
    "name": "Example Plugin",
    "version": "1.0.0",
    "author": "DataSpectre",
    "description": "Reference plugin",
    "category": "reference",
    "min_app_version": "1.0.0",
    "dependencies": [],
    "components": []
  }
}
```

## Ciclo de vida

1. Descoberta.
2. Validacao.
3. Registro.
4. Inicializacao.
5. Uso.
6. Encerramento.

Falhas em plugins sao isoladas e registradas nos logs.

