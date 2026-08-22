# DataSpectre CLI 2.0 — alterações desta revisão

Esta revisão transforma a identidade visual e operacional do projeto em **DataSpectre CLI** sem remover as salvaguardas de uso autorizado.

## Principais melhorias

- Rebranding completo da interface, documentação, configuração e pacote Python para DataSpectre.
- Nova identidade visual de terminal verde/preto, com arte ASCII própria para console e imagem `assets/dataspectre_terminal.png` para README/divulgação.
- Largura de terminal detectada automaticamente e tabelas com truncamento seguro para evitar cortes e sobreposição.
- Correção do alinhamento dos painéis quando ANSI está ativo.
- Menu interativo simplificado e baseado em funcionalidades realmente implementadas.
- Novos acessos interativos para Smart Scan, Inventário de Ativos, System Health e Resumo de Projetos.
- Saída segura em EOF/Ctrl+C e mensagens mais consistentes.
- Novo comando instalado `dataspectre`, mantendo `sentinelscan` apenas como alias de compatibilidade.
- Configuração principal movida para `config/dataspectre.yaml`, com leitura opcional do arquivo legado.
- Atalhos Windows `INSTALL_DATASPECTRE.bat` e `START_DATASPECTRE.bat`.
- Suite de testes atualizada para a nova interface e rebranding.

## Compatibilidade

`python main.py ...` continua funcionando. `DATASPECTRE_ROOT` é a variável de ambiente preferencial; `SENTINELSCAN_ROOT` continua aceita somente para compatibilidade com instalações antigas.
