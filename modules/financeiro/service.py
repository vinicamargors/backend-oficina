from core.database import supabase
from datetime import datetime, timedelta

def obter_dados_financeiros(empresa_id: str, data_inicial: str = None, data_final: str = None):
    hoje = datetime.now()

    # 1. Busca as OS com a liberdade do filtro de período
    query = supabase.table("ordens_servico").select("status, total_geral, lucro_estimado").eq("empresa_id", empresa_id)
    
    # Aplicando a tesoura do tempo (Se o usuário enviou os filtros)
    if data_inicial:
        query = query.gte("data_abertura", f"{data_inicial}T00:00:00")
    if data_final:
        query = query.lte("data_abertura", f"{data_final}T23:59:59")
        
    os_data = query.execute().data

    faturamento_pago = 0.0
    faturamento_projetado = 0.0
    lucro_realizado = 0.0
    total_os_concluidas = 0

    for os in os_data:
        status = os.get("status")
        total = float(os.get("total_geral") or 0.0)
        lucro = float(os.get("lucro_estimado") or 0.0)

        if status == "PAGO":
            faturamento_pago += total
            lucro_realizado += lucro
            total_os_concluidas += 1
        elif status in ["EXECUCAO", "FINALIZADO"]:
            faturamento_projetado += total

    ticket_medio = (faturamento_pago / total_os_concluidas) if total_os_concluidas > 0 else 0.0

    # 2. GERAÇÃO HISTÓRICA DOS ÚLTIMOS 6 MESES (Mantemos fixo para o gráfico de tendência)
    historico = []
    for i in range(5, -1, -1):
        mes_ref = hoje.month - i
        ano_ref = hoje.year
        if mes_ref <= 0:
            mes_ref += 12
            ano_ref -= 1
            
        data_inicio_mes = datetime(ano_ref, mes_ref, 1).isoformat()
        if mes_ref == 12:
            data_fim_mes = datetime(ano_ref, 12, 31, 23, 59, 59).isoformat()
        else:
            data_fim_mes = (datetime(ano_ref, mes_ref + 1, 1) - timedelta(seconds=1)).isoformat()

        # Busca dados do período blindado para o gráfico
        os_periodo = supabase.table("ordens_servico").select("total_geral, lucro_estimado").eq("empresa_id", empresa_id).eq("status", "PAGO").gte("data_abertura", data_inicio_mes).lte("data_abertura", data_fim_mes).execute().data
        
        fat_mes = sum(float(o.get("total_geral") or 0.0) for o in os_periodo)
        lucro_mes = sum(float(o.get("lucro_estimado") or 0.0) for o in os_periodo)

        historico.append({
            "mes_ano": f"{mes_ref:02d}/{ano_ref}",
            "faturamento": round(fat_mes, 2),
            "lucro": round(lucro_mes, 2)
        })

    return {
        "faturamento_pago": round(faturamento_pago, 2),
        "faturamento_projetado": round(faturamento_projetado, 2),
        "lucro_realizado": round(lucro_realizado, 2),
        "ticket_medio": round(ticket_medio, 2),
        "historico_6_meses": historico
    }

