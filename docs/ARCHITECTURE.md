# Architecture

DataSpectre CLI usa arquitetura em camadas:

1. `cli/`: interface de terminal, parsing de comandos, mensagens e tabelas.
2. `app/`: bootstrap, ciclo de vida e composicao de dependencias.
3. `core/`: eventos, contratos de modulos/plugins, validacoes, seguranca e excecoes.
4. `services/`: configuracao, logs, auditoria, projetos, sessoes, relatorios e historico.
5. `modules/`: funcionalidades independentes carregadas pelo gerenciador de modulos.
6. `plugins/`: extensoes opcionais carregadas por manifesto.
7. `data/`, `reports/`, `logs/`, `cache/`, `backups/`: persistencia operacional.

## Fluxo de inicializacao

1. `main.py` chama `cli.app.main`.
2. A CLI resolve o diretorio raiz.
3. `DataSpectreApplication` chama `Bootstrapper`.
4. O bootstrap valida Python, cria diretorios, carrega configuracoes, inicializa logs e auditoria.
5. Servicos de projetos, sessoes, relatorios e historico sao conectados ao contexto.
6. Modulos e plugins sao descobertos, validados, inicializados e registrados.
7. A CLI executa o comando solicitado.

## Eventos

O `EventBus` publica eventos internos como:

- `module.loaded`
- `module.execution_started`
- `module.execution_finished`
- `plugin.loaded`
- `plugin.initialized`
- `application.initialized`

Esses eventos sao encaminhados para logs de auditoria.

## Decisoes de implementacao

- A persistencia inicial usa JSON/JSONL para manter simplicidade, rastreabilidade e facilidade de testes.
- A CLI usa apenas biblioteca padrao no runtime, reduzindo atrito de instalacao.
- Modulos internos iniciais sao seguros e nao intrusivos; novos modulos podem ser adicionados pela interface publica.

