# CALCULADORA CUSTO CLT x PJ

Projeto simples, em arquitetura em camadas, porém bem estruturado e com funções agrupadas conforme relacionamento.

## Execução

- `main.py` abre uma janela gráfica por padrão.
- A interface possuí 4 abas, cada uma tem sua responsabilidade e cálculo próprio.
- Após selecionar o botão "Execução", os cálculos serão exibidos diretamente na interface.

## Estrutura

```text
gui.py                  Interface em Tkinter
main.py                 Execução do Projeto
utils.py                Funções auxiliares e de formatação de valores
helpers.py              Lógica de calculos e padronização das informações para exibição ao usuário.
config.py               Bases para calculos dos impostos, seguindo as tabelas de 2026.
requirements.txt        Dependências do projeto
```

## Como executar com janela

```bash
python main.py
```

## Como executar pelo menu do terminal

```bash
python main.py
```

## Instalação das dependências

```bash
pip install -r requirements.txt
```

## Observações importantes

- A única dependência necessário é o PyInstaller no caso do usuário querer gerar um .exe.