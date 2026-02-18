"""
Tests for accounts app models and views
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Test User model"""
    
    def test_create_user(self):
        """Test creating a regular user"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='CLIENT'
        )
        assert user.email == 'test@example.com'
        assert user.role == 'CLIENT'
        assert user.check_password('testpass123')
        assert user.is_active
        assert not user.is_staff
    
    def test_create_superuser(self):
        """Test creating a superuser"""
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        assert user.is_staff
        assert user.is_superuser
    
    def test_user_str_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        assert str(user) == 'test@example.com'
    
    def test_user_email_uniqueness(self):
        """Test that user emails must be unique"""
        User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        with pytest.raises(Exception):
            User.objects.create_user(
                email='test@example.com',
                password='differentpass123'
            )


@pytest.mark.django_db
class TestUserAuthentication:
    """Test user authentication"""
    
    def test_jwt_token_generation(self, client_user):
        """Test JWT token generation"""
        client = APIClient()
        response = client.post('/api/token/', {
            'email': 'client@example.com',
            'password': 'clientpass123'
        })
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
    
    def test_invalid_credentials(self):
        """Test authentication with invalid credentials"""
        client = APIClient()
        response = client.post('/api/token/', {
            'email': 'nonexistent@example.com',
            'password': 'wrongpass'
        })
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_400_BAD_REQUEST]
    
    def test_token_refresh(self, client_user):
        """Test token refresh"""
        from rest_framework_simplejwt.tokens import RefreshToken
        
        refresh = RefreshToken.for_user(client_user)
        client = APIClient()
        response = client.post('/api/token/refresh/', {
            'refresh': str(refresh)
        })
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data


@pytest.mark.django_db
class TestUserRoles:
    """Test user role-based access"""
    
    def test_client_role(self):
        """Test client user creation"""
        user = User.objects.create_user(
            email='client@example.com',
            password='pass123',
            role='CLIENT'
        )
        assert user.role == 'CLIENT'
    
    def test_biker_role(self):
        """Test biker user creation"""
        user = User.objects.create_user(
            email='biker@example.com',
            password='pass123',
            role='BIKER'
        )
        assert user.role == 'BIKER'
    
    def test_admin_role(self):
        """Test admin user creation"""
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='pass123'
        )
        user.role = 'ADMIN'
        user.save()
        assert user.role == 'ADMIN'
        assert user.is_staff
