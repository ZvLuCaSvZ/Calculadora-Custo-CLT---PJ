from __future__ import annotations

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