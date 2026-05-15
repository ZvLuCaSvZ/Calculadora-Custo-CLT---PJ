from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass, asdict
from typing import Callable, Dict, List, Optional, Tuple

from utils import (
    parse_brl,
)

from helpers import (
    CalculadoraPJ,
    CalculadoraCLT,
    CalculadoraTributaria,
    FormatadorResultado,
)



class CampoMoeda(ttk.Entry):
    def valor(self) -> float:
        return parse_brl(self.get())


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Calculadora CLT x PJ")
        self.state('zoomed')
        self.bind('<Escape>', lambda e: self.root.state('normal'))
        self.bind('<F11>', lambda e: self.root.state('zoomed') if self.root.state() == 'normal' else self.root.state('normal'))

        self.tributaria = CalculadoraTributaria()
        self.calc_pj = CalculadoraPJ(self.tributaria)
        self.calc_clt = CalculadoraCLT(self.tributaria)

        self._configurar_estilo()
        self._montar_interface()

    def _configurar_estilo(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(12, 8))
        style.configure("Titulo.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Aviso.TLabel", font=("Segoe UI", 9), foreground="#000000")

    def _montar_interface(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Calculadora CLT x PJ", style="Titulo.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            container,
            text="Valores aceitos: 10000, 10000.50, 10.000,50 ou R$ 10.000,50. Revise as alíquotas em ConfigTributaria quando necessário.",
            style="Aviso.TLabel",
        ).pack(anchor="w", pady=(2, 12))

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)

        self._aba_pj_equivalente_clt(notebook)
        self._aba_clt_equivalente_pj(notebook)
        self._aba_simular_pj(notebook)
        self._aba_simular_clt(notebook)

    def _criar_aba(
        self, notebook: ttk.Notebook, titulo: str
    ) -> Tuple[ttk.Frame, tk.Text]:
        frame = ttk.Frame(notebook, padding=12)
        notebook.add(frame, text=titulo)

        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(99, weight=1)

        saida = tk.Text(frame, wrap="word", font=("Consolas", 14), height=48)
        saida.grid(row=99, column=0, columnspan=3, sticky="nsew", pady=(12, 0))
        scroll = ttk.Scrollbar(frame, orient="vertical", command=saida.yview)
        saida.configure(yscrollcommand=scroll.set)
        scroll.grid(row=99, column=3, sticky="ns", pady=(12, 0))
        return frame, saida

    def _campo(
        self, frame: ttk.Frame, row: int, label: str, valor_padrao: str = ""
    ) -> CampoMoeda:
        ttk.Label(frame, text=label).grid(
            row=row, column=0, sticky="w", padx=(0, 8), pady=5
        )
        entrada = CampoMoeda(frame)
        entrada.insert(0, valor_padrao)
        entrada.grid(row=row, column=1, sticky="ew", pady=5)
        return entrada

    def _escrever_saida(self, saida: tk.Text, conteudo: str) -> None:
        saida.configure(state="normal")
        saida.delete("1.0", tk.END)
        saida.insert(tk.END, conteudo)
        saida.configure(state="disabled")

    def _executar_com_tratamento(
        self, callback: Callable[[], str], saida: tk.Text
    ) -> None:
        try:
            conteudo = callback()
            self._escrever_saida(saida, conteudo)
        except Exception as exc:
            messagebox.showerror("Erro no cálculo", str(exc))

    def _aba_pj_equivalente_clt(self, notebook: ttk.Notebook) -> None:
        frame, saida = self._criar_aba(notebook, "PJ equivalente CLT")
        liquido_clt = self._campo(frame, 0, "Líquido CLT desejado:")
        prolabore = self._campo(frame, 1, "Pró-labore mensal PJ:")

        def calcular() -> str:
            resultados = self.calc_pj.calcular_pj_equivalente_clt(
                liquido_clt.valor(), prolabore.valor()
            )
            return FormatadorResultado.lista_pj(resultados)

        ttk.Button(
            frame,
            text="Execução",
            command=lambda: self._executar_com_tratamento(calcular, saida),
        ).grid(row=2, column=1, sticky="e", pady=8)

    def _aba_clt_equivalente_pj(self, notebook: ttk.Notebook) -> None:
        frame, saida = self._criar_aba(notebook, "CLT equivalente PJ")
        liquido_pj = self._campo(frame, 0, "Faturamento Bruto PJ:")
        ajuda_custo = self._campo(frame, 1, "Ajuda de custo CLT:", "0")
        usar_media = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Comparar usando remuneração líquida média anual CLT, incluindo férias e 13º proporcionais",
            variable=usar_media,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=5)

        def calcular() -> str:
            resultado = self.calc_clt.calcular_clt_equivalente_pj(
                liquido_pj.valor(),
                ajuda_custo.valor(),
                usar_media_anual_clt=usar_media.get(),
            )
            criterio = (
                "remuneração líquida média anual"
                if usar_media.get()
                else "líquido mensal + ajuda"
            )
            return f"Critério usado: {criterio}\n\n{FormatadorResultado.clt(resultado)}"

        ttk.Button(
            frame,
            text="Execução",
            command=lambda: self._executar_com_tratamento(calcular, saida),
        ).grid(row=3, column=1, sticky="e", pady=8)

    def _aba_simular_pj(self, notebook: ttk.Notebook) -> None:
        frame, saida = self._criar_aba(notebook, "Simular custo PJ")
        bruto = self._campo(frame, 0, "Bruto / Nota Fiscal PJ:")
        prolabore = self._campo(frame, 1, "Pró-labore mensal:")

        def calcular() -> str:
            resultados = self.calc_pj.simular(bruto.valor(), prolabore.valor())
            return FormatadorResultado.lista_pj(resultados)

        ttk.Button(
            frame,
            text="Execução",
            command=lambda: self._executar_com_tratamento(calcular, saida),
        ).grid(row=2, column=1, sticky="e", pady=8)

    def _aba_simular_clt(self, notebook: ttk.Notebook) -> None:
        frame, saida = self._criar_aba(notebook, "Simular custo CLT")
        salario = self._campo(frame, 0, "Salário bruto CLT:")
        ajuda_custo = self._campo(frame, 1, "Ajuda de custo:", "0")

        def calcular() -> str:
            resultado = self.calc_clt.simular(salario.valor(), ajuda_custo.valor())
            return FormatadorResultado.clt(resultado)

        ttk.Button(
            frame,
            text="Execução",
            command=lambda: self._executar_com_tratamento(calcular, saida),
        ).grid(row=2, column=1, sticky="e", pady=8)