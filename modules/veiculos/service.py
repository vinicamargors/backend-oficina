import os
import httpx
from fastapi import HTTPException
from core.database import supabase
from .schemas import VeiculoCreate, VeiculoUpdate
from core.audit import salvar_audit_log

async def consultar_placa_externa(placa: str):
    token = os.getenv("WDAPIPLACAS_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="Token da API de placas não configurado no .env")
    
    # Chamada assíncrona: alta performance, não trava a esteira da fábrica
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"https://wdapi2.com.br/consulta/{placa}/{token}", timeout=5.0)
            if r.status_code == 200:
                dados = r.json()
                return {
                    "marca": dados.get("MARCA") or dados.get("marca", ""),
                    "modelo": dados.get("MODELO") or dados.get("modelo", ""),
                    "cor": dados.get("cor", ""),
                    "ano": dados.get("ano", ""),
                    "chassi": dados.get("chassi", "")
                }
            raise HTTPException(status_code=404, detail="Placa não encontrada no mercado.")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Serviço de consulta de placas indisponível.")

def listar_veiculos(empresa_id: str, placa: str = None):
    query = supabase.table("veiculos").select("*, clientes(nome, telefone)").eq("empresa_id", empresa_id)
    if placa:
        query = query.eq("placa", placa.upper())
    
    response = query.order("placa").execute()
    return response.data

def obter_veiculo_por_id(veiculo_id: str, empresa_id: str):
    response = supabase.table("veiculos").select("*").eq("id", veiculo_id).eq("empresa_id", empresa_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Veículo não encontrado.")
    return response.data[0]

def criar_veiculo(dados: VeiculoCreate):
    dados.placa = dados.placa.upper().strip()
    
    # Trava contra fraudes: sem placa duplicada na mesma empresa
    duplicado = supabase.table("veiculos").select("id").eq("placa", dados.placa).eq("empresa_id", str(dados.empresa_id)).execute()
    if duplicado.data:
        raise HTTPException(status_code=409, detail=f"Veículo com placa {dados.placa} já registrado.")

    # Sem try-except! Se o cliente_id não existir, o core/errors.py devolve a resposta.
    response = supabase.table("veiculos").insert(dados.model_dump(mode='json')).execute()
    novo_veiculo = response.data[0]
    
    salvar_audit_log("veiculos", "INSERT", novo_veiculo["id"], dados.empresa_id, antes=None, depois=novo_veiculo)
    return novo_veiculo

def atualizar_veiculo(veiculo_id: str, empresa_id: str, dados: VeiculoUpdate):
    estado_anterior = obter_veiculo_por_id(veiculo_id, empresa_id)
    
    if dados.placa:
        dados.placa = dados.placa.upper().strip()
        
    campos_alterados = dados.model_dump(exclude_unset=True, mode='json')
    if not campos_alterados:
        return estado_anterior

    # Sem try-except! Deixa o Supabase barrar e o Global Handler traduzir.
    response = supabase.table("veiculos").update(campos_alterados).eq("id", veiculo_id).eq("empresa_id", empresa_id).execute()
    estado_posterior = response.data[0]
    
    salvar_audit_log("veiculos", "UPDATE", veiculo_id, empresa_id, antes=estado_anterior, depois=estado_posterior)
    return estado_posterior

def deletar_veiculo(veiculo_id: str, empresa_id: str):
    estado_anterior = obter_veiculo_por_id(veiculo_id, empresa_id)
    
    # Deleção limpa. Se tiver OS amarrada, o erro é pego antes de chegar no usuário.
    supabase.table("veiculos").delete().eq("id", veiculo_id).eq("empresa_id", empresa_id).execute()
    
    salvar_audit_log("veiculos", "DELETE", veiculo_id, empresa_id, antes=estado_anterior, depois=None)
    return {"status": "sucesso", "detail": "Veículo removido com sucesso."}