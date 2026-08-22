# Functional Audit - DataSpectre CLI

## Dados da auditoria

- Data: 2026-07-06
- Revalidacao adicional: 2026-07-07
- Versao do projeto: 1.0.0
- Fonte oficial consultada: `docs/MASTER_PROMPT.md` e `docs/TECHNICAL_SPECIFICATION.md`
- Objetivo: validar o fluxo funcional da CLI, revisar menus, corrigir opcoes sem handler, adicionar instalador assistido, fortalecer testes e confirmar estabilidade com `pytest`.

## Menus testados

- Tela inicial e dashboard.
- Menu principal interativo.
- Network Recon Autorizado (Nmap).
- Web Vulnerability Audit (Nuclei).
- Fluxos guiados defensivos do menu principal.
- Report Center.
- Historico.
- Configuracoes.
- Verificar ambiente.
- Instalador assistido.
- Verificar Nmap/Nuclei.
- Listar modulos.
- Ajuda.
- Limpeza segura de temporarios.
- Encerramento com relatorio final da sessao.

## Funcoes testadas

- Inicializacao da aplicacao.
- Renderizacao de banner, dashboard, ajuda, tabelas, paineis e mensagens.
- Descoberta/listagem de modulos.
- Comandos `scan nmap` e `scan nuclei` em modo cancelado sem autorizacao.
- Validacao e montagem segura de comandos Nmap/Nuclei com mocks.
- Parser de XML Nmap e JSONL Nuclei.
- Geracao de relatorios TXT, JSON, CSV e HTML.
- Historico de acoes.
- Limpeza segura em simulacao e confirmada.
- Gerenciamento de projetos e sessoes via comandos.
- Plugins e logs.
- Instalador assistido via servico, CLI e scripts.
- Relatorios de setup TXT/JSON.
- Entradas invalidas, vazias ou canceladas.

## Problemas encontrados

- Algumas opcoes do menu principal (`4`, `5`, `6`, `7`, `8` e `10`) apareciam no menu, mas caiam como opcao invalida.
- A opcao de limpeza no menu interativo apenas simulava a limpeza e nao tinha confirmacao/cancelamento dentro do fluxo.
- O Report Center interativo abria somente a listagem, sem submenu claro para voltar ou gerar relatorio manual.
- Nao havia instalador assistido para verificar ambiente, Nmap e Nuclei.
- Nao havia relatorio formal de setup em `reports/setup/`.
- Durante os testes, a nova camada de setup tinha referencias antigas a `returncode` em vez do campo normalizado `return_code`.
- Na revalidacao de 2026-07-07, o comando de relatorio manual com JSON inline falhou no PowerShell porque o shell removeu aspas internas do payload.

## Problemas corrigidos

- Todas as opcoes do menu principal agora abrem uma tela funcional, fluxo guiado seguro ou recurso operacional implementado.
- Configuracoes ganhou submenu com `Ver configuracao atual`, `Verificar ambiente`, `Instalador assistido`, `Verificar Nmap/Nuclei` e `Voltar`.
- Limpeza interativa agora mostra aviso, simula, pede confirmacao e permite cancelar sem apagar arquivos.
- Report Center ganhou submenu para listar relatorios, gerar relatorio manual e voltar.
- Instalador assistido criado com verificacao de Python, pip, Git, dependencias, Nmap, Nuclei, gerenciador de pacotes, permissoes, estrutura e entrada da aplicacao.
- Relatorios de setup TXT/JSON criados em `reports/setup/`.
- Testes de setup, scripts e navegacao interativa adicionados.
- Uso interno de `return_code` corrigido em todas as checagens do setup.
- Comando `reports generate` ganhou `--data-file`, testes de regressao e documentacao para evitar falhas de citacao de JSON entre shells.
- Modulos Nmap/Nuclei/Smart Scan ganharam comandos reais, `--simulate`, relatorios em pastas simples e validacao de arquivo de alvos do Nuclei.

## Funcoes que ainda precisam de melhoria

- Evoluir os fluxos guiados de API, TLS, CVE, hardening, logs e OSINT para modulos especializados completos.
- Implementar gerenciador persistente de perfis de scan com criacao, edicao e restauracao de padroes.
- Adicionar um navegador interno de relatorios com filtros por projeto, data, sessao e ferramenta.
- Adicionar verificacao opcional de templates Nuclei com confirmacao para atualizacao/baixar templates.

## Matriz de validacao

