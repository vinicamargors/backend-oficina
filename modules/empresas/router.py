from fastapi import APIRouter, Depends, Header, HTTPException
from typing import Optional
from uuid import UUID
from . import schemas, service
from core.security import validar_passaporte

router = APIRouter(dependencies=[Depends(validar_passaporte)])

def check_master(x_cargo: str):
    if x_cargo != "master":
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas o Master da plataforma tem essa permissão.")

@router.get("/")
def get_empresas(empresa_id: Optional[UUID] = None, x_cargo: str = Header(default="DONO")):
    return service.listar_empresas(x_cargo, str(empresa_id) if empresa_id else "")

@router.get("/{empresa_id}/detalhes")
def get_detalhes_empresa(empresa_id: UUID, x_cargo: str = Header(default="master")):
    check_master(x_cargo)
    return service.obter_detalhes(str(empresa_id))

@router.post("/", response_model=schemas.EmpresaResponse)
def post_empresa(empresa: schemas.EmpresaCreate, x_cargo: str = Header(default="master")):
    check_master(x_cargo)
    return service.criar_empresa(empresa)

@router.put("/{empresa_id}")
def put_empresa(empresa_id: UUID, empresa: schemas.EmpresaUpdate, x_cargo: str = Header(default="DONO")):
    return service.atualizar_empresa(str(empresa_id), x_cargo, empresa)

@router.delete("/{empresa_id}")
def delete_empresa(empresa_id: UUID, x_cargo: str = Header(default="master")):
    check_master(x_cargo)
    return service.deletar_empresa(str(empresa_id))

@router.put("/{empresa_id}/configuracoes")
def put_configuracoes(empresa_id: UUID, config: schemas.ConfigUpdate):
    return service.atualizar_configuracoes(str(empresa_id), config)