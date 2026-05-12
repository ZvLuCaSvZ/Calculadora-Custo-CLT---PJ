
from __future__ import annotations

import tkinter as tk
import PyInstaller.__main__
from tkinter import ttk, messagebox
from dataclasses import dataclass, asdict
from typing import Callable, Dict, List, Optional, Tuple

"""
Calculadora CLT x PJ com interface grafica (Tkinter).

Funcionalidades:
1. Calculo PJ equivalente CLT
2. Calculo CLT equivalente PJ
3. Simular custo PJ
4. Simular custo CLT

As tabelas/aliquotas estao parametrizadas em ConfigTributaria.
Revise os parametros com um contador antes de usar para decisoes reais.
"""


# Utilitarios

def formatar_brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_percentual(valor: float) -> str:
    return f"{valor:.2%}".replace(".", ",")


def parse_brl(texto: str) -> float:
    texto = (texto or "").strip().replace("R$", "").replace(" ", "")
    if not texto:
        return 0.0

    # Aceita tanto 1234.56 quanto 1.234,56 e 1234,56
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        valor = float(texto)
    except ValueError as exc:
        raise ValueError(f"Valor invalido: {texto}") from exc

    if valor < 0:
        raise ValueError("Digite apenas valores positivos.")
    return valor


def arredondar(valor: float) -> float:
    return round(valor + 1e-9, 2)

# Configuracoes tributarias

@dataclass(frozen=True)
class FaixaProgressiva:
    limite: Optional[float]
    aliquota: float
    deducao: float = 0.0


@dataclass(frozen=True)
class FaixaSimples:
    limite: float
    aliquota: float
    deducao: float


@dataclass(frozen=True)
class ConfigTributaria:
    # INSS empregado 2026 - (Faixa, Alíquota)
    inss_faixas: Tuple[Tuple[float, float], ...] = (
        (1621.00, 0.075), 
        (2902.84, 0.09),
        (4354.27, 0.12),
        (8475.55, 0.14),
    )
    teto_inss: float = 8475.55
    inss_prolabore_aliquota: float = 0.11

    # IRRF mensal - (Faixa, Alíquota, Dedução)
    irrf_faixas: Tuple[FaixaProgressiva, ...] = (
        FaixaProgressiva(2428.80, 0.0, 0.0), 
        FaixaProgressiva(2826.65, 0.075, 182.16),
        FaixaProgressiva(3751.05, 0.15, 394.16),
        FaixaProgressiva(4664.68, 0.225, 675.49),
        FaixaProgressiva(None, 0.275, 908.73),
    )

    # Encargos CLT
    aliquota_fgts: float = 0.08 # FGTS 8%
    aliquota_patronal: float = 0.286  # INSS empresa (20%) + terceiros (5,80%) + SAT (2,79%)

    # Simples Nacional - Anexos III e V - (Faixa, Alíquota, Dedução)
    simples_anexo_3: Tuple[FaixaSimples, ...] = (
        FaixaSimples(180000, 0.06, 0),
        FaixaSimples(360000, 0.112, 9360),
        FaixaSimples(720000, 0.135, 17640),
        FaixaSimples(1800000, 0.16, 35640),
        FaixaSimples(3600000, 0.21, 125640),
        FaixaSimples(4800000, 0.33, 648000),
    )
    simples_anexo_5: Tuple[FaixaSimples, ...] = (
        FaixaSimples(180000, 0.155, 0),
        FaixaSimples(360000, 0.18, 4500),
        FaixaSimples(720000, 0.195, 9900),
        FaixaSimples(1800000, 0.205, 17100),
        FaixaSimples(3600000, 0.23, 62100),
        FaixaSimples(4800000, 0.305, 540000),
    )

    # Lucro Presumido
    presuncao_servicos: float = 0.32 # 32% Base Presumida
    irpj_aliquota: float = 0.15 # 15% IRPJ
    irpj_adicional_aliquota: float = 0.10 # 10% ADICIONAL IRPJ
    irpj_adicional_limite_mensal: float = 20000.0 # LIMITE PARA ADICIONAL IRPJ
    csll_aliquota: float = 0.09 # 9% CSLL
    pis_aliquota: float = 0.0065 # 0,65% PIS
    cofins_aliquota: float = 0.03 # 3% COFINS
    iss_aliquota: float = 0.05 # 5% ISS 


