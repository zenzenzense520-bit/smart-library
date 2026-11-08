from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from library.models import Author, Book, Category, Loan, Notification, Reservation, User


class Command(BaseCommand):
    help = 'Create deterministic demo users and library records.'

    def handle(self, *args, **options):
        admin = self._user('admin@zhixing.local', '系统管理员', User.Role.ADMIN, 'Admin123!')
        student = self._user('student@zhixing.local', '林知夏', User.Role.STUDENT, 'Student123!')
        staff = self._user('staff@zhixing.local', '周老师', User.Role.STAFF, 'Staff123!')

        categories = {
            name: Category.objects.get_or_create(name=name)[0]
            for name in ['文学', '计算机', '社会科学', '哲学', '艺术']
        }
        authors = {
            name: Author.objects.get_or_create(name=name)[0]
            for name in [
                '余华', 'Martin Fowler', '费孝通', 'Virginia Woolf',
                'Randal E. Bryant', 'Erich Gamma', '加西亚·马尔克斯'
            ]
        }
        books_data = [
            ('活着', '9787506365437', categories['文学'], [authors['余华']], 4, '讲述了一个人一生的温情与苦难，直击生命的坚韧。'),
            ('重构：改善既有代码的设计', '9787115417411', categories['计算机'], [authors['Martin Fowler']], 3, '软件工程经典，清晰解析代码重构原则、方法与设计演进。'),
            ('乡土中国', '9787301174820', categories['社会科学'], [authors['费孝通']], 5, '社会学巨著，深刻剖析中国传统乡土社会结构与人际网络。'),
            ('一间自己的房间', '9787532782024', categories['文学'], [authors['Virginia Woolf']], 2, '女性主义文学经典散文集，探寻独立思考与创作自由。'),
            ('深入理解计算机系统', '9787111544937', categories['计算机'], [authors['Randal E. Bryant']], 2, '从程序员视角深入透彻解析硬件架构、编译器、操作系统与并发网络。'),
            ('设计模式：可复用面向对象软件的基础', '9787111211273', categories['计算机'], [authors['Erich Gamma']], 1, 'Gang of Four 传世之作，奠定现代面向对象设计模式基石。'),
            ('百年孤独', '9787544253994', categories['文学'], [authors['加西亚·马尔克斯']], 3, '魔幻现实主义文学巅峰巨作，展现布恩迪亚家族七代人的孤独与传奇。'),
        ]
        created_books = {}
        for title, isbn, category, book_authors, copies, summary in books_data:
            book, created = Book.objects.get_or_create(
                title=title,
                defaults={
                    'isbn': isbn,
                    'category': category,
                    'total_copies': copies,
                    'available_copies': copies,
                    'summary': summary
                }
            )
            if created:
                book.authors.set(book_authors)
            created_books[title] = book

        # 为林知夏同学初始化示范借阅记录（生成生动的计算机读者画像）
        cs_book = created_books['重构：改善既有代码的设计']
        if not Loan.objects.filter(user=student, book=cs_book).exists():
            Loan.objects.create(
                user=student,
                book=cs_book,
                borrowed_at=timezone.now() - timedelta(days=10),
                due_at=timezone.now() + timedelta(days=20),
                status=Loan.Status.BORROWED
            )

        # 增加一条已归还的借阅记录用于统计履约率
        lit_book = created_books['活着']
        if not Loan.objects.filter(user=student, book=lit_book).exists():
            Loan.objects.create(
                user=student,
                book=lit_book,
                borrowed_at=timezone.now() - timedelta(days=40),
                due_at=timezone.now() - timedelta(days=10),
                returned_at=timezone.now() - timedelta(days=12),
                status=Loan.Status.RETURNED,
                fine_amount=Decimal('0.00')
            )

        # 为林知夏创建一条到馆待取的预约演示记录
        rare_book = created_books['设计模式：可复用面向对象软件的基础']
        rare_book.available_copies = 0
        rare_book.save(update_fields=['available_copies'])

        if not Reservation.objects.filter(user=student, book=rare_book).exists():
            res = Reservation.objects.create(
                user=student,
                book=rare_book,
                status=Reservation.Status.NOTIFIED,
                notified_at=timezone.now() - timedelta(hours=6),
                hold_expires_at=timezone.now() + timedelta(hours=42)
            )

        # 创建一条演示到馆通知与系统欢迎通知
        if not Notification.objects.filter(user=student, notification_type=Notification.Type.RESERVATION_ARRIVED).exists():
            Notification.objects.create(
                user=student,
                title=f'【到馆提醒】您预约的《{rare_book.title}》已到馆待取',
                content=f'您排队预约的图书《{rare_book.title}》已被归还，系统已为您优先锁定保留 48 小时。请在此期间前往书院服务台或在系统内一键借阅取书。',
                notification_type=Notification.Type.RESERVATION_ARRIVED,
                related_book=rare_book,
                is_read=False
            )

        if not Notification.objects.filter(user=student, notification_type=Notification.Type.SYSTEM).exists():
            Notification.objects.create(
                user=student,
                title='欢迎体验知行书院全新「智慧图书馆」服务',
                content='知行书院智慧服务全新升级：支持智能预约排队与到馆超时顺延，并上线基于读者画像的个性化图书推荐系统。',
                notification_type=Notification.Type.SYSTEM,
                is_read=False
            )

        self.stdout.write(self.style.SUCCESS(f'Demo data ready. Admin: {admin.email}, student: {student.email}'))

    @staticmethod
    def _user(email, name, role, password):
        user, created = User.objects.get_or_create(email=email, defaults={'name': name, 'role': role})
        if created:
            user.set_password(password)
            user.save(update_fields=['password'])
        return user
