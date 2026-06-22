from pydantic import BaseModel
from typing import List, Dict

class SerieTemporalMes(BaseModel):
    mes_ano: str
    faturamento: float
    lucro: float

class FinanceiroResponse(BaseModel):
    faturamento_pago: float     # Dinheiro real no caixa (Status PAGO)
    faturamento_projetado: float # Dinheiro que vai entrar (Status EXECUCAO, FINALIZADO)
    lucro_realizado: float       # Lucro real das OS Pagas
    ticket_medio: float          # Quanto cada carro deixa em média na oficina
    historico_6_meses: List[SerieTemporalMes]