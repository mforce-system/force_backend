from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_str: str):
    """
    Validate JWT token and return the user.
    """
    try:
        # Validate token
        UntypedToken(token_str)
        
        # Decode and get user
        from rest_framework_simplejwt.backends import TokenBackend
        backend = TokenBackend(algorithm='HS256')
        payload = backend.decode(token_str, verify=True)
        user_id = payload.get('user_id')
        
        if user_id:
            return User.objects.get(id=user_id)
    except (InvalidToken, TokenError, User.DoesNotExist):
        pass
    
    return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    WebSocket middleware for JWT authentication.
    Expects token in query string: ws://...?token=<jwt_token>
    """
    async def __call__(self, scope, receive, send):
        # Parse query string for token
        query_string = parse_qs(scope.get("query_string", b"").decode())
        token = query_string.get("token")
        
        if token and len(token) > 0:
            scope["user"] = await get_user_from_token(token[0])
        else:
            scope["user"] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)

