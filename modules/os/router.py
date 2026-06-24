from fastapi import APIRouter, Depends, Query
from typing import Optional
from uuid import UUID
from . import schemas, service
from core.security import validar_passaporte

router = APIRouter(dependencies=[Depends(validar_passaporte)])

@router.post("/", response_model=dict)
def criar_ordem_servico(os: schemas.OSCreate):
    return service.criar_os(os)

@router.get("/")
def listar_ordens_servico(
    empresa_id: UUID = Query(..., description="ID da empresa (Obrigatório para isolar os dados)"),
    status: Optional[str] = Query(None, description="Filtra por: ORCAMENTO, EXECUCAO, FINALIZADO, PAGO"),
    search: Optional[str] = Query(None, description="Busca rápida por placa, ID ou nome do cliente"),
    skip: int = Query(0, description="Para paginação: quantos registos pular"),
    limit: int = Query(50, description="Limite de registos por ecrã")
):
    """
    Retorna a esteira de valor da oficina. 
    Apenas as OS da empresa informada.
    """
    return service.listar_os(
        empresa_id=str(empresa_id), 
        status=status, 
        search=search, 
        skip=skip, 
        limit=limit
    )

@router.put("/{empresa_id}/{os_id}")
def atualizar_ordem_servico(empresa_id: UUID, os_id: UUID, os: schemas.OSUpdate):
    return service.atualizar_os(str(os_id), str(empresa_id), os)

@router.delete("/{empresa_id}/{os_id}")
def deletar_ordem_servico(empresa_id: UUID, os_id: UUID):
    return service.deletar_os(str(os_id), str(empresa_id))

# --- Sub-rotas de Itens da OS ---
@router.post("/{empresa_id}/{os_id}/itens")
def adicionar_item_os(empresa_id: UUID, os_id: UUID, item: schemas.OSItemCreate):
    return service.adicionar_item(str(os_id), str(empresa_id), item)

@router.delete("/{empresa_id}/{os_id}/itens/{item_id}")
def remover_item_os(empresa_id: UUID, os_id: UUID, item_id: UUID):
    return service.remover_item(str(os_id), str(item_id), str(empresa_id))

@router.get("/{empresa_id}/{os_id}/imprimir", response_model=schemas.OSDossieResponse)
def imprimir_os(empresa_id: UUID, os_id: UUID):
    return service.obter_dossie_impressao(str(os_id), str(empresa_id))