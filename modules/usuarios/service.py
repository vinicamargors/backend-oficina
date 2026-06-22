from fastapi import HTTPException
from core.database import supabase, supabase_admin
from .schemas import UsuarioCreate, UsuarioUpdate
from core.audit import salvar_audit_log

def listar_usuarios(empresa_id: str):
    return supabase.table("usuarios").select("*").eq("empresa_id", empresa_id).order("nome").execute().data

def criar_usuario(dados: UsuarioCreate, empresa_id: str):
    # 1. Cria a blindagem lá na provedora de identidade (Auth)
    try:
        user_auth = supabase_admin.auth.admin.create_user({
            "email": dados.email,
            "password": dados.senha,
            "email_confirm": True
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro na provedora de Auth: {str(e)}")

    # 2. Grava a carteira de trabalho dele no nosso banco
    db_data = {
        "id": user_auth.user.id, # O Chassi vem inviolável direto da matriz
        "nome": dados.nome,
        "email": dados.email,
        "cargo": dados.cargo,
        "ativo": dados.ativo,
        "empresa_id": empresa_id
    }
    response = supabase.table("usuarios").insert(db_data).execute()
    salvar_audit_log("usuarios", "INSERT", user_auth.user.id, empresa_id, antes=None, depois=db_data)
    return response.data[0]

def atualizar_usuario(usuario_id: str, empresa_id: str, dados: UsuarioUpdate):
    estado_anterior = supabase.table("usuarios").select("*").eq("id", usuario_id).eq("empresa_id", empresa_id).execute().data[0]
    if not estado_anterior:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado.")
    # Se mandou senha nova, a gente comunica a provedora de Auth para trocar a fechadura
    if dados.senha:
        try:
            supabase_admin.auth.admin.update_user_by_id(usuario_id, {"password": dados.senha})
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erro ao trocar senha no cofre: {str(e)}")

    # Se mandou e-mail novo, atualiza a identidade no Auth também
    if dados.email:
        try:
            supabase_admin.auth.admin.update_user_by_id(usuario_id, {"email": dados.email, "email_confirm": True})
        except Exception:
            raise HTTPException(status_code=400, detail="Este e-mail já está sendo usado por outro usuário global.")

    # Atualiza o perfil na nossa tabela
    campos = dados.model_dump(exclude={"senha"}, exclude_unset=True, mode='json')
    if not campos:
        return supabase.table("usuarios").select("*").eq("id", usuario_id).execute().data[0]

    response = supabase.table("usuarios").update(campos).eq("id", usuario_id).eq("empresa_id", empresa_id).execute()
    salvar_audit_log("usuarios", "UPDATE", usuario_id, empresa_id, antes=estado_anterior, depois=response.data[0])
    if not response.data:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado.")
    return response.data[0]

def obter_perfil_logado(usuario_id: str):
    # Busca a ficha do cara na NOSSA tabela pública usando o ID que veio do token
    response = supabase.table("usuarios").select("*").eq("id", usuario_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Perfil não encontrado na nossa jurisdição.")
    return response.data[0]