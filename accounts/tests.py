"""
Tests for the accounts application.
Tests User model and UserManager.
"""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Tests for the custom User model."""
    
    def test_create_user_with_email(self):
        """Test creating a user with email."""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            role="client"
        )
        
        assert user.email == "test@example.com"
        assert user.check_password("testpass123")
        assert user.role == "client"
        assert user.is_active is True
        assert user.is_staff is False
    
    def test_create_user_normalizes_email(self):
        """Test that email is normalized when creating user."""
        user = User.objects.create_user(
            email="Test@EXAMPLE.COM",
            password="testpass123",
            role="client"
        )
        
        assert user.email == "Test@example.com"
    
    def test_create_user_without_email_raises_error(self):
        """Test that creating user without email raises ValueError."""
        with pytest.raises(ValueError):
            User.objects.create_user(
                email="",
                password="testpass123",
                role="client"
            )
    
    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123"
        )
        
        assert user.email == "admin@example.com"
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.is_active is True
    
    def test_user_str_returns_email(self):
        """Test that User.__str__ returns email."""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            role="client"
        )
        
        assert str(user) == "test@example.com"
    
    def test_user_role_choices(self):
        """Test that user can have valid role choices."""
        for role in ['client', 'biker', 'admin']:
            user = User.objects.create_user(
                email=f"{role}@example.com",
                password="testpass123",
                role=role
            )
            assert user.role == role
    
    def test_user_date_joined_auto_set(self):
        """Test that date_joined is automatically set."""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            role="client"
        )
        
        assert user.date_joined is not None
    
    def test_user_email_is_unique(self):
        """Test that user email must be unique."""
        User.objects.create_user(
            email="unique@example.com",
            password="testpass123",
            role="client"
        )
        
        with pytest.raises(Exception):  # IntegrityError
            User.objects.create_user(
                email="unique@example.com",
                password="testpass456",
                role="biker"
            )


@pytest.mark.django_db
class TestUserManager:
    """Tests for the UserManager."""
    
    def test_create_user_sets_password(self):
        """Test that create_user properly hashes password."""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            role="client"
        )
        
        # Password should be hashed, not stored as plain text
        assert user.password != "testpass123"
        assert user.check_password("testpass123")
    
    def test_create_user_with_extra_fields(self):
        """Test creating user with extra fields."""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            role="biker",
            is_active=True
        )
        
        assert user.is_active is True
        assert user.role == "biker"
    
    def test_create_superuser_defaults(self):
        """Test that create_superuser sets correct defaults."""
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123"
        )
        
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.is_active is True


@pytest.mark.django_db
class TestJWTAuthentication:
    """Tests for JWT authentication endpoints."""
    
    def test_obtain_token_pair(self, api_client, client_user):
        """Test obtaining JWT token pair."""
        response = api_client.post('/api/token/', {
            'email': client_user.email,
            'password': 'testpassword'
        })
        
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data
    
    def test_obtain_token_invalid_credentials(self, api_client):
        """Test that invalid credentials returns 401."""
        response = api_client.post('/api/token/', {
            'email': 'wrong@example.com',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 401
    
    def test_refresh_token(self, api_client, client_user):
        """Test refreshing JWT token."""
        # First get tokens
        response = api_client.post('/api/token/', {
            'email': client_user.email,
            'password': 'testpassword'
        })
        refresh_token = response.data['refresh']
        
        # Refresh the token
        response = api_client.post('/api/token/refresh/', {
            'refresh': refresh_token
        })
        
        assert response.status_code == 200
        assert 'access' in response.data
    
    def test_refresh_with_invalid_token(self, api_client):
        """Test that invalid refresh token returns error."""
        response = api_client.post('/api/token/refresh/', {
            'refresh': 'invalid_token'
        })
        
        assert response.status_code == 401
    
    def test_access_protected_endpoint_with_token(self, client_api_client):
        """Test accessing protected endpoint with valid token."""
        response = client_api_client.get('/api/deliveries/')
        
        assert response.status_code == 200
    
    def test_access_protected_endpoint_without_token(self, api_client):
        """Test that protected endpoint requires authentication."""
        response = api_client.get('/api/deliveries/')
        
        assert response.status_code == 401
