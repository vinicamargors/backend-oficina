from core.database import supabase
from datetime import datetime, timedelta

def obter_dados_financeiros(empresa_id: str):
    hoje = datetime.now()
    inicio_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    # 1. Busca todas as OS criadas para o cálculo de faturamento e ticket médio
    os_data = supabase.table("ordens_servico").select("status, total_geral, lucro_estimado").eq("empresa_id", empresa_id).execute().data

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

    # 2. GERAÇÃO HISTÓRICA DOS ÚLTIMOS 6 MESES - Otimizado e limpo, direto no formato de série temporal
    historico = []
    for i in range(5, -1, -1):
        # Avança os meses usando aritmética simples de datas
        mes_ref = hoje.month - i
        ano_ref = hoje.year
        if mes_ref <= 0:
            mes_ref += 12
            ano_ref -= 1
            
        data_inicio_mes = datetime(ano_ref, mes_ref, 1).isoformat()
        # Define o fim do mês adicionando 32 dias e quebrando no dia 1 do próximo mês - 1 segundo
        if mes_ref == 12:
            data_fim_mes = datetime(ano_ref, 12, 31, 23, 59, 59).isoformat()
        else:
            data_fim_mes = (datetime(ano_ref, mes_ref + 1, 1) - timedelta(seconds=1)).isoformat()

        # Busca dados do período no banco
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