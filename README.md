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
python3 dataspectre.py
```

`./START_DATASPECTRE.sh` continua disponível como atalho e usa o mesmo ponto de entrada.

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
python3 dataspectre.py status
python3 dataspectre.py help
python3 dataspectre.py interactive
python3 dataspectre.py setup check
python3 dataspectre.py modules list
python3 dataspectre.py plugins list
```

O comando global `dataspectre` e o atalho `./START_DATASPECTRE.sh` são opcionais. Os dois aceitam os mesmos parâmetros:

```bash
./START_DATASPECTRE.sh status
./START_DATASPECTRE.sh modules list
./START_DATASPECTRE.sh help
```

## Fluxo básico

Crie um projeto e uma sessão:

```bash
python3 dataspectre.py projects create "Laboratório autorizado" --description "Ambiente de testes"
python3 dataspectre.py projects list
python3 dataspectre.py sessions start <project_id>
```

Execute os módulos locais e gere relatórios:

```bash
python3 dataspectre.py modules run asset_inventory --param input_file=examples/assets.json --report
python3 dataspectre.py modules run system_health --report --report-format html
python3 dataspectre.py reports list
```

Gere um relatório manual a partir de um arquivo JSON:

```bash
python3 dataspectre.py reports generate --title "Resumo" --format json --data-file examples/assets.json
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

O instalador assistido verifica e oferece a instalação das ferramentas disponíveis no Linux. Ele nunca inicia uma auditoria:

```bash
python3 dataspectre.py setup wizard --install
```

Verifique o ambiente antes de executar uma auditoria:

```bash
python3 dataspectre.py setup tools
python3 dataspectre.py modules list
```

Os comandos de auditoria exigem `--authorize`:

```bash
python3 dataspectre.py scan nmap 127.0.0.1 --authorize
python3 dataspectre.py scan nuclei http://localhost --authorize
python3 dataspectre.py scan smart 127.0.0.1 --authorize
```

Para verificar o fluxo sem as ferramentas externas, use dados de simulação identificados:

```bash
python3 dataspectre.py scan nmap 127.0.0.1 --authorize --simulate
python3 dataspectre.py scan nuclei http://localhost --authorize --simulate
python3 dataspectre.py scan smart 127.0.0.1 --authorize --simulate
```

Perfis de maior impacto exigem confirmação adicional:

```bash
python3 dataspectre.py scan nmap 127.0.0.1 --profile custom --custom-flag -sV --authorize --extra-confirm
python3 dataspectre.py scan nuclei http://localhost --profile high --authorize --extra-confirm
```

## Relatórios, histórico e manutenção

```bash
python3 dataspectre.py reports list
python3 dataspectre.py logs audit --limit 20
python3 dataspectre.py maintenance clean-temp
python3 dataspectre.py maintenance clean-temp --yes
```

Sem `--yes`, a limpeza apenas mostra o que pode ser removido. Relatórios, logs, projetos e dados persistentes são preservados.

## Atualização

Dentro da pasta do projeto:

```bash
git pull --ff-only
./INSTALL_DATASPECTRE_LINUX.sh
python3 dataspectre.py status
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
