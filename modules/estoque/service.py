from fastapi import HTTPException
from core.database import supabase
from .schemas import EstoqueCreate, EstoqueUpdate, EstoqueAjuste
from core.audit import salvar_audit_log

def listar_estoque(empresa_id: str, categoria: str = None):
    query = supabase.table("estoque").select("*").eq("empresa_id", empresa_id)
    if categoria:
        query = query.eq("categoria", categoria.upper())
    
    itens = query.order("nome").execute().data

    # Cálculo financeiro bruto. 
    estoque_baixo = sum(1 for i in itens if i["quantidade"] <= i.get("minimo_alerta", 5))
    valor_custo = sum(i["quantidade"] * i["custo"] for i in itens)
    valor_venda = sum(i["quantidade"] * i["venda"] for i in itens)

    return {
        "itens": itens,
        "stats": {
            "total_itens": len(itens),
            "estoque_baixo": estoque_baixo,
            "valor_total_custo": round(valor_custo, 2),
            "valor_total_venda": round(valor_venda, 2)
        }
    }

def obter_item(item_id: str, empresa_id: str):
    response = supabase.table("estoque").select("*").eq("id", item_id).eq("empresa_id", empresa_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Item não encontrado no estoque.")
    return response.data[0]

def criar_item(dados: EstoqueCreate):
    dados.nome = dados.nome.strip()
    
    # Validação contra redundância no sistema
    duplicado = supabase.table("estoque").select("id").eq("nome", dados.nome).eq("categoria", dados.categoria).eq("empresa_id", str(dados.empresa_id)).execute()
    if duplicado.data:
        raise HTTPException(status_code=409, detail=f"O item '{dados.nome}' já existe na categoria {dados.categoria}.")

    response = supabase.table("estoque").insert(dados.model_dump(mode='json')).execute()
    novo_item = response.data[0]
    
    salvar_audit_log("estoque", "INSERT", novo_item["id"], dados.empresa_id, antes=None, depois=novo_item)
    return novo_item

def atualizar_item(item_id: str, empresa_id: str, dados: EstoqueUpdate):
    estado_anterior = obter_item(item_id, empresa_id)
    
    if dados.nome:
        dados.nome = dados.nome.strip()
        
    campos_alterados = dados.model_dump(exclude_unset=True, mode='json')
    if not campos_alterados:
        return estado_anterior

    response = supabase.table("estoque").update(campos_alterados).eq("id", item_id).eq("empresa_id", empresa_id).execute()
    estado_posterior = response.data[0]
    
    salvar_audit_log("estoque", "UPDATE", item_id, empresa_id, antes=estado_anterior, depois=estado_posterior)
    return estado_posterior

def deletar_item(item_id: str, empresa_id: str):
    estado_anterior = obter_item(item_id, empresa_id)
    
    # O Supabase vai gritar se tiver OS usando e o core/errors.py vai traduzir pra 400.
    supabase.table("estoque").delete().eq("id", item_id).eq("empresa_id", empresa_id).execute()
    
    salvar_audit_log("estoque", "DELETE", item_id, empresa_id, antes=estado_anterior, depois=None)
    return {"status": "sucesso", "detail": "Item varrido do mapa logístico."}

def ajustar_estoque(item_id: str, empresa_id: str, ajuste: EstoqueAjuste):
    estado_anterior = obter_item(item_id, empresa_id)
    qtd_atual = estado_anterior["quantidade"]
    
    if ajuste.tipo == "entrada":
        nova_qtd = qtd_atual + ajuste.quantidade
    else:
        nova_qtd = max(0, qtd_atual - ajuste.quantidade) # Nunca deixa ficar negativo

    response = supabase.table("estoque").update({"quantidade": nova_qtd}).eq("id", item_id).eq("empresa_id", empresa_id).execute()
    estado_posterior = response.data[0]
    
    salvar_audit_log("estoque", "AJUSTE", item_id, empresa_id, antes=estado_anterior, depois=estado_posterior)
    return estado_posterior