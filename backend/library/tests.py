import json
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Author, Book, Category, Loan, Notification, Reservation, User
from .recommendation import RecommendationEngine
from .services import ReservationService


class LibraryApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('student@example.com', 'Student123!', name='测试学生')
        self.admin = User.objects.create_superuser('admin@example.com', 'Admin123!', name='测试管理员')
        self.category = Category.objects.create(name='计算机')
        self.author = Author.objects.create(name='测试作者')
        self.book = Book.objects.create(title='测试书', category=self.category, total_copies=1, available_copies=1)
        self.book.authors.add(self.author)

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

    def test_reservation_queue_and_hold_on_return(self):
        # 验证预约队列与排位、还书自动锁定给排队第1位、生成到馆通知
        u1 = self.user
        u2 = User.objects.create_user('u2@example.com', 'U2pass123!', name='学生乙')
        u3 = User.objects.create_user('u3@example.com', 'U3pass123!', name='学生丙')

        # 先由 u1 借出该书，库存归 0
        self.authenticate(u1)
        res_borrow = self.client.post('/api/loans', {'book_id': str(self.book.id)})
        loan_id = res_borrow.data['id']

        # u2 与 u3 排队预约
        self.authenticate(u2)
        r2 = self.client.post('/api/reservations', {'book': str(self.book.id)})
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.data['queue_position'], 1)

        self.authenticate(u3)
        r3 = self.client.post('/api/reservations', {'book': str(self.book.id)})
        self.assertEqual(r3.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r3.data['queue_position'], 2)

        # u1 归还图书
        self.authenticate(u1)
        res_ret = self.client.post(f'/api/loans/{loan_id}/return')
        self.assertEqual(res_ret.status_code, status.HTTP_200_OK)

        # 检查图书可用库存仍为 0（因被锁定保留给 u2）
        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 0)

        # 检查 u2 预约状态变为 notified，并生成通知
        self.authenticate(u2)
        res_list = self.client.get('/api/reservations')
        u2_res = res_list.data['results'][0] if 'results' in res_list.data else res_list.data[0]
        self.assertEqual(u2_res['status'], Reservation.Status.NOTIFIED)
        self.assertEqual(u2_res['queue_position'], 0)
        self.assertIsNotNone(u2_res['hold_expires_at'])

        notifs = Notification.objects.filter(user=u2)
        self.assertEqual(notifs.count(), 1)
        self.assertIn('到馆提醒', notifs.first().title)

        # u2 一键核销/借阅
        claim_res = self.client.post(f"/api/reservations/{u2_res['id']}/claim")
        self.assertEqual(claim_res.status_code, status.HTTP_201_CREATED)

    def test_reservation_timeout_and_cascade(self):
        # 验证超时未借释放，自动顺延给后续等待者
        u1 = self.user
        u2 = User.objects.create_user('u2_cascade@example.com', 'Pass123!', name='等待者2')

        self.book.available_copies = 0
        self.book.save(update_fields=['available_copies'])

        # u1 已到馆待取，但时间设为已过期
        res1 = Reservation.objects.create(
            user=u1,
            book=self.book,
            status=Reservation.Status.NOTIFIED,
            hold_expires_at=timezone.now() - timedelta(hours=1)
        )
        # u2 正在排队
        res2 = Reservation.objects.create(
            user=u2,
            book=self.book,
            status=Reservation.Status.WAITING
        )

        released, cascaded = ReservationService.check_and_release_expired_reservations()
        self.assertEqual(released, 1)
        self.assertEqual(cascaded, 1)

        res1.refresh_from_db()
        self.assertEqual(res1.status, Reservation.Status.EXPIRED)

        res2.refresh_from_db()
        self.assertEqual(res2.status, Reservation.Status.NOTIFIED)
        self.assertIsNotNone(res2.hold_expires_at)

        # u1 收到失效通知，u2 收到到馆提醒
        self.assertTrue(Notification.objects.filter(user=u1, notification_type=Notification.Type.RESERVATION_EXPIRED).exists())
        self.assertTrue(Notification.objects.filter(user=u2, notification_type=Notification.Type.RESERVATION_ARRIVED).exists())

    def test_recommendation_and_user_profile(self):
        # 测试个性化推荐与读者画像
        self.authenticate(self.user)
        # 借阅一本计算机书
        self.client.post('/api/loans', {'book_id': str(self.book.id)})

        # 创建另一本推荐候选书
        book2 = Book.objects.create(
            title='代码整洁之道',
            category=self.category,
            total_copies=2,
            available_copies=2
        )
        book2.authors.add(self.author)

        # 测试为你推荐 API
        res_rec = self.client.get('/api/recommendations/for-you')
        self.assertEqual(res_rec.status_code, status.HTTP_200_OK)
        rec_ids = [b['id'] for b in res_rec.data]
        self.assertIn(str(book2.id), rec_ids)

        # 测试书目相关推荐
        res_rel = self.client.get(f'/api/recommendations/books/{self.book.id}/related')
        self.assertEqual(res_rel.status_code, status.HTTP_200_OK)
        self.assertTrue(any(b['id'] == str(book2.id) for b in res_rel.data))

        # 测试读者画像 API
        res_prof = self.client.get('/api/recommendations/user-profile')
        self.assertEqual(res_prof.status_code, status.HTTP_200_OK)
        self.assertIn('reading_dna_label', res_prof.data)
        self.assertIn('top_categories', res_prof.data)
        self.assertEqual(res_prof.data['total_loans'], 1)

    def test_notification_apis(self):
        # 测试通知接口（未读统计、全部已读）
        Notification.objects.create(
            user=self.user,
            title='测试通知1',
            content='内容1',
            is_read=False
        )
        Notification.objects.create(
            user=self.user,
            title='测试通知2',
            content='内容2',
            is_read=False
        )
        self.authenticate(self.user)

        res_count = self.client.get('/api/notifications/unread-count')
        self.assertEqual(res_count.status_code, status.HTTP_200_OK)
        self.assertEqual(res_count.data['unread_count'], 2)

        res_read_all = self.client.post('/api/notifications/read-all')
        self.assertEqual(res_read_all.status_code, status.HTTP_200_OK)

        res_count_after = self.client.get('/api/notifications/unread-count')
        self.assertEqual(res_count_after.data['unread_count'], 0)
