# Changelog

Todas as mudancas relevantes do DataSpectre CLI serao registradas neste arquivo.

## [2.0.4] - 2026-08-22

### Alterado

- O desenho da logo foi removido do terminal e substituido pelo nome compacto `DATASPECTRECLI`.

## [2.0.3] - 2026-08-22

### Adicionado

- `dataspectre.py` como ponto de entrada principal para executar com `python3 dataspectre.py`.

### Alterado

- O menu agora informa se Nmap e Nuclei estao instalados antes de iniciar uma auditoria.
- A simulacao nao e mais ativada por padrao no modo interativo; e necessario confirma-la explicitamente.
- O atalho Linux e a verificacao de instalacao agora usam `dataspectre.py`.

## [2.0.2] - 2026-08-22

### Melhorado

- Cabeçalho do terminal redesenhado com emblema DataSpectre pontilhado e indicadores compactos.
- Indicadores de sistema, Python, módulos, plugins, projetos e IP local agora aparecem em blocos alinhados.
- Todas as opções interativas agora explicam o objetivo, os dados esperados e exemplos antes da execução.
- Nmap, Nuclei e Smart Scan oferecem simulação identificada quando a ferramenta externa não está instalada.

### Alterado

- Removido o fluxo de OSINT do menu e das informações públicas do pacote.
- Menu interativo reorganizado em português, preservando somente as funções disponíveis.

## [2.0.1] - 2026-08-22

### Melhorado

- Instalacao Linux agora registra o pacote em modo editavel, criando um comando `dataspectre` funcional no ambiente virtual.
- README simplificado para instalacao, atualizacao e uso direto pelo terminal Linux com `git clone`.
- Interface ajustada para terminais estreitos: a marca fica compacta e tabelas muito largas passam a usar formato vertical legivel.

### Corrigido

- Configuracao explícita de descoberta de pacotes no `pyproject.toml`, corrigindo a falha de `pip install -e .`.
- Caminhos longos nao sao mais cortados na tela de status.
- Verificacao de setup passou a validar apenas arquivos necessários para executar a aplicacao.

## [2.0.0] - 2026-08-22
- Adicionados `INSTALL_DATASPECTRE_LINUX.sh` e `START_DATASPECTRE.sh` para instalacao/execucao nativa em Kali, Ubuntu, Debian, Fedora, Arch, Manjaro, openSUSE, Alpine, Void e outras distribuicoes com Python 3.10+.

### Adicionado

- Identidade visual DataSpectre em verde/preto, arte ASCII para terminal e imagem oficial em `assets/dataspectre_terminal.png`.
- Comando instalado `dataspectre` e atalhos Windows `INSTALL_DATASPECTRE.bat` / `START_DATASPECTRE.bat`.
- Acessos interativos para Smart Scan, Inventario de Ativos, System Health e Resumo de Projetos.
- Documento `docs/DATASPECTRE_V2_CHANGES.md` com o resumo da migracao.

### Melhorado

- Interface agora detecta a largura do terminal e limita colunas longas para reduzir cortes e sobreposicoes.
- Menu interativo foi simplificado para mostrar principalmente funcionalidades realmente implementadas.
- Configuracao principal passou para `config/dataspectre.yaml`, mantendo leitura do arquivo antigo apenas por compatibilidade.
- Branding, README, documentacao, pacote Python e relatorios de setup foram atualizados para DataSpectre CLI.

### Corrigido

- Alinhamento de paineis em terminais com ANSI habilitado.
- Encerramento do menu em EOF e tratamento de entradas vazias.
- Regressao do teste de resolucao do diretorio raiz causada pelo sufixo `-main` do ZIP original.
- Suite automatizada revisada e validada integralmente apos o rebranding.

## [Nao lancado] - 2026-07-06

### Adicionado

