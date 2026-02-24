from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_str: str):
    """
    Validate JWT token and return the matching user.
    - Uses UntypedToken to validate the token signature and expiry.
    - Uses TokenBackend with the project SECRET_KEY to decode the payload.
    - Returns the user if found, otherwise returns AnonymousUser.
    """
    try:
        # Validate token signature and expiry first
        UntypedToken(token_str)

        # Decode the payload using the project's SECRET_KEY
        from rest_framework_simplejwt.backends import TokenBackend
        backend = TokenBackend(algorithm='HS256', signing_key=settings.SECRET_KEY)
        payload = backend.decode(token_str, verify=True)

        # Extract user_id from the decoded payload
        user_id = payload.get('user_id')

        if user_id:
            return User.objects.get(id=user_id)

    except (InvalidToken, TokenError, User.DoesNotExist):
        # Any token or user issue — treat as anonymous
        pass

    return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    WebSocket middleware for JWT authentication.
    Expects token in query string: ws://...?token=<jwt_token>
    Attaches the authenticated user to the scope so consumers can access it via self.scope['user'].
    """
    async def __call__(self, scope, receive, send):
        # Parse the WebSocket query string to extract the token
        query_string = parse_qs(scope.get("query_string", b"").decode())
        token = query_string.get("token")

        if token and len(token) > 0:
            # Validate token and attach the user to scope
            scope["user"] = await get_user_from_token(token[0])
        else:
            # No token provided — treat as anonymous
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)