from core.database import supabase

def obter_dashboard_operacional(empresa_id: str):
    # 1. Puxa todas as OS ativas e recentes da oficina de uma vez só
    os_data = supabase.table("ordens_servico").select("status").eq("empresa_id", empresa_id).execute().data
    
    status_counts = {'ORCAMENTO': 0, 'AGUARDANDO_PECA': 0, 'EXECUCAO': 0, 'FINALIZADO': 0, 'PAGO': 0}
    for os in os_data:
        st = os.get("status", "ORCAMENTO")
        if st in status_counts:
            status_counts[st] += 1
            
    total_abertas = status_counts['ORCAMENTO'] + status_counts['AGUARDANDO_PECA'] + status_counts['EXECUCAO']

    # 2. Varre o estoque buscando o que está abaixo do mínimo
    estoque_data = supabase.table("estoque").select("id, nome, quantidade, minimo_alerta, categoria").eq("empresa_id", empresa_id).execute().data
    itens_criticos = [i for i in estoque_data if i["quantidade"] <= i.get("minimo_alerta", 5)]

    # 3. Busca o TOP 5 das últimas ordens de serviço com JOIN em Clientes e Veículos
    ultimas_os = supabase.table("ordens_servico").select(
        "id, status, data_abertura, total_geral, clientes(nome, telefone), veiculos(placa, modelo)"
    ).eq("empresa_id", empresa_id).order("data_abertura", desc=True).limit(5).execute().data

    return {
        "total_abertas": total_abertas,
        "estoque_critico_count": len(itens_criticos),
        "status_counts": status_counts,
        "ultimas_os": ultimas_os,
        "itens_criticos": itens_criticos[:5] # Devolve apenas os 5 mais urgentes pro front não quebrar
    }