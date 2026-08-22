# DataSpectre CLI

Ferramenta de terminal para inventário de ativos, saúde do sistema, organização de projetos, relatórios e auditorias autorizadas com Nmap e Nuclei.

Use somente em ativos próprios, laboratórios ou ambientes para os quais você possui autorização explícita.

## Instalação no Linux

Requer Python 3.10+ e Git. Em Debian, Ubuntu, Kali e derivados, instale-os se necessário:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
```

Clone e instale:

```bash
git clone https://github.com/joaoguirqueiroz/dataspectrecli.git
cd dataspectrecli
chmod +x INSTALL_DATASPECTRE_LINUX.sh START_DATASPECTRE.sh
./INSTALL_DATASPECTRE_LINUX.sh
```

Abra o menu guiado da própria pasta:

```bash
./START_DATASPECTRE.sh
```

Para usar o comando de qualquer terminal na sessão atual:

```bash
export PATH="$HOME/.local/bin:$PATH"
dataspectre
```

O caminho `~/.local/bin` pode ser adicionado ao arquivo de configuração do seu shell para mantê-lo nas próximas sessões. Sem alterar o `PATH`, o comando abaixo sempre funciona:

```bash
~/.local/bin/dataspectre status
```

## Primeiros comandos

```bash
dataspectre status
dataspectre help
dataspectre interactive
dataspectre setup check
dataspectre modules list
dataspectre plugins list
```

Caso esteja usando apenas o clone, substitua `dataspectre` por `./START_DATASPECTRE.sh`:

```bash
./START_DATASPECTRE.sh status
./START_DATASPECTRE.sh modules list
./START_DATASPECTRE.sh help
```

## Fluxo básico

Crie um projeto e uma sessão:

```bash
dataspectre projects create "Laboratório autorizado" --description "Ambiente de testes"
dataspectre projects list
dataspectre sessions start <project_id>
```

Execute os módulos locais e gere relatórios:

```bash
dataspectre modules run asset_inventory --param input_file=examples/assets.json --report
dataspectre modules run system_health --report --report-format html
dataspectre reports list
```

Gere um relatório manual a partir de um arquivo JSON:

```bash
dataspectre reports generate --title "Resumo" --format json --data-file examples/assets.json
```

## Auditorias autorizadas

Nmap e Nuclei são opcionais. Instale as ferramentas externas apenas se precisar desses módulos:

```bash
sudo apt install -y nmap
nmap --version
```

```bash
nuclei -version
```

Verifique o ambiente antes de executar uma auditoria:

```bash
dataspectre setup tools
dataspectre modules list
```

Os comandos de auditoria exigem `--authorize`:

```bash
dataspectre scan nmap 127.0.0.1 --authorize
dataspectre scan nuclei http://localhost --authorize
dataspectre scan smart 127.0.0.1 --authorize
```

Para verificar o fluxo sem as ferramentas externas, use dados de simulação identificados:

```bash
dataspectre scan nmap 127.0.0.1 --authorize --simulate
dataspectre scan nuclei http://localhost --authorize --simulate
dataspectre scan smart 127.0.0.1 --authorize --simulate
```

Perfis de maior impacto exigem confirmação adicional:

```bash
dataspectre scan nmap 127.0.0.1 --profile custom --custom-flag -sV --authorize --extra-confirm
dataspectre scan nuclei http://localhost --profile high --authorize --extra-confirm
```

## Relatórios, histórico e manutenção

```bash
dataspectre reports list
dataspectre logs audit --limit 20
dataspectre maintenance clean-temp
dataspectre maintenance clean-temp --yes
```

Sem `--yes`, a limpeza apenas mostra o que pode ser removido. Relatórios, logs, projetos e dados persistentes são preservados.

## Atualização

Dentro da pasta do projeto:

```bash
git pull --ff-only
./INSTALL_DATASPECTRE_LINUX.sh
dataspectre status
```

## Diagnóstico rápido

```bash
python3 --version
git --version
./START_DATASPECTRE.sh setup check
```

Se a instalação de dependências falhar, recrie o ambiente virtual e rode o instalador novamente:

```bash
rm -rf .venv
./INSTALL_DATASPECTRE_LINUX.sh
```

Para executar a suíte de testes:

```bash
source .venv/bin/activate
python -B -m pytest -p no:cacheprovider
```

## Estrutura

```text
app/        inicialização e ciclo de vida
cli/        comandos e interface de terminal
core/       contratos, validações e segurança
modules/    módulos internos
services/   configuração, relatórios, projetos e logs
config/     valores padrão da aplicação
docs/       documentação técnica
tests/      testes automatizados
```

## Licença

Consulte [LICENSE](LICENSE).
