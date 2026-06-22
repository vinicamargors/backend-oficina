from fastapi import APIRouter, Depends, Header, HTTPException
from typing import List
from uuid import UUID
from . import schemas, service
from core.security import validar_passaporte


router = APIRouter()

def verificar_permissao(x_cargo: str):
    """Lei do mercado: Só quem tem skin in the game (Dono ou Master) mexe na folha de pagamento."""
    if x_cargo not in ["DONO", "master"]:
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas o Dono da oficina pode gerenciar funcionários.")
    
@router.get("/me", response_model=schemas.UsuarioResponse)
def get_me(usuario_logado: dict = Depends(validar_passaporte)):
    # O validar_passaporte decodificou o JWT e devolveu um dicionário. 
    # A chave 'sub' é o UUID do usuário criado pelo Supabase Auth.
    user_id = usuario_logado.get("sub")
    
    return service.obter_perfil_logado(user_id)

@router.get("/{empresa_id}", response_model=List[schemas.UsuarioResponse])
def get_usuarios(empresa_id: UUID, x_cargo: str = Header(default="DONO", )):
    verificar_permissao(x_cargo)
    return service.listar_usuarios(str(empresa_id))

@router.post("/{empresa_id}", response_model=schemas.UsuarioResponse)
def post_usuario(empresa_id: UUID, usuario: schemas.UsuarioCreate, x_cargo: str = Header(default="DONO",)):
    verificar_permissao(x_cargo)
    return service.criar_usuario(usuario, str(empresa_id))

@router.put("/{empresa_id}/{usuario_id}", response_model=schemas.UsuarioResponse)
def put_usuario(empresa_id: UUID, usuario_id: UUID, usuario: schemas.UsuarioUpdate, x_cargo: str = Header(default="DONO")):
    verificar_permissao(x_cargo)
    return service.atualizar_usuario(str(usuario_id), str(empresa_id), usuario)

