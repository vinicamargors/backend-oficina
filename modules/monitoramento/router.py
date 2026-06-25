from fastapi import APIRouter, Depends, Header, HTTPException
from core.database import supabase
from core.security import validar_passaporte
from datetime import datetime, timedelta

router = APIRouter(dependencies=[Depends(validar_passaporte)])

@router.get("/")
def get_dados_grafana_ancap(x_cargo: str = Header(default="MECANICO")):
    # Acesso estrito e autoritário. Só a cúpula entra.
    if x_cargo != "master":
        raise HTTPException(status_code=403, detail="Acesso restrito. Propriedade confidencial da infraestrutura.")

    hoje = datetime.now()
    ontem = (hoje - timedelta(days=1)).isoformat()

    # 1. Puxa os logs da API das últimas 24h
    logs = supabase.table("api_metrics").select("*").gte("criado_em", ontem).execute().data

    total_requisicoes = len(logs)
    
    # 2. Calcula Tempo Médio de Resposta
    tempo_medio = sum(log["tempo_ms"] for log in logs) / total_requisicoes if total_requisicoes > 0 else 0

    # 3. Descobre a Rota mais lenta (O Gargalo)
    rotas_agrupadas = {}
    for log in logs:
        r = log["rota"]
        if r not in rotas_agrupadas:
            rotas_agrupadas[r] = {"chamadas": 0, "tempo_total": 0}
        rotas_agrupadas[r]["chamadas"] += 1
        rotas_agrupadas[r]["tempo_total"] += log["tempo_ms"]

    rotas_stats = []
    for rota, stats in rotas_agrupadas.items():
        rotas_stats.append({
            "rota": rota,
            "chamadas": stats["chamadas"],
            "tempo_medio_ms": round(stats["tempo_total"] / stats["chamadas"], 2)
        })
    
    # Ordena para mostrar as rotas mais lentas no topo
    rotas_lentas = sorted(rotas_stats, key=lambda x: x["tempo_medio_ms"], reverse=True)[:5]
    rotas_mais_chamadas = sorted(rotas_stats, key=lambda x: x["chamadas"], reverse=True)[:5]

    # 4. Chama a função de I/O do Banco de Dados
    db_io = supabase.rpc("get_db_io_metrics").execute().data

    return {
        "resumo_24h": {
            "total_requisicoes": total_requisicoes,
            "tempo_medio_ms": round(tempo_medio, 2)
        },
        "top_5_rotas_lentas": rotas_lentas,
        "top_5_rotas_usadas": rotas_mais_chamadas,
        "io_banco_de_dados": db_io
    }