- Interface CLI mais organizada com paineis, ajuda integrada, menu interativo ampliado, barra de progresso e mensagens coloridas quando suportado pelo terminal.
- Dashboard inicial em estilo cyber/hacker com logo ASCII, slogan, autor, status, usuario, sistema operacional, IP local, CPU, RAM e aviso etico.
- Integracao do Nmap como modulo interno `nmap_scan`, com perfis reais `rapida/quick`, `servicos/services`, `scripts-padrao`, `servicos-scripts`, `portas/ports` e `custom`.
- Integracao do Nuclei como modulo interno `nuclei_scan`, com perfis reais `basic`, `technologies`, `exposure`, `low-medium`, `medium-high`, `high`, `critical`, `template` e `custom`.
- Comandos `scan nmap` e `scan nuclei` com confirmacao obrigatoria de autorizacao e confirmacao extra para perfis avancados/personalizados.
- Modulo `smart_scan` para correlacionar descoberta Nmap, endpoints web selecionados e achados Nuclei.
- Comando `scan smart` com perfis `basic`, `intermediate`, `advanced` e `custom`.
- Servico `SmartScanService` para selecao inteligente de endpoints web, decisoes rastreaveis, correlacao e score de risco.
- Servico `BaselineService` e comandos `baseline create` / `baseline compare` para baseline defensivo de exposicoes.
- Configuracao YAML segura em `config/dataspectre.yaml` e exemplo em `config/dataspectre.example.yaml`.
- Suporte controlado a NSE do Nmap com perfis/scripts permitidos.
- Filtros adicionais de Nuclei por tags, severidades, templates e diretorios de templates.
- Opcao `--target-file` no Nuclei para montar comando real com `nuclei -l targets.txt`.
- Modo `--simulate` para Nmap, Nuclei e Smart Scan quando ferramentas externas estiverem ausentes, sempre com resultado ficticio explicitamente marcado.
- Exportacao de relatorios nos formatos Markdown, TXT, JSON, CSV e HTML.
- Organizacao simples de relatorios de scanner em `reports/nmap/`, `reports/nuclei/` e `reports/smart_scan/`, com data e hora no nome.
- Historico interno enriquecido com funcao executada, data/hora, resultado e erro tecnico quando houver.
- Relatorio final da sessao no encerramento do modo interativo, incluindo tempo total, modulos usados, relatorios criados e erros encontrados.
- Servico e comando de limpeza segura de temporarios, com simulacao por padrao e confirmacao explicita via `--yes`.
- Instalador assistido com verificacao de Python, pip, Git, dependencias, estrutura de pastas, arquivos obrigatorios, permissoes, Nmap e Nuclei.
- Scripts auxiliares `scripts/setup_wizard.py`, `scripts/check_tools.py`, `scripts/install_dependencies.py`, `scripts/setup_report.py` e `scripts/__init__.py`.
- Comandos `setup check`, `setup tools` e `setup wizard` para verificar ambiente, ferramentas e abrir o assistente pela CLI.
- Relatorios de setup em `reports/setup/setup_report.txt` e `reports/setup/setup_report.json`.
- Submenu de configuracoes com `Verificar ambiente`, `Instalador assistido` e `Verificar Nmap/Nuclei`.
- Documento `docs/FUNCTIONAL_AUDIT.md` com matriz funcional opcao por opcao.
- Opcao `--data-file` em `reports generate` para gerar relatorios manuais a partir de arquivos JSON.
- Suite ampliada para 224 testes automatizados, cobrindo os novos fluxos de CLI, YAML, relatorios, configuracao, historico, limpeza, Nmap, Nuclei, smart scan, baseline, instalador assistido, scripts e resumo de sessao.
- Arquivo `requirements.txt` raiz apontando para as dependencias de execucao.
- Dependencia `rich` para experiencia visual profissional em terminais compativeis, com fallback ASCII.

### Melhorado

