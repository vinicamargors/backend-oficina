import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from core.database import supabase

class MonitoramentoAPMMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Deixa a requisição seguir o fluxo normal dela
        response = await call_next(request)
        
        # Para o cronômetro
        process_time = (time.time() - start_time) * 1000 # Converte pra milissegundos
        
        # Filtra pra não poluir o banco com requisições de OPTIONS (CORS) ou rotas inúteis
        if request.method != "OPTIONS" and "/api/v1/" in request.url.path:
            # Registra a métrica no Supabase de forma silenciosa
            try:
                supabase.table("api_metrics").insert({
                    "metodo": request.method,
                    "rota": request.url.path,
                    "status_code": response.status_code,
                    "tempo_ms": round(process_time, 2)
                }).execute()
            except Exception:
                pass # Se der erro no log, a gente engole pra não quebrar a API do cliente
                
        return response