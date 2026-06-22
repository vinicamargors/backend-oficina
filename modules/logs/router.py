from fastapi import APIRouter, Depends, Header, HTTPException
from typing import Optional
from uuid import UUID
from . import service
from core.security import validar_passaporte

router = APIRouter(dependencies=[Depends(validar_passaporte)])

def verificar_permissao(x_cargo: str):
    if x_cargo not in ["DONO", "master"]:
        raise HTTPException(status_code=403, detail="Acesso negado. Auditoria é restrita à gestão.")

@router.get("/{empresa_id}")
def get_logs(
    empresa_id: UUID,
    tabela: Optional[str] = None,
    operacao: Optional[str] = None,
    data_ini: Optional[str] = None,
    data_fim: Optional[str] = None,
    x_cargo: str = Header(default="DONO")
):
    verificar_permissao(x_cargo)
    return service.listar_logs(str(empresa_id), tabela, operacao, data_ini, data_fim)

@router.get("/{empresa_id}/exportar")
def exportar_logs(
    empresa_id: UUID,
    data_ini: Optional[str] = None,
    data_fim: Optional[str] = None,
    x_cargo: str = Header(default="DONO")
):
    verificar_permissao(x_cargo)
    return service.exportar_logs_txt(str(empresa_id), data_ini, data_fim)