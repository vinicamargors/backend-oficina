# core/audit.py
from core.database import supabase

def salvar_audit_log(tabela: str, operacao: str, registro_id: str, empresa_id: str, antes: dict = None, depois: dict = None):
    """A Mão Invisível que tudo registra e nada perdoa."""
    supabase.table("audit_logs").insert({
        "tabela": tabela,
        "operacao": operacao,
        "registro_id": str(registro_id),
        "empresa_id": str(empresa_id), # Agora blindado por inquilino!
        "dados_antes": antes,
        "dados_depois": depois
    }).execute()