- Tratamento de erros da CLI com mensagens amigaveis ao usuario e detalhes tecnicos persistidos em logs e historico.
- Tratamento de erros para Nmap/Nuclei ausentes, alvos invalidos, timeout, saida vazia, parsing XML/JSONL e templates/configuracoes invalidas.
- Parser Nmap enriquecido com hostnames, IP, sistema operacional, produto, versao e tecnologias quando disponiveis no XML.
- Nmap agora monta comandos praticos como `nmap -T4 -F TARGET`, `nmap -sV TARGET`, `nmap -sC TARGET`, `nmap -sV -sC TARGET` e `nmap -p PORTAS TARGET`.
- Nuclei agora monta comandos praticos como `nuclei -u TARGET`, `nuclei -u TARGET -severity high`, `nuclei -u TARGET -severity critical`, `nuclei -u TARGET -severity medium,high`, `nuclei -u TARGET -t TEMPLATE` e `nuclei -l targets.txt`.
- Smart Scan agora salva TXT/XML do Nmap, interpreta o XML, seleciona somente endpoints web e executa Nuclei apenas nesses endpoints.
- Priorizacao de risco combinando severidade, endpoint correlacionado, servico, versao e evidencia.
- README com secao completa "Como executar no Linux", comandos por distribuicao, primeira execucao, atualizacao, solucao de problemas, FAQ, desenvolvimento e licenca.
- README com secoes dedicadas ao uso de Nmap e Nuclei no DataSpectre CLI.
- README com secoes para Smart Scan, Baseline Defensivo e Configuracao YAML.
- README com secao "Instalador assistido", incluindo execucao, verificacoes, Nmap, Nuclei, relatorios e erros comuns.
- Guia de testes atualizado com a cobertura dos novos componentes.
- Navegacao interativa revisada para substituir telas marcadas como desenvolvimento por fluxos guiados defensivos.
- Ajuda e documentacao agora mostram `--data-file` para evitar problemas de citacao de JSON em shells diferentes.

### Corrigido

- Banner inicial removeu a linha hexadecimal de autor, mantendo a apresentacao profissional da CLI.
- Saida de status preserva o caminho completo do projeto mesmo quando o painel visual quebra linhas longas.
- Validacao de configuracao agora aceita todos os formatos de relatorio suportados.
- Opcao "Listar modulos" agora usa renderizacao dedicada, mostra Nmap/Nuclei, informa estado/categoria/versao e exibe mensagem amigavel quando nao ha modulos carregados.
- Opcoes `4`, `5`, `6`, `7`, `8` e `10` do menu interativo deixaram de cair como invalidas e agora exibem status funcional claro.
- Opcoes `3`, `4`, `5`, `6`, `7`, `8` e `10` agora exibem fluxos guiados seguros em vez de mensagens de desenvolvimento.
- Fluxo interativo de limpeza agora mostra aviso, simula, pede confirmacao e permite cancelar sem apagar arquivos.
- Fluxo interativo de relatorios agora abre o Report Center, lista relatorios e permite gerar relatorio manual com validacao JSON.
- Geracao manual de relatorios agora possui caminho por arquivo JSON, reduzindo falhas de uso com JSON inline no PowerShell.

## [1.0.0] - 2026-07-06

### Adicionado

- Estrutura completa do repositorio conforme a especificacao tecnica.
- Nucleo da aplicacao com bootstrap, contexto, eventos, seguranca e ciclo de vida.
- Interface CLI com comandos para status, configuracoes, projetos, sessoes, modulos, relatorios, plugins e auditoria.
- Gerenciador de modulos com descoberta automatica, validacao, estados, execucao e isolamento de falhas.
- Sistema centralizado de configuracao com validacao e persistencia em JSON.
- Logs rotativos e auditoria estruturada em JSONL.
- Gerenciamento de projetos e sessoes com catalogo, historico e arquivos por projeto.
- Sistema de relatorios em Markdown e JSON.
- Sistema de plugins com manifestos e plugin de referencia.
- Modulos internos `asset_inventory`, `system_health` e `project_summary`.
- Testes unitarios e de integracao.
- Documentacao operacional, tecnica e de contribuicao.
- Suite ampliada com mais de 100 testes automatizados cobrindo core, CLI, configuracao, logs, relatorios, projetos, sessoes, modulos, plugins, utilitarios, erros, integracao, regressao e smoke.
- Segunda rodada de validacao da suite, removendo teste/helper redundante, cobrindo entradas principais, smoke script, lifecycle defensivo, plugins duplicados/incompativeis, metadados inconsistentes e falhas de loader.

### Observacoes

- A especificacao descreve uma plataforma expansivel; esta versao entrega a base funcional completa para evolucao incremental.
- Modulos de auditoria intrusiva nao foram adicionados nesta versao inicial; o foco e seguranca operacional, inventario informado e extensibilidade.
- Configuracoes corrompidas, niveis de log invalidos e plugins incompativeis agora possuem comportamento seguro coberto por testes de regressao.
- A validacao daquela rodada registrou 136 testes aprovados e 100% de cobertura nos pacotes da aplicacao.
