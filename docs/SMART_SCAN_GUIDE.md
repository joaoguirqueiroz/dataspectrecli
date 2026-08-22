# Smart Scan Guide

## Objetivo

O Smart Scan combina descoberta Nmap, selecao de endpoints web e validacao Nuclei de forma controlada, rastreavel e autorizada.

## Fluxo

1. Validar alvo ou lista de alvos.
2. Exigir confirmacao de autorizacao.
3. Executar Nmap com argumentos seguros e reais, salvando TXT e XML.
4. Interpretar XML e extrair hosts, hostnames, SO, portas, servicos, produtos, versoes e tecnologias.
5. Selecionar somente endpoints web candidatos.
6. Executar Nuclei somente nos endpoints selecionados, quando instalado.
7. Correlacionar achados Nuclei com host, porta, servico e tecnologia Nmap.
8. Calcular risco priorizado.
9. Gerar relatorios TXT, JSON, CSV e HTML.

## Comando

```bash
python main.py scan smart 127.0.0.1 --authorize
python main.py scan smart 192.168.1.10 --profile advanced --authorize --extra-confirm
python main.py scan smart 127.0.0.1 --authorize --simulate
```

Com `--simulate`, dados ficticios sao gerados somente quando Nmap ou Nuclei nao estiverem disponiveis. O relatorio marca claramente:

```text
Resultado simulado: estes dados sao ficticios e servem apenas para demonstracao da interface e dos relatorios.
```

## Relatorios

```text
reports/smart_scan/
```

Os relatorios incluem comando executado, alvo, data/hora, status, resultados do Nmap, endpoints web selecionados, achados Nuclei correlacionados, recomendacoes basicas e aviso de uso autorizado.

## Perfis

- `basic`: fluxo leve e seguro.
- `intermediate`: adiciona mais contexto de servico e tags de exposicao.
- `advanced`: exige confirmacao extra e usa perfil NSE seguro.
- `custom`: exige confirmacao extra e permite portas, templates, tags, severidades e NSE controlado.

## Baseline

```bash
python main.py baseline create lab --data resultado-smart.json
python main.py baseline compare lab --data resultado-smart-novo.json
```

O baseline compara servicos, versoes e achados, destacando mudancas relevantes para Blue Team.

## Seguranca

- Nao ha stealth, evasao, exploracao automatica ou brute force.
- Nao ha `shell=True`.
- Nuclei nao roda sem endpoint web relevante.
- Nmap/Nuclei exigem autorizacao explicita.
- Perfis avancados e customizados exigem confirmacao extra.
