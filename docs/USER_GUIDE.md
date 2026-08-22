# User Guide

## Verificar status

```bash
python main.py status
```

## Abrir ajuda e menu interativo

```bash
python main.py help
python main.py interactive
```

No menu interativo, use `0` para sair corretamente e visualizar o relatorio final da sessao.

No menu `Configuracoes`, use:

- `Verificar ambiente` para checar Python, pip, Git, estrutura do projeto, dependencias, Nmap e Nuclei.
- `Instalador assistido` para abrir o fluxo guiado com confirmacao antes de qualquer instalacao.
- `Verificar Nmap/Nuclei` para revisar somente as ferramentas externas.

## Instalador assistido

```bash
python scripts/setup_wizard.py
python scripts/setup_wizard.py --check-only
python main.py setup check
python main.py setup tools
python main.py setup wizard
```

O assistente nao executa scans. Ele verifica `nmap --version` e `nuclei -version`, detecta `apt`, `dnf`, `pacman` ou `yay`, valida dependencias Python e gera:

```text
reports/setup/setup_report.txt
reports/setup/setup_report.json
```

## Criar projeto

```bash
python main.py projects create "Meu Projeto" --description "Auditoria autorizada"
```

## Iniciar sessao

```bash
python main.py sessions start <project_id>
```

## Executar modulo

```bash
python main.py modules list
python main.py modules run system_health --report
python main.py modules run system_health --report --report-format html
python main.py modules run asset_inventory --param input_file=examples/assets.json --report --report-format csv
```

## Executar analises autorizadas com Nmap e Nuclei

```bash
python main.py scan nmap 127.0.0.1 --authorize
python main.py scan nmap 127.0.0.1 --profile rapida --authorize
python main.py scan nmap 127.0.0.1 --profile servicos --authorize
python main.py scan nmap 127.0.0.1 --profile scripts-padrao --authorize
python main.py scan nmap 127.0.0.1 --profile servicos-scripts --authorize
python main.py scan nmap 127.0.0.1 --profile portas --ports 80,443 --authorize
python main.py scan nuclei http://localhost --authorize
python main.py scan nuclei http://localhost --profile medium-high --authorize
python main.py scan nuclei http://localhost --profile high --authorize --extra-confirm
python main.py scan nuclei http://localhost --profile critical --authorize --extra-confirm
python main.py scan nuclei http://localhost --profile template --template exposures/ --authorize --extra-confirm
python main.py scan nuclei --target-file targets.txt --authorize
python main.py scan smart 127.0.0.1 --authorize
python main.py scan smart 127.0.0.1 --profile advanced --authorize --extra-confirm
```

Sem `--authorize`, a execucao e cancelada com mensagem clara. Perfis personalizados e de alto impacto exigem `--extra-confirm`.

Quando Nmap ou Nuclei nao estiverem instalados, use `--simulate` para gerar dados ficticios claramente marcados:

```bash
python main.py scan nmap 127.0.0.1 --authorize --simulate
python main.py scan nuclei http://localhost --authorize --simulate
python main.py scan smart 127.0.0.1 --authorize --simulate
```

## Smart scan

O smart scan usa Nmap para identificar portas/servicos, salva TXT/XML, interpreta o XML, seleciona endpoints web relevantes e roda Nuclei apenas nesses endpoints, quando a ferramenta estiver instalada.

```bash
python main.py scan smart 127.0.0.1 --authorize
python main.py scan smart 192.168.1.10 --profile intermediate --authorize
python main.py scan smart 192.168.1.10 --profile custom --ports 80,443 --tag tech --severity high --authorize --extra-confirm
python main.py scan smart 127.0.0.1 --authorize --simulate
```

Os resultados ficam em:

```text
reports/smart_scan/
```

## Baseline defensivo

Crie um baseline a partir de um JSON de scan ou de relatorio:

```bash
python main.py baseline create lab-interno --data resultado-smart.json
```

Compare uma nova execucao:

```bash
python main.py baseline compare lab-interno --data resultado-smart-novo.json
```

O comparativo mostra novos servicos, servicos removidos, mudancas de versao, novos achados, achados resolvidos e achados persistentes.

## Configuracao YAML

Edite `config/dataspectre.yaml` para ajustar timeout, concorrencia, rate limit, maximo de alvos, portas web, tags/severidades/templates do Nuclei, scripts NSE permitidos, baseline e alertas.

Use `config/dataspectre.example.yaml` como referencia.

## Gerar relatorio manual

```bash
python main.py reports generate --title "Resumo" --data "{\"status\":\"ok\"}"
python main.py reports generate --title "Resumo HTML" --format html --data "{\"status\":\"ok\"}"
python main.py reports generate --title "Resumo arquivo" --format json --data-file examples/assets.json
```

Formatos suportados: `markdown`, `txt`, `json`, `csv` e `html`.

No PowerShell, use `--%` quando precisar passar JSON inline com aspas:

```powershell
python --% main.py reports generate --title "Resumo" --format json --data "{\"status\":\"ok\"}"
```

Para uso recorrente, `--data-file` evita diferencas de citacao entre shells.

Relatorios de ferramentas ficam em:

```text
reports/nmap/
reports/nuclei/
reports/smart_scan/
```

## Consultar auditoria

```bash
python main.py logs audit --limit 20
```

## Limpar temporarios com seguranca

```bash
python main.py maintenance clean-temp
python main.py maintenance clean-temp --yes
```

O primeiro comando apenas simula a limpeza. A remocao real exige `--yes` e preserva relatorios, logs, projetos, sessoes e dados persistentes.
