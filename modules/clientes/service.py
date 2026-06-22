from core.database import supabase
from .schemas import ClienteCreate, ClienteUpdate
from fastapi import HTTPException
from postgrest.exceptions import APIError
from core.audit import salvar_audit_log

def listar_clientes_por_empresa(empresa_id: str):
    response = supabase.table("clientes").select("*").eq("empresa_id", empresa_id).execute()
    return response.data

def obter_cliente_por_id(cliente_id: str, empresa_id: str):
    response = supabase.table("clientes").select("*").eq("id", cliente_id).eq("empresa_id", empresa_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Cliente não encontrado na sua jurisdição.")
    return response.data[0]

def criar_novo_cliente(dados: ClienteCreate):
    response = supabase.table("clientes").insert(dados.model_dump(mode='json')).execute()
    if not response.data:
        raise HTTPException(status_code=400, detail="Falha ao registrar propriedade do cliente.")
    
    novo_cliente = response.data[0]
    # INSERT: Não existia dado 'antes'
    salvar_audit_log("clientes", "INSERT", novo_cliente["id"], dados.empresa_id, antes=None, depois=novo_cliente)
    return novo_cliente

def atualizar_cliente(cliente_id: str, empresa_id: str, dados: ClienteUpdate):
    # 1. Captura o estado atual antes da mudança
    estado_anterior = obter_cliente_por_id(cliente_id, empresa_id)
    
    # 2. Filtra apenas os campos que o front enviou de fato para alteração
    campos_alterados = dados.model_dump(exclude_unset=True, mode='json')
    if not campos_alterados:
        return estado_anterior # Nada a mudar, economiza processamento

    response = supabase.table("clientes").update(campos_alterados).eq("id", cliente_id).eq("empresa_id", empresa_id).execute()
    if not response.data:
        raise HTTPException(status_code=400, detail="Erro ao processar atualização.")
    
    estado_posterior = response.data[0]
    # Salva o log com o 'antes' e o 'depois' perfeitamente mapeados
    salvar_audit_log("clientes", "UPDATE", cliente_id, empresa_id, antes=estado_anterior, depois=estado_posterior)
    return estado_posterior

def deletar_cliente(cliente_id: str, empresa_id: str):
    estado_anterior = obter_cliente_por_id(cliente_id, empresa_id)
    
    # Se der erro de foreign key, o FastAPI intercepta e devolve a mensagem do core/errors.py automaticamente!
    supabase.table("clientes").delete().eq("id", cliente_id).eq("empresa_id", empresa_id).execute()
    
    salvar_audit_log("clientes", "DELETE", cliente_id, empresa_id, antes=estado_anterior, depois=None)
    return {"status": "sucesso", "detail": "Cliente removido e log gerado."}