import json
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Author, Book, Category, Loan, User


class LibraryApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('student@example.com', 'Student123!', name='测试学生')
        self.admin = User.objects.create_superuser('admin@example.com', 'Admin123!', name='测试管理员')
        category = Category.objects.create(name='计算机')
        author = Author.objects.create(name='测试作者')
        self.book = Book.objects.create(title='测试书', category=category, total_copies=1, available_copies=1)
        self.book.authors.add(author)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)
    def test_root_health_check(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content)['status'], 'ok')

    def test_register_and_login(self):
        response = self.client.post('/api/auth/register', {'name': '新用户', 'email': 'new@example.com', 'password': 'Password123!', 'role': 'student'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post('/api/auth/login', {'email': 'new@example.com', 'password': 'Password123!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_register_staff_role(self):
        response = self.client.post('/api/auth/register', {'name': '教职工', 'email': 'staff-new@example.com', 'password': 'Password123!', 'role': 'staff'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['role'], 'staff')

    def test_register_legacy_teacher_role(self):
        response = self.client.post('/api/auth/register', {'name': '旧角色教职工', 'email': 'teacher@example.com', 'password': 'Password123!', 'role': 'teacher'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['role'], 'staff')

    def test_borrow_decrements_inventory(self):
        self.authenticate(self.user)
        response = self.client.post('/api/loans', {'book_id': str(self.book.id)})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 0)

    def test_cannot_borrow_without_inventory(self):
        self.authenticate(self.user)
        self.client.post('/api/loans', {'book_id': str(self.book.id)})
        other = User.objects.create_user('other@example.com', 'Other123!', name='其他学生')
        self.authenticate(other)
        response = self.client.post('/api/loans', {'book_id': str(self.book.id)})
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_return_calculates_fine(self):
        self.authenticate(self.user)
        loan = Loan.objects.create(user=self.user, book=self.book, due_at=timezone.now() - timedelta(days=3))
        self.book.available_copies = 0
        self.book.save(update_fields=['available_copies'])
        response = self.client.post(f'/api/loans/{loan.id}/return')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['fine_amount']), Decimal('3.00'))

    def test_reservation_requires_empty_inventory(self):
        self.authenticate(self.user)
        self.book.available_copies = 0
        self.book.save(update_fields=['available_copies'])
        response = self.client.post('/api/reservations', {'book': str(self.book.id)})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        duplicate = self.client.post('/api/reservations', {'book': str(self.book.id)})
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_stats_requires_admin(self):
        self.authenticate(self.user)
        self.assertEqual(self.client.get('/api/admin/stats').status_code, status.HTTP_403_FORBIDDEN)
        self.authenticate(self.admin)
        self.assertEqual(self.client.get('/api/admin/stats').status_code, status.HTTP_200_OK)
