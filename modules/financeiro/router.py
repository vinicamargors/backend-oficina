from fastapi import APIRouter, Header, HTTPException, Depends, Query
from typing import Optional
from uuid import UUID
from core.security import validar_passaporte
from . import schemas, service

router = APIRouter(dependencies=[Depends(validar_passaporte)])

@router.get("/{empresa_id}", response_model=schemas.FinanceiroResponse)
def get_dados_financeiros(
    empresa_id: UUID, 
    data_inicial: Optional[str] = Query(None, description="Filtro de data inicial (YYYY-MM-DD)"),
    data_final: Optional[str] = Query(None, description="Filtro de data final (YYYY-MM-DD)"),
    x_cargo: str = Header(default="MECANICO")
):
    # VALIDAÇÃO DE CLASSE: Mecânico não mete o dedo no caixa da empresa!
    if x_cargo not in ["DONO", "FINANCEIRO", "master"]:
        raise HTTPException(
            status_code=403, 
            detail="Acesso negado pelo livre mercado. Você não tem permissão para visualizar o caixa."
        )
    
    # Passamos os filtros de tempo para o motor financeiro
    return service.obter_dados_financeiros(str(empresa_id), data_inicial, data_final)

@router.get("/inteligencia/{empresa_id}", response_model=schemas.InteligenciaFinanceiraResponse)
def get_inteligencia_financeira(
    empresa_id: UUID, 
    data_inicial: Optional[str] = Query(None, description="YYYY-MM-DD"),
    data_final: Optional[str] = Query(None, description="YYYY-MM-DD"),
    x_cargo: str = Header(default="MECANICO")
):
    if x_cargo not in ["DONO", "FINANCEIRO", "master"]:
        raise HTTPException(
            status_code=403, 
            detail="Acesso negado. Apenas a alta cúpula tem acesso à inteligência estratégica."
        )
    
    return service.obter_inteligencia_financeira(str(empresa_id), data_inicial, data_final)