| Funcao | Caminho no menu | Status inicial | Problema encontrado | Correcao feita | Status final |
| --- | --- | --- | --- | --- | --- |
| Tela inicial/dashboard | Inicio do modo interativo | OK | Nenhum bloqueador encontrado | Mantida renderizacao com painel, status e aviso etico | OK |
| Nmap | Menu principal > 1 | OK | Exige ferramenta externa para execucao real | Mantido cancelamento seguro sem autorizacao e testes com mocks | OK |
| Nuclei | Menu principal > 2 | OK | Exige ferramenta externa para execucao real | Mantido cancelamento seguro sem autorizacao e testes com mocks | OK |
| API Security Audit | Menu principal > 3 | Parcial | Fluxo especializado ainda ausente | Fluxo guiado seguro para planejamento de auditoria API autorizada | OK |
| SSL/TLS Inspector | Menu principal > 4 | Quebrado | Opcao aparecia, mas caia como invalida | Fluxo guiado seguro para revisao TLS autorizada | OK |
| CVE Intelligence | Menu principal > 5 | Quebrado | Opcao aparecia, mas caia como invalida | Fluxo guiado defensivo para correlacao manual de servico/versao/CVE | OK |
| Linux Hardening Audit | Menu principal > 6 | Quebrado | Opcao aparecia, mas caia como invalida | Fluxo guiado local para checklist de hardening | OK |
| Log Threat Analyzer | Menu principal > 7 | Quebrado | Opcao aparecia, mas caia como invalida | Fluxo guiado para revisao dos logs da propria aplicacao | OK |
| OSINT Tecnico | Menu principal > 8 | Quebrado | Opcao aparecia, mas caia como invalida | Fluxo passivo para organizacao de evidencias fornecidas pelo usuario | OK |
| Report Center | Menu principal > 9 | Parcial | Listagem direta sem submenu de navegacao | Submenu com listar, gerar manual e voltar | OK |
| Relatorio manual por arquivo | `reports generate --data-file` | Ausente | JSON inline era fragil em PowerShell | Adicionado `--data-file` com validacao de arquivo JSON | OK |
| Scan Profile Manager | Menu principal > 10 | Quebrado | Opcao aparecia, mas caia como invalida | Fluxo guiado com perfis ativos e configuracao YAML | OK |
| Historico | Menu principal > 11 | OK | Nenhum bloqueador encontrado | Mantida listagem de eventos recentes | OK |
| Configuracoes | Menu principal > 12 | Parcial | Apenas imprimia JSON da configuracao | Submenu com configuracao, setup e verificacao de ferramentas | OK |
| Verificar ambiente | Configuracoes > 2 | Ausente | Funcao nao existia no menu | Integrado ao `SetupService` e gera relatorio TXT/JSON | OK |
| Instalador assistido | Configuracoes > 3 | Ausente | Funcao nao existia | Fluxo seguro com confirmacao antes de instalar | OK |
| Verificar Nmap/Nuclei | Configuracoes > 4 | Ausente | Funcao nao existia | Verificacao dedicada das ferramentas externas | OK |
| Listar modulos | Menu principal > 13 | OK | Nenhum bloqueador encontrado nesta rodada | Mantida renderizacao dedicada com Nmap/Nuclei | OK |
| Ajuda | Menu principal > 14 | OK | Faltavam comandos do setup | Ajuda atualizada com setup wizard/check/tools | OK |
| Limpeza de temporarios | Menu principal > 15 | Parcial | Simulava sem confirmacao interativa | Fluxo com aviso, preview, confirmacao e cancelamento | OK |
| Sair | Menu principal > 0 | OK | Nenhum bloqueador encontrado | Mantido relatorio final da sessao | OK |
| CLI setup check | `python main.py setup check` | Ausente | Comando nao existia | Comando criado e testado | OK |
| CLI setup tools | `python main.py setup tools` | Ausente | Comando nao existia | Comando criado e testado | OK |
| CLI setup wizard | `python main.py setup wizard` | Ausente | Comando nao existia | Comando criado e testado | OK |
| Script setup wizard | `python scripts/setup_wizard.py` | Ausente | Arquivo nao existia | Script criado com modo assistido e `--check-only` | OK |
| Script check tools | `python scripts/check_tools.py` | Ausente | Arquivo nao existia | Script criado | OK |
| Script install dependencies | `python scripts/install_dependencies.py` | Ausente | Arquivo nao existia | Script criado com confirmacao | OK |
| Script setup report | `python scripts/setup_report.py` | Ausente | Arquivo nao existia | Script criado | OK |

## Comandos usados

```bash
python -B -m pytest -p no:cacheprovider
python -B -m pytest -p no:cacheprovider tests/test_setup_service.py tests/test_cli.py::test_cli_setup_check_generates_setup_reports tests/test_cli.py::test_cli_setup_wizard_check_mode tests/test_cli.py::test_cli_interactive_settings_environment_check
python main.py setup check
python main.py setup tools
python scripts/setup_wizard.py --check-only
python main.py status
python main.py modules list
python main.py reports generate --title "Validacao funcional" --format json --data-file examples/assets.json
```

## Status final

- Auditoria funcional concluida.
- Instalador assistido criado.
- Relatorios de setup criados.
- Menu principal revisado opcao por opcao.
- Submenus principais revisados.
- Testes automatizados ampliados.
- Ultima suite automatizada registrada nesta rodada: `224 passed`.