# Modelos de resultado

@dataclass
class ResultadoPJ:
    regime: str
    bruto: float
    prolabore: float
    liquido: float
    total_encargos: float
    inss: float
    irrf: float
    simples: float = 0.0
    aliquota_efetiva: float = 0.0
    fator_r: Optional[float] = None
    irpj: float = 0.0
    adicional_irpj: float = 0.0
    csll: float = 0.0
    pis: float = 0.0
    cofins: float = 0.0
    iss: float = 0.0
    total_impostos: float = 0.0
    liquido_desejado: Optional[float] = None
    diferenca: Optional[float] = None


@dataclass
class ResultadoCLT:
    salario_bruto: float
    ajuda_custo: float
    inss: float
    irrf: float
    fgts: float
    inss_patronal: float
    liquido_mensal: float
    liquido_mensal_com_ajuda: float
    ferias_bruto: float
    ferias_inss: float
    ferias_irrf: float
    ferias_fgts: float
    ferias_inss_patronal: float
    ferias_liquido: float
    decimo_bruto: float
    decimo_inss: float
    decimo_irrf: float
    decimo_fgts: float
    decimo_inss_patronal: float
    decimo_liquido: float
    provisao_ferias_mensal: float
    provisao_decimo_mensal: float
    custo_fgts_mensal_total: float
    custo_inss_patronal_mensal_total: float
    custo_total_empresa_mensal: float
    remuneracao_liquida_media_mensal: float
    liquido_desejado: Optional[float] = None
    diferenca: Optional[float] = None

# Calculadoras de imposto

class CalculadoraTributaria:
    def __init__(self, config: ConfigTributaria | None = None) -> None:
        self.config = config or ConfigTributaria()

    def calcular_inss_clt(self, salario_bruto: float) -> float:
        base = min(salario_bruto, self.config.teto_inss)
        total = 0.0
        limite_anterior = 0.0

        for limite, aliquota in self.config.inss_faixas:
            base_faixa = min(base, limite) - limite_anterior
            if base_faixa > 0:
                total += base_faixa * aliquota
            if base <= limite:
                break
            limite_anterior = limite

        return arredondar(total)

    def calcular_inss_prolabore(self, prolabore: float) -> float:
        base = min(prolabore, self.config.teto_inss)
        return arredondar(base * self.config.inss_prolabore_aliquota)

    def calcular_irrf_por_base(self, base_calculo: float) -> float:
        for faixa in self.config.irrf_faixas:
            if faixa.limite is None or base_calculo <= faixa.limite:
                return arredondar(
                    max(base_calculo * faixa.aliquota - faixa.deducao, 0.0)
                )
        return 0.0

    def calcular_irrf_clt(self, salario_bruto: float) -> float:
        inss = self.calcular_inss_clt(salario_bruto)
        return self.calcular_irrf_por_base(salario_bruto - inss)

    def calcular_irrf_prolabore(self, prolabore: float) -> float:
        inss = self.calcular_inss_prolabore(prolabore)
        return self.calcular_irrf_por_base(prolabore - inss)

# Calculadora PJ

