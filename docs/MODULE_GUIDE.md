# Module Guide

Modulos sao unidades funcionais independentes carregadas por `ModuleManager`.

## Contrato

Cada modulo deve:

- herdar de `BaseModule`;
- expor `metadata`;
- implementar `execute`;
- validar parametros relevantes;
- retornar `ModuleResult`;
- exportar `MODULE_CLASS`.

## Estados

- `loaded`
- `ready`
- `running`
- `completed`
- `error`
- `finalized`

## Modulos incluidos

- `asset_inventory`: normaliza inventarios autorizados.
- `system_health`: exibe saude do runtime.
- `project_summary`: resume projetos e sessoes.

