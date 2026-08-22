# Nmap Scan

Modulo interno para executar Nmap somente em alvos autorizados, usando perfis seguros,
validacao de entrada, saida TXT/XML, parsing estruturado, historico e relatorios.

## Perfis

- `rapida` ou `quick`: `nmap -T4 -F TARGET`.
- `servicos` ou `services`: `nmap -sV TARGET`.
- `scripts-padrao`: `nmap -sC TARGET`.
- `servicos-scripts`: `nmap -sV -sC TARGET`.
- `portas` ou `ports`: `nmap -p PORTAS TARGET`.
- `custom`: flags permitidas e confirmacao extra.

## Uso

```bash
python main.py scan nmap 127.0.0.1 --profile rapida --authorize
python main.py scan nmap 127.0.0.1 --profile servicos-scripts --authorize
python main.py scan nmap 127.0.0.1 --profile portas --ports 80,443 --authorize
python main.py scan nmap 127.0.0.1 --authorize --simulate
```

Sem `--authorize`, o modulo cancela a execucao. Quando o Nmap nao estiver instalado, `--simulate` gera dados ficticios claramente marcados.

## Relatorios

```text
reports/nmap/
```