class CalculadoraPJ:
    def __init__(self, tributaria: CalculadoraTributaria | None = None) -> None:
        self.tributaria = tributaria or CalculadoraTributaria()
        self.config = self.tributaria.config

    def aliquota_efetiva_simples(
        self, rbt12: float, faixas: Tuple[FaixaSimples, ...]
    ) -> float:
        if rbt12 <= 0:
            return 0.0
        for faixa in faixas:
            if rbt12 <= faixa.limite:
                return max((rbt12 * faixa.aliquota - faixa.deducao) / rbt12, 0.0)
        raise ValueError("Receita Brutal Anual acima do limite do Simples Nacional parametrizado.")

    def simples_anexo_3(self, bruto: float, prolabore: float) -> ResultadoPJ:
        return self._calcular_simples(
            "Simples Anexo III", bruto, prolabore, self.config.simples_anexo_3
        )

    def simples_anexo_5(self, bruto: float, prolabore: float) -> ResultadoPJ:
        return self._calcular_simples(
            "Simples Anexo V", bruto, prolabore, self.config.simples_anexo_5
        )

    def simples_fator_r(self, bruto: float, prolabore: float) -> ResultadoPJ:
        fator_r = prolabore / bruto if bruto > 0 else 0.0
        if fator_r >= 0.28:
            resultado = self.simples_anexo_3(bruto, prolabore)
            resultado.regime = "Simples com Fator R (Anexo III)"
        else:
            resultado = self.simples_anexo_5(bruto, prolabore)
            resultado.regime = "Simples com Fator R (Anexo V)"
        resultado.fator_r = fator_r
        return resultado

    def lucro_presumido(self, bruto: float, prolabore: float) -> ResultadoPJ:
        base_presumida = bruto * self.config.presuncao_servicos
        irpj = base_presumida * self.config.irpj_aliquota
        adicional_irpj = 0.0
        if base_presumida > self.config.irpj_adicional_limite_mensal:
            adicional_irpj = (
                base_presumida - self.config.irpj_adicional_limite_mensal
            ) * self.config.irpj_adicional_aliquota

        csll = base_presumida * self.config.csll_aliquota
        pis = bruto * self.config.pis_aliquota
        cofins = bruto * self.config.cofins_aliquota
        iss = bruto * self.config.iss_aliquota
        inss = self.tributaria.calcular_inss_prolabore(prolabore)
        irrf = self.tributaria.calcular_irrf_prolabore(prolabore)
        total_impostos = irpj + adicional_irpj + csll + pis + cofins + iss
        liquido = bruto - total_impostos - inss - irrf
        total_encargos = total_impostos + inss + irrf

        return ResultadoPJ(
            regime="Lucro Presumido",
            bruto=arredondar(bruto),
            prolabore=arredondar(prolabore),
            irpj=arredondar(irpj),
            adicional_irpj=arredondar(adicional_irpj),
            csll=arredondar(csll),
            pis=arredondar(pis),
            cofins=arredondar(cofins),
            iss=arredondar(iss),
            total_impostos=arredondar(total_impostos),
            inss=inss,
            irrf=irrf,
            liquido=arredondar(liquido),
            total_encargos=arredondar(total_encargos),
        )

    def todos_regimes(self) -> List[Tuple[str, Callable[[float, float], ResultadoPJ]]]:
        return [
            ("Simples Anexo III", self.simples_anexo_3),
            ("Simples Anexo V", self.simples_anexo_5),
            ("Simples com Fator R", self.simples_fator_r),
            ("Lucro Presumido", self.lucro_presumido)
        ]
        
    def simular(self, bruto: float, prolabore: float) -> List[ResultadoPJ]:
        return [funcao(bruto, prolabore) for _, funcao in self.todos_regimes()]

    def calcular_pj_equivalente_clt(
        self, liquido_clt: float, prolabore: float
    ) -> List[ResultadoPJ]:
        resultados = []
        for _, funcao in self.todos_regimes():
            resultados.append(
                self.encontrar_bruto_por_liquido(liquido_clt, prolabore, funcao)
            )
        return resultados

    def encontrar_bruto_por_liquido(
        self,
        liquido_desejado: float,
        prolabore: float,
        funcao_calculo: Callable[[float, float], ResultadoPJ],
        tolerancia: float = 0.01,
        max_iter: int = 250,
    ) -> ResultadoPJ:
        bruto_min = max(liquido_desejado, 0.01)
        bruto_max = max(liquido_desejado * 3, 1000.0)

        while funcao_calculo(bruto_max, prolabore).liquido < liquido_desejado:
            bruto_max *= 2
            if bruto_max > 100_000_000:
                raise ValueError("Nao foi possivel encontrar um bruto PJ adequado.")

        resultado_final = funcao_calculo(bruto_max, prolabore)
        for _ in range(max_iter):
            bruto_meio = (bruto_min + bruto_max) / 2
            resultado = funcao_calculo(bruto_meio, prolabore)
            diferenca = resultado.liquido - liquido_desejado
            resultado_final = resultado

            if abs(diferenca) <= tolerancia:
                break
            if resultado.liquido < liquido_desejado:
                bruto_min = bruto_meio
            else:
                bruto_max = bruto_meio

        resultado_final.liquido_desejado = liquido_desejado
        resultado_final.diferenca = arredondar(
            resultado_final.liquido - liquido_desejado
        )
        return resultado_final

    def _calcular_simples(
        self,
        nome_regime: str,
        bruto: float,
        prolabore: float,
        faixas: Tuple[FaixaSimples, ...],
    ) -> ResultadoPJ:
        rbt12 = bruto * 12
        aliquota_efetiva = self.aliquota_efetiva_simples(rbt12, faixas)
        simples = bruto * aliquota_efetiva
        inss = self.tributaria.calcular_inss_prolabore(prolabore)
        irrf = self.tributaria.calcular_irrf_prolabore(prolabore)
        liquido = bruto - simples - inss - irrf
        total_encargos = simples + inss + irrf

        return ResultadoPJ(
            regime=nome_regime,
            bruto=arredondar(bruto),
            prolabore=arredondar(prolabore),
            aliquota_efetiva=aliquota_efetiva,
            simples=arredondar(simples),
            inss=inss,
            irrf=irrf,
            liquido=arredondar(liquido),
            total_encargos=arredondar(total_encargos),
        )

