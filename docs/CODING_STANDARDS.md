# Coding Standards

## Linguagem

O projeto usa Python 3.10+.

## Organizacao

- Interfaces publicas ficam em `core/`.
- Regras operacionais ficam em `services/`.
- A camada `cli/` nao deve conter regras de negocio.
- Modulos e plugins devem usar apenas interfaces publicas do nucleo.

## Nomenclatura

- Arquivos e pacotes: `snake_case`.
- Classes: `PascalCase`.
- Funcoes, metodos e variaveis: `snake_case`.
- Constantes: `UPPER_SNAKE_CASE`.

## Erros

Use excecoes especificas de `core.exceptions` para erros esperados. Falhas de modulos e plugins devem ser isoladas e registradas.

## Comentarios

Comentarios devem explicar decisao ou comportamento nao obvio. Evite comentarios que apenas repetem o codigo.

## Persistencia

Use `services.storage.write_json` para escrita atomica de JSON e `append_jsonl` para trilhas append-only.

