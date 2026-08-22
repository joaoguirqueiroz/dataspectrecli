# Smart Scan

Correlaciona descoberta Nmap autorizada com validacao Nuclei direcionada. O modulo exige `--authorize`, salva TXT/XML do Nmap, interpreta o XML, seleciona apenas endpoints com caracteristica web e executa Nuclei somente nesses endpoints.

## Fluxo

1. Validar alvo autorizado.
2. Executar Nmap com perfil seguro.
3. Interpretar o XML do Nmap.
4. Selecionar servicos web como http, https, nginx, apache, tomcat e portas web comuns.
5. Montar URLs HTTP/HTTPS.
6. Executar Nuclei somente nos endpoints web.
7. Correlacionar host, porta, servico, versao, endpoint, template e severidade.
8. Gerar relatorios.

## Uso

```bash
python main.py scan smart 127.0.0.1 --authorize
python main.py scan smart 127.0.0.1 --profile advanced --authorize --extra-confirm
python main.py scan smart 127.0.0.1 --authorize --simulate
```

Quando Nmap ou Nuclei nao estiverem instalados, `--simulate` gera dados ficticios claramente marcados para testar interface, parsing e relatorios.

## Relatorios

```text
reports/smart_scan/
```