# Calculadora CLT

class CalculadoraCLT:
    def __init__(self, tributaria: CalculadoraTributaria | None = None) -> None:
        self.tributaria = tributaria or CalculadoraTributaria()
        self.config = self.tributaria.config

    def simular(self, salario_bruto: float, ajuda_custo: float = 0.0) -> ResultadoCLT:
        inss = self.tributaria.calcular_inss_clt(salario_bruto)
        irrf = self.tributaria.calcular_irrf_clt(salario_bruto)
        fgts = salario_bruto * self.config.aliquota_fgts
        inss_patronal = salario_bruto * self.config.aliquota_patronal
        liquido_mensal = salario_bruto - inss - irrf

        ferias_bruto = salario_bruto + salario_bruto / 3
        ferias_inss = self.tributaria.calcular_inss_clt(ferias_bruto)
        ferias_irrf = self.tributaria.calcular_irrf_clt(ferias_bruto)
        ferias_fgts = ferias_bruto * self.config.aliquota_fgts
        ferias_inss_patronal = ferias_bruto * self.config.aliquota_patronal
        ferias_liquido = ferias_bruto - ferias_inss - ferias_irrf

        decimo_bruto = salario_bruto
        decimo_inss = self.tributaria.calcular_inss_clt(decimo_bruto)
        decimo_irrf = self.tributaria.calcular_irrf_clt(decimo_bruto)
        decimo_fgts = decimo_bruto * self.config.aliquota_fgts
        decimo_inss_patronal = decimo_bruto * self.config.aliquota_patronal
        decimo_liquido = decimo_bruto - decimo_inss - decimo_irrf

        # Provisoes mensais de custo da empresa em regime de competencia.
        provisao_ferias_mensal = ferias_liquido / 12

        provisao_decimo_mensal = decimo_liquido / 12

        custo_fgts_mensal_total = fgts + (ferias_fgts + decimo_fgts) / 12
        
        custo_inss_patronal_mensal_total = (inss_patronal
                                         + (ferias_inss_patronal + decimo_inss_patronal) / 12
        )

        remuneracao_liquida_media_mensal = (
            liquido_mensal
          + ajuda_custo
          + fgts  
          + (ferias_fgts + decimo_fgts) / 12
          + (ferias_liquido + decimo_liquido) /12
        )

        custo_total_empresa_mensal = (
            liquido_mensal
            + ajuda_custo
            + custo_fgts_mensal_total
            + custo_inss_patronal_mensal_total
            + (ferias_liquido + decimo_liquido) / 12
        )

        return ResultadoCLT(
            salario_bruto=arredondar(salario_bruto),
            ajuda_custo=arredondar(ajuda_custo),
            inss=inss,
            irrf=irrf,
            fgts=arredondar(fgts),
            inss_patronal=arredondar(inss_patronal),
            liquido_mensal=arredondar(liquido_mensal),
            liquido_mensal_com_ajuda=arredondar(liquido_mensal + ajuda_custo),
            ferias_bruto=arredondar(ferias_bruto),
            ferias_inss=ferias_inss,
            ferias_irrf=ferias_irrf,
            ferias_fgts=arredondar(ferias_fgts),
            ferias_inss_patronal=arredondar(ferias_inss_patronal),
            ferias_liquido=arredondar(ferias_liquido),
            decimo_bruto=arredondar(decimo_bruto),
            decimo_inss=decimo_inss,
            decimo_irrf=decimo_irrf,
            decimo_fgts=arredondar(decimo_fgts),
            decimo_inss_patronal=arredondar(decimo_inss_patronal),
            decimo_liquido=arredondar(decimo_liquido),
            provisao_ferias_mensal=arredondar(provisao_ferias_mensal),
            provisao_decimo_mensal=arredondar(provisao_decimo_mensal),
            custo_fgts_mensal_total=arredondar(custo_fgts_mensal_total),
            custo_inss_patronal_mensal_total=arredondar(
                custo_inss_patronal_mensal_total
            ),
            custo_total_empresa_mensal=arredondar(custo_total_empresa_mensal),
            remuneracao_liquida_media_mensal=arredondar(
                remuneracao_liquida_media_mensal
            ),
        )

    def calcular_clt_equivalente_pj(
        self,
        liquido_pj: float,
        ajuda_custo: float = 0.0,
        usar_media_anual_clt: bool = False,
        tolerancia: float = 0.01,
        max_iter: int = 250,
    ) -> ResultadoCLT:
        """Encontra o salario bruto CLT que gera liquido equivalente ao PJ.

        Por padrao, compara PJ liquido com o liquido mensal CLT + ajuda de custo.
        Se usar_media_anual_clt=True, compara com liquido mensal + ajuda + 13o/ferias proporcionais.
        """
        bruto_min = 0.01
        bruto_max = max(liquido_pj * 3, 1000.0)

        def liquido_referencia(resultado: ResultadoCLT) -> float:
            return (
                resultado.remuneracao_liquida_media_mensal
                if usar_media_anual_clt
                else resultado.liquido_mensal_com_ajuda
            )

        while liquido_referencia(self.simular(bruto_max, ajuda_custo)) < liquido_pj:
            bruto_max *= 2
            if bruto_max > 100_000_000:
                raise ValueError("Nao foi possivel encontrar um salario CLT adequado.")

        resultado_final = self.simular(bruto_max, ajuda_custo)
        for _ in range(max_iter):
            bruto_meio = (bruto_min + bruto_max) / 2
            resultado = self.simular(bruto_meio, ajuda_custo)
            diferenca = liquido_referencia(resultado) - liquido_pj
            resultado_final = resultado

            if abs(diferenca) <= tolerancia:
                break
            if liquido_referencia(resultado) < liquido_pj:
                bruto_min = bruto_meio
            else:
                bruto_max = bruto_meio

        resultado_final.liquido_desejado = liquido_pj
        resultado_final.diferenca = arredondar(
            liquido_referencia(resultado_final) - liquido_pj
        )
        return resultado_final

