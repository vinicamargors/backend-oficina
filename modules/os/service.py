from fastapi import HTTPException
from core.database import supabase
from datetime import datetime
from .schemas import OSCreate, OSUpdate, OSItemCreate
from core.audit import salvar_audit_log

# modules/os/service.py

def listar_os(empresa_id: str, status: str = None, search: str = None, skip: int = 0, limit: int = 50):
    """O Radar do Pátio: Puxa as OS com paginação pesada e auditoria de volume total."""
    
    # A Mágica: pedimos ao Supabase para contar os registros exatos (count="exact")
    query = supabase.table("ordens_servico").select(
        "id, status, data_abertura, total_geral, descricao_problema, clientes(nome, telefone), veiculos(placa, modelo)",
        count="exact" 
    ).eq("empresa_id", empresa_id)

    if status:
        query = query.eq("status", status.upper())

    query = query.order("data_abertura", desc=True)

    # 1. MODO BUSCA ATIVADA (Filtro em memória com contagem própria)
    if search:
        response = query.limit(1000).execute()
        todas_os = response.data
        termo = search.lower()
        filtradas = []
        
        for os in todas_os:
            clientes = os.get("clientes") or {}
            veiculos = os.get("veiculos") or {}
            
            cli_nome = str(clientes.get("nome", "")).lower()
            vei_placa = str(veiculos.get("placa", "")).lower()
            os_id = str(os.get("id", "")).lower()
            desc = str(os.get("descricao_problema", "")).lower()
            
            if termo in cli_nome or termo in vei_placa or termo in os_id or termo in desc:
                filtradas.append(os)
        
        total_real = len(filtradas)
        return {
            "items": filtradas[skip : skip + limit],
            "total": total_real,
            "skip": skip,
            "limit": limit
        }

    # 2. MODO LISTAGEM PADRÃO (O banco faz o trabalho pesado de contar e paginar)
    response = query.range(skip, skip + limit - 1).execute()
    
    return {
        "items": response.data,
        "total": response.count or 0, # O Supabase devolve o total exato aqui
        "skip": skip,
        "limit": limit
    }

def recalcular_totais_os(os_id: str):
    """Mão invisível que ajusta o faturamento da OS automaticamente"""
    itens = supabase.table("os_itens").select("*").eq("os_id", os_id).execute().data
    
    total_pecas = sum(i["quantidade"] * i["venda_unitario"] for i in itens if i["tipo"] in ["PECA", "TERCEIRIZADO"])
    total_mao_obra = sum(i["quantidade"] * i["venda_unitario"] for i in itens if i["tipo"] == "MAO_OBRA")
    
    # REGRA CAPITALISTA: Mão de obra é puro suor, não tem custo de mercadoria! (Ignoramos o custo dela)
    custo_total = sum(i["quantidade"] * i["custo_unitario"] for i in itens if i["tipo"] != "MAO_OBRA")
    
    venda_total = total_pecas + total_mao_obra
    lucro = venda_total - custo_total

    supabase.table("ordens_servico").update({
        "total_pecas": total_pecas,
        "total_mao_obra": total_mao_obra,
        "total_geral": venda_total,
        "lucro_estimado": lucro
    }).eq("id", os_id).execute()

def criar_os(dados: OSCreate):
    # Regra 1: Evitar fraude/duplicidade de OS em orçamento pro mesmo carro
    os_aberta = supabase.table("ordens_servico").select("id").eq("veiculo_id", str(dados.veiculo_id)).eq("status", "ORCAMENTO").eq("empresa_id", str(dados.empresa_id)).execute()
    if os_aberta.data:
        raise HTTPException(status_code=409, detail="Este veículo já possui um orçamento aberto na oficina.")

    # Regra 2: Atualizar o KM do carro se o informado for maior
    if dados.km_atual:
        veiculo = supabase.table("veiculos").select("km_atual").eq("id", str(dados.veiculo_id)).execute().data[0]
        if not veiculo.get("km_atual") or dados.km_atual > veiculo["km_atual"]:
            supabase.table("veiculos").update({"km_atual": dados.km_atual}).eq("id", str(dados.veiculo_id)).execute()

    response = supabase.table("ordens_servico").insert(dados.model_dump(mode='json')).execute()
    nova_os = response.data[0]
    salvar_audit_log("ordens_servico", "INSERT", nova_os["id"], dados.empresa_id, antes=None, depois=nova_os)
    return nova_os