def obter_inteligencia_financeira(empresa_id: str, data_inicial: str = None, data_final: str = None):
    # Puxa o dossiê massivo das OS com todos os joins necessários
    query = supabase.table("ordens_servico").select(
        "id, status, total_geral, total_pecas, total_mao_obra, lucro_estimado, data_abertura, data_fechamento, forma_pagamento",
        "clientes(id, nome)",
        "veiculos(id, placa, marca, modelo, ano)",
        "usuarios(id, nome)" # O Mecânico
    ).eq("empresa_id", empresa_id)

    if data_inicial:
        query = query.gte("data_abertura", f"{data_inicial}T00:00:00")
    if data_final:
        query = query.lte("data_abertura", f"{data_final}T23:59:59")

    os_list = query.execute().data

    # Agregadores capitalistas
    clientes_aggr = {}
    mecanicos_aggr = {}
    pagamentos_aggr = {}
    marcas_aggr = {}
    
    lead_times_horas = []
    
    total_faturado_pecas = 0.0
    total_faturado_mao_obra = 0.0
    
    total_orcamentos = 0
    total_aprovados = 0

    for os in os_list:
        status = os.get("status")
        
        # Métrica de Conversão de Vendas
        total_orcamentos += 1
        if status in ["EXECUCAO", "FINALIZADO", "PAGO"]:
            total_aprovados += 1

        # A partir daqui, só interessa o que gerou trabalho ou dinheiro real
        if status not in ["FINALIZADO", "PAGO"]:
            continue 

        lucro = float(os.get("lucro_estimado") or 0.0)
        faturamento = float(os.get("total_geral") or 0.0)
        
        total_faturado_pecas += float(os.get("total_pecas") or 0.0)
        total_faturado_mao_obra += float(os.get("total_mao_obra") or 0.0)

        # 1. Ranking de Clientes
        cli = os.get("clientes")
        if cli:
            cid = cli["id"]
            if cid not in clientes_aggr:
                clientes_aggr[cid] = {"nome": cli["nome"], "lucro": 0.0, "faturamento": 0.0, "qtd_os": 0}
            clientes_aggr[cid]["lucro"] += lucro
            clientes_aggr[cid]["faturamento"] += faturamento
            clientes_aggr[cid]["qtd_os"] += 1

        # 2. Produtividade por Mecânico
        usr = os.get("usuarios")
        if usr:
            uid = usr["id"]
            if uid not in mecanicos_aggr:
                mecanicos_aggr[uid] = {"nome": usr["nome"], "lucro_gerado": 0.0, "faturamento_gerado": 0.0, "qtd_os": 0}
            mecanicos_aggr[uid]["lucro_gerado"] += lucro
            mecanicos_aggr[uid]["faturamento_gerado"] += faturamento
            mecanicos_aggr[uid]["qtd_os"] += 1

        # 3. Métodos de Pagamento
        forma = os.get("forma_pagamento")
        if forma:
            if forma not in pagamentos_aggr:
                pagamentos_aggr[forma] = {"forma": forma, "qtd": 0, "valor_total": 0.0}
            pagamentos_aggr[forma]["qtd"] += 1
            pagamentos_aggr[forma]["valor_total"] += faturamento

        # 4. Rentabilidade por Marca de Veículo
        vei = os.get("veiculos")
        if vei:
            marca = vei.get("marca") or "Não Informada"
            marca = marca.upper().strip()
            if marca not in marcas_aggr:
                marcas_aggr[marca] = {"marca": marca, "lucro": 0.0, "faturamento": 0.0, "qtd_os": 0}
            marcas_aggr[marca]["lucro"] += lucro
            marcas_aggr[marca]["faturamento"] += faturamento
            marcas_aggr[marca]["qtd_os"] += 1

        # 5. Lead Time (O tempo é inimigo do lucro)
        dt_abertura = os.get("data_abertura")
        dt_fechamento = os.get("data_fechamento")
        if dt_abertura and dt_fechamento:
            try:
                # Limpa o 'Z' maldito do formato ISO para o Python ler nativo
                t1 = datetime.fromisoformat(dt_abertura.replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(dt_fechamento.replace("Z", "+00:00"))
                horas = (t2 - t1).total_seconds() / 3600.0
                if horas >= 0:
                    lead_times_horas.append(horas)
            except Exception:
                pass

    # Processamento Final das Listas (A Mão Invisível peneirando os dados)
    
    # Clientes sanguessugas vs Clientes de Ouro
    clientes_sorted = sorted(clientes_aggr.values(), key=lambda x: x["lucro"], reverse=True)
    top_10 = clientes_sorted[:10]
    # Piores clientes: Pegamos o final da lista invertido, ignorando quem não deu lucro nenhum ou prejuízo
    piores_10 = sorted(clientes_aggr.values(), key=lambda x: x["lucro"])[:10] 

    mec_sorted = sorted(mecanicos_aggr.values(), key=lambda x: x["lucro_gerado"], reverse=True)
    marcas_sorted = sorted(marcas_aggr.values(), key=lambda x: x["lucro"], reverse=True)

    avg_lead_time = round(sum(lead_times_horas) / len(lead_times_horas), 1) if lead_times_horas else 0.0
    taxa_conversao = round((total_aprovados / total_orcamentos) * 100, 1) if total_orcamentos > 0 else 0.0

    return {
        "top_10_clientes": top_10,
        "piores_10_clientes": piores_10,
        "produtividade_mecanicos": mec_sorted,
        "metodos_pagamento": list(pagamentos_aggr.values()),
        "rentabilidade_marcas": marcas_sorted,
        "origem_faturamento": {
            "pecas": total_faturado_pecas,
            "mao_obra": total_faturado_mao_obra
        },
        "lead_time_medio_horas": avg_lead_time,
        "taxa_conversao_orcamentos": taxa_conversao
    }