# Formatacao de saida

class FormatadorResultado:
    @staticmethod
    def pj(resultado: ResultadoPJ) -> str:
        linhas = [
            f"=== {resultado.regime.upper()} ===",
            f"Bruto / nota fiscal: {formatar_brl(resultado.bruto)}",
            f"Pró-labore: {formatar_brl(resultado.prolabore)}",
        ]
        if resultado.fator_r is not None:
            linhas.append(f"Fator R: {formatar_percentual(resultado.fator_r)}")
        if resultado.aliquota_efetiva:
            linhas.extend(
                [
                    f"Alíquota efetiva: {formatar_percentual(resultado.aliquota_efetiva)}",
                    f"Simples: {formatar_brl(resultado.simples)}",
                ]
            )
        if resultado.total_impostos:
            linhas.extend(
                [
                    f"IRPJ: {formatar_brl(resultado.irpj)}",
                    f"Adicional IRPJ: {formatar_brl(resultado.adicional_irpj)}",
                    f"CSLL: {formatar_brl(resultado.csll)}",
                    f"PIS: {formatar_brl(resultado.pis)}",
                    f"COFINS: {formatar_brl(resultado.cofins)}",
                    f"ISS: {formatar_brl(resultado.iss)}",
                    f"Total impostos PJ: {formatar_brl(resultado.total_impostos)}",
                ]
            )
        linhas.extend(
            [
                f"INSS pró-labore: {formatar_brl(resultado.inss)}",
                f"IRRF pró-labore: {formatar_brl(resultado.irrf)}",
                f"Líquido final PJ: {formatar_brl(resultado.liquido)}",
                f"Total encargos: {formatar_brl(resultado.total_encargos)}",
            ]
        )
        if resultado.liquido_desejado is not None:
            linhas.extend(
                [
                    f"Líquido desejado: {formatar_brl(resultado.liquido_desejado)}",
                    f"Diferença: {formatar_brl(resultado.diferenca or 0.0)}",
                ]
            )
        return "\n".join(linhas)

    @staticmethod
    def clt(resultado: ResultadoCLT) -> str:
        linhas = [
            "=== CLT ===",
            f"Salário bruto: {formatar_brl(resultado.salario_bruto)}",
            f"Ajuda de custo: {formatar_brl(resultado.ajuda_custo)}",
            f"INSS empregado: {formatar_brl(resultado.inss)}",
            f"IRRF: {formatar_brl(resultado.irrf)}",
            f"FGTS mensal: {formatar_brl(resultado.fgts)}",
            f"INSS patronal mensal: {formatar_brl(resultado.inss_patronal)}",
            f"Líquido mensal: {formatar_brl(resultado.liquido_mensal)}",
            f"Líquido mensal + ajuda: {formatar_brl(resultado.liquido_mensal_com_ajuda)}",
            "",
            "=== FÉRIAS ===",
            f"Base férias + 1/3: {formatar_brl(resultado.ferias_bruto)}",
            f"Líquido férias: {formatar_brl(resultado.ferias_liquido)}",
            f"FGTS férias: {formatar_brl(resultado.ferias_fgts)}",
            f"INSS férias: {formatar_brl(resultado.ferias_inss)}",
            f"INSS patronal férias: {formatar_brl(resultado.ferias_inss_patronal)}",
            f"IRRF férias: {formatar_brl(resultado.ferias_irrf)}",
            "",
            "=== 13º SALÁRIO ===",
            f"Base 13º: {formatar_brl(resultado.decimo_bruto)}",
            f"Líquido 13º: {formatar_brl(resultado.decimo_liquido)}",
            f"FGTS 13º: {formatar_brl(resultado.decimo_fgts)}",
            f"INSS 13º: {formatar_brl(resultado.decimo_inss)}",
            f"INSS patronal 13º: {formatar_brl(resultado.decimo_inss_patronal)}",
            f"IRRF 13º: {formatar_brl(resultado.decimo_irrf)}",
            "",
            "=== TOTAIS MENSAIS PROVISIONADOS ===",
            f"Provisão férias mensal: {formatar_brl(resultado.provisao_ferias_mensal)}",
            f"Provisão 13º mensal: {formatar_brl(resultado.provisao_decimo_mensal)}",
            f"FGTS total mensal: {formatar_brl(resultado.custo_fgts_mensal_total)}",
            f"INSS patronal total mensal: {formatar_brl(resultado.custo_inss_patronal_mensal_total)}",
            f"Remuneração líquida média mensal ao empregado: {formatar_brl(resultado.remuneracao_liquida_media_mensal)}",
            f"Custo total mensal para empresa: {formatar_brl(resultado.custo_total_empresa_mensal)}",
        ]
        if resultado.liquido_desejado is not None:
            linhas.extend(
                [
                    f"Líquido desejado: {formatar_brl(resultado.liquido_desejado)}",
                    f"Diferença: {formatar_brl(resultado.diferenca or 0.0)}",
                ]
            )
        return "\n".join(linhas)

    @staticmethod
    def lista_pj(resultados: List[ResultadoPJ]) -> str:
        blocos = [FormatadorResultado.pj(resultado) for resultado in resultados]
        melhor = min(resultados, key=lambda item: item.bruto)
        resumo = [
            "=== MELHOR OPÇÃO POR MENOR BRUTO / NOTA ===",
            f"Regime: {melhor.regime}",
            f"Bruto / nota fiscal: {formatar_brl(melhor.bruto)}",
            f"Líquido final: {formatar_brl(melhor.liquido)}",
            f"Total encargos: {formatar_brl(melhor.total_encargos)}",
        ]
        return "\n\n".join(blocos + ["\n".join(resumo)])

# Interface grafica

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

# Execucao

def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

#PyInstaller.__main__.run([
#  '--noupx',
#   '--name=Calculadora CLT x PJ',             
#    '--icon=favicon.ico',          
#    '--windowed',
#    '--noconsole',
#   'main.py'
#])