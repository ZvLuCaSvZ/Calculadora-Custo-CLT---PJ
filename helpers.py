from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Dict, List, Optional, Tuple


from utils import (
    arredondar,
    formatar_brl,
    formatar_percentual,
)

from config import (
    ConfigTributaria,
    FaixaSimples, 
    FaixaProgressiva,
    ResultadoPJ,
    ResultadoCLT,
)

# Calcula o INSS e IRRF para o Pró-Labore e o CLT. 
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


# Calculo dos imposto e custo do PJ.
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


# Calculo dos imposto e custo do CLT.   
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
    

# Apresentar os resultados na tela seguinda a formatação da classe
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