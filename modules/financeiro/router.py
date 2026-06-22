from fastapi import APIRouter, Header, HTTPException, Depends
from uuid import UUID
from core.security import validar_passaporte
from . import schemas, service

router = APIRouter(dependencies=[Depends(validar_passaporte)])

@router.get("/{empresa_id}", response_model=schemas.FinanceiroResponse)
def get_dados_financeiros(empresa_id: UUID, x_cargo: str = Header(default="MECANICO")):
    # VALIDAÇÃO DE CLASSE: Mecânico não mete o dedo no caixa da empresa!
    if x_cargo not in ["DONO", "FINANCEIRO", "master"]:
        raise HTTPException(
            status_code=403, 
            detail="Acesso negado pelo livre mercado. Você não tem permissão para visualizar o caixa da empresa."
        )
    return service.get_dados_financeiros(str(empresa_id))