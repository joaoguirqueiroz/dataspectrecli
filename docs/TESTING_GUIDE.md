# Testing Guide

## Executar testes

```bash
pytest
```

ou:

```bash
python -m pytest
```

Para evitar caches durante revisoes finais:

```bash
python -B -m pytest -p no:cacheprovider
```

## Cobertura

```bash
pytest --cov=. --cov-report=term-missing
```

Na validacao atual, a suite chegou a 224 testes automatizados cobrindo core, CLI, configuracao, YAML, logs, relatorios, projetos, sessoes, modulos, plugins, utilitarios, erros, integracao, regressao, limpeza segura, Nmap, Nuclei, smart scan, baseline, instalador assistido, scripts auxiliares e smoke tests.

## Estrutura

- `tests/test_core.py`: eventos, permissoes, contratos, validadores e recursos.
- `tests/test_cli.py`: comandos reais da CLI, parsing de parametros, arquivo de alvos do Nuclei e simulacao controlada.
- `tests/test_config.py`: configuracoes validas, invalidas, padrao e corrompidas.
- `tests/test_logger.py`: logs, auditoria e historico.
- `tests/test_reports.py`: relatorios Markdown, TXT, JSON, CSV, HTML, organizacao por projeto/data/sessao e erros esperados.
- `tests/test_projects.py`: catalogo, arquivamento, historico e estatisticas.
- `tests/test_sessions.py`: abertura, fechamento, retomada e persistencia.
- `tests/test_modules.py`: descoberta, registro, execucao, modulos internos e falhas controladas.
- `tests/test_plugins.py`: plugins validos, invalidos, desativados e incompativeis.
- `tests/test_utils.py`: persistencia auxiliar, historico, tabelas e mensagens.
- `tests/test_errors.py`: hierarquia de erros e tratamento pela CLI.
- `tests/test_integration.py`: fluxos completos entre servicos.
- `tests/test_smoke.py`: inicializacao e comandos basicos.
- `tests/test_cleanup.py`: limpeza segura de cache e preservacao de dados importantes.
- `tests/test_scanner_service.py`: validacao de alvos, comandos reais de Nmap/Nuclei, ausencia de `shell=True`, parsing Nmap XML, parsing Nuclei JSONL, ferramentas ausentes, simulacao marcada e timeout.
- `tests/test_scanner_modules.py`: modulos Nmap/Nuclei/smart scan, cancelamento sem autorizacao, confirmacao extra, relatorios em `reports/nmap`, `reports/nuclei` e `reports/smart_scan`, correlacao e historico.
- `tests/test_smart_scan_service.py`: selecao de endpoints web, decisoes do motor, correlacao Nmap/Nuclei e score de risco.
- `tests/test_baseline.py`: criacao e comparacao de baseline, novos servicos, mudancas de versao e achados persistentes/resolvidos.
- `tests/test_setup_service.py`: verificacao de ambiente, Python, pip, Git, Nmap, Nuclei, gerenciadores de pacote, relatorios de setup e comandos seguros sem `shell=True`.
- `tests/test_setup_scripts.py`: entradas auxiliares `check_tools`, `setup_report` e `setup_wizard` sem instalar ferramentas reais.

Os testes usam fixtures em `tests/conftest.py` para criar uma copia temporaria do projeto, evitando que logs, relatorios e dados de execucao sujem o repositorio.

## Criterios

Uma alteracao deve:

- passar nos testes existentes;
- adicionar testes quando alterar comportamento;
- preservar a estrutura documentada;
- atualizar documentacao e changelog quando criar funcionalidade.
