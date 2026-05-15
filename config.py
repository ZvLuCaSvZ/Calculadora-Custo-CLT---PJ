from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Dict, List, Optional, Tuple


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