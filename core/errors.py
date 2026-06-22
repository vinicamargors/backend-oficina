from fastapi import Request
from fastapi.responses import JSONResponse
from postgrest.exceptions import APIError

async def supabase_exception_handler(request: Request, exc: APIError):
    """
    O Tribunal Privado: intercepta qualquer erro do Supabase antes 
    de chegar no usuário e formata a resposta.
    """
    erro_str = str(exc)
    
    # 23505: unique_violation (Tentou cadastrar placa, email ou CPF que já existe)
    if "23505" in erro_str:
        status_code = 409
        mensagem = "Conflito no mercado: Já existe um registro ativo com estes dados únicos (Ex: Placa, CPF/CNPJ, Email)."
    
    # 23503: foreign_key_violation (A lei máxima da rastreabilidade)
    elif "23503" in erro_str:
        status_code = 400
        # Se for erro de INSERT/UPDATE (cliente não existe)
        if "is not present in table" in erro_str:
            mensagem = "Operação inválida: Você está tentando vincular a um registro fantasma que não existe no sistema."
        # Se for erro de DELETE (tentando apagar quem tem dívida/OS)
        else:
            mensagem = "Bloqueio de Auditoria: Este registro possui histórico financeiro ou dependências ativas e não pode ser apagado."
            
    # 23502: not_null_violation (Tentou burlar o Pydantic e mandou nulo direto pro banco)
    elif "23502" in erro_str:
        status_code = 422
        mensagem = "Dados incompletos: Um campo obrigatório no banco não foi preenchido."
        
    # 23514: check_violation (Ex: Tentou colocar um status de OS que não existe no CHECK ARRAY)
    elif "23514" in erro_str:
        status_code = 400
        mensagem = "Regra de negócio violada: O valor inserido não é permitido pelo contrato do banco de dados."
        
    # Erro de sintaxe (uuid inválido, etc)
    elif "22P02" in erro_str:
        status_code = 422
        mensagem = "Formato de dado inválido. Verifique se os IDs estão no formato correto."

    # Qualquer outro erro bizarro não mapeado
    else:
        status_code = 400
        mensagem = f"Erro interno de transação: {erro_str}"

    return JSONResponse(
        status_code=status_code,
        content={"detail": mensagem}
    )