def atualizar_os(os_id: str, empresa_id: str, dados: OSUpdate):
    os_atual = supabase.table("ordens_servico").select("*").eq("id", os_id).eq("empresa_id", empresa_id).execute().data[0]
    campos = dados.model_dump(exclude_unset=True, mode='json')
    
    if not campos:
        return os_atual

    # REGRA ANCAP AQUI: Se a KM mudou na tela, a gente OBRIGA a tabela de veículos a atualizar!
    if "km_atual" in campos and campos["km_atual"]:
        veiculo_id = os_atual["veiculo_id"]
        veiculo = supabase.table("veiculos").select("km_atual").eq("id", str(veiculo_id)).execute().data[0]
        # Só atualiza se o KM novo for maior que o antigo (ou se antes estava zerado)
        if not veiculo.get("km_atual") or campos["km_atual"] > veiculo["km_atual"]:
            supabase.table("veiculos").update({"km_atual": campos["km_atual"]}).eq("id", str(veiculo_id)).execute()

    # Regra de negócio: Bateu o martelo, registra a data de fechamento
    if "status" in campos and campos["status"] in ["FINALIZADO", "PAGO"] and not os_atual.get("data_fechamento"):
        campos["data_fechamento"] = datetime.now().isoformat()

    response = supabase.table("ordens_servico").update(campos).eq("id", os_id).execute()
    os_nova = response.data[0]
    salvar_audit_log("ordens_servico", "UPDATE", os_id, empresa_id, antes=os_atual, depois=os_nova)
    return os_nova

def adicionar_item(os_id: str, empresa_id: str, item: OSItemCreate):
    # Se a peça vem do estoque, o mercado cobra a conta: tem que ter saldo.
    if item.estoque_id:
        estoque = supabase.table("estoque").select("*").eq("id", str(item.estoque_id)).eq("empresa_id", empresa_id).execute().data[0]
        if estoque["quantidade"] < item.quantidade:
            raise HTTPException(status_code=400, detail=f"Estoque insuficiente. Saldo atual: {estoque['quantidade']}")
        
        # Dá baixa no estoque
        supabase.table("estoque").update({"quantidade": estoque["quantidade"] - item.quantidade}).eq("id", str(item.estoque_id)).execute()

    dados_item = item.model_dump(mode='json')
    dados_item.update({"os_id": os_id, "empresa_id": empresa_id})
    
    response = supabase.table("os_itens").insert(dados_item).execute()
    recalcular_totais_os(os_id)
    return response.data[0]

def remover_item(os_id: str, item_id: str, empresa_id: str):
    item = supabase.table("os_itens").select("*").eq("id", item_id).eq("empresa_id", empresa_id).execute().data
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    item = item[0]

    # Estorno de propriedade: Devolve pro estoque se saiu de lá
    if item.get("estoque_id"):
        estoque = supabase.table("estoque").select("quantidade").eq("id", item["estoque_id"]).execute().data[0]
        supabase.table("estoque").update({"quantidade": estoque["quantidade"] + item["quantidade"]}).eq("id", item["estoque_id"]).execute()

    supabase.table("os_itens").delete().eq("id", item_id).execute()
    recalcular_totais_os(os_id)
    return {"status": "sucesso", "detail": "Item removido e estornado (se aplicável)."}

def deletar_os(os_id: str, empresa_id: str, motivo_exclusao: str):
    # Antes de queimar o arquivo, devolve as peças pro estoque
    itens = supabase.table("os_itens").select("id").eq("os_id", os_id).eq("empresa_id", empresa_id).execute().data
    for i in itens:
        remover_item(os_id, i["id"], empresa_id)

    # Pega a "foto" da OS como ela era antes da morte
    os_atual = supabase.table("ordens_servico").select("*").eq("id", os_id).execute().data[0]
    
    # INJEÇÃO CAPITALISTA: Colocamos o motivo dentro da foto para a auditoria pegar!
    os_atual["motivo_exclusao"] = motivo_exclusao

    # Executa a OS
    supabase.table("ordens_servico").delete().eq("id", os_id).execute()
    
    # Salva o log blindado
    salvar_audit_log("ordens_servico", "DELETE", os_id, empresa_id, antes=os_atual, depois=None)
    
    return {"status": "sucesso", "detail": "OS cancelada, estoque restaurado e log gerado."}


def obter_dossie_impressao(os_id: str, empresa_id: str):
    # O Supabase traz a OS e já faz o JOIN com clientes, veiculos e usuarios(mecânico)
    response_os = supabase.table("ordens_servico").select(
        "*, clientes(nome, telefone, cpf_cnpj, endereco), veiculos(placa, modelo, marca, cor, ano, chassi, km_atual), usuarios(nome)"
    ).eq("id", os_id).eq("empresa_id", empresa_id).execute()

    if not response_os.data:
        raise HTTPException(status_code=404, detail="Ordem de Serviço não encontrada.")
    
    ordem_completa = response_os.data[0]

    # Busca os itens da nota
    itens = supabase.table("os_itens").select("*").eq("os_id", os_id).execute().data

    # Busca os dados da matriz (oficina) para sair no cabeçalho da impressão
    empresa = supabase.table("empresas").select(
        "nome_fantasia, razao_social, cnpj, telefone, email, endereco"
    ).eq("id", empresa_id).execute().data

    # Retorna o pacote completo pronto para a gráfica do Frontend
    return {
        "ordem": ordem_completa,
        "itens": itens,
        "empresa": empresa[0] if empresa else {}
    }