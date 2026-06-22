from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.database import supabase # O nosso cliente da matriz

seguranca_armada = HTTPBearer()

def validar_passaporte(credentials: HTTPAuthorizationCredentials = Security(seguranca_armada)):
    """
    O segurança da portaria terceirizado. 
    Manda o token de volta pro Supabase e deixa eles validarem a criptografia.
    """
    token = credentials.credentials
    
    try:
        # Bate na Big Tech e valida o passaporte na hora. Suporta qualquer algoritmo (ES256, HS256, etc)
        auth_response = supabase.auth.get_user(token)
        
        # Se a matriz aprovou, a gente empacota o ID (sub) e devolve pro nosso router
        return {"sub": auth_response.user.id}
        
    except Exception as e:
        # Se o token for falso, expirado ou adulterado, o Supabase levanta o erro e a gente barra na porta.
        raise HTTPException(
            status_code=401, 
            detail="Passaporte rejeitado pela matriz. Token inválido, expirado ou corrompido."
        )