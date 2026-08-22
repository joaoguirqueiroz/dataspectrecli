# Nuclei Scan

Modulo interno para executar Nuclei somente em alvos autorizados, com perfis seguros,
limites configuraveis, parsing JSONL, historico e relatorios integrados.

## Perfis

- `basic`: `nuclei -u TARGET`.
- `medium-high`: `nuclei -u TARGET -severity medium,high`.
- `high`: `nuclei -u TARGET -severity high`.
- `critical`: `nuclei -u TARGET -severity critical`.
- `template`: `nuclei -u TARGET -t CAMINHO_DO_TEMPLATE`.
- lista de alvos: `nuclei -l targets.txt`.
- `custom`: templates, tags e severidades controladas.

## Uso

```bash
python main.py scan nuclei http://localhost --authorize
python main.py scan nuclei http://localhost --profile high --authorize --extra-confirm
python main.py scan nuclei http://localhost --profile template --template exposures/ --authorize --extra-confirm
python main.py scan nuclei --target-file targets.txt --authorize
python main.py scan nuclei http://localhost --authorize --simulate
```

Sem `--authorize`, o modulo cancela a execucao. Perfis `high`, `critical`, `template` e `custom` exigem `--extra-confirm`. Quando o Nuclei nao estiver instalado, `--simulate` gera dados ficticios claramente marcados.

## Relatorios

```text
reports/nuclei/
```
