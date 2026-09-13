from django.core.management.base import BaseCommand

from library.models import Author, Book, Category, User


class Command(BaseCommand):
    help = 'Create deterministic demo users and library records.'

    def handle(self, *args, **options):
        admin = self._user('admin@zhixing.local', '系统管理员', User.Role.ADMIN, 'Admin123!')
        student = self._user('student@zhixing.local', '林知夏', User.Role.STUDENT, 'Student123!')
        self._user('staff@zhixing.local', '周老师', User.Role.STAFF, 'Staff123!')

        categories = {name: Category.objects.get_or_create(name=name)[0] for name in ['文学', '计算机', '社会科学']}
        authors = {name: Author.objects.get_or_create(name=name)[0] for name in ['余华', 'Martin Fowler', '费孝通', 'Virginia Woolf']}
        books = [
            ('活着', '9787506365437', categories['文学'], [authors['余华']], 4),
            ('重构：改善既有代码的设计', '9787115417411', categories['计算机'], [authors['Martin Fowler']], 3),
            ('乡土中国', '9787301174820', categories['社会科学'], [authors['费孝通']], 5),
            ('一间自己的房间', '9787532782024', categories['文学'], [authors['Virginia Woolf']], 2),
        ]
        for title, isbn, category, book_authors, copies in books:
            book, created = Book.objects.get_or_create(title=title, defaults={'isbn': isbn, 'category': category, 'total_copies': copies, 'available_copies': copies, 'summary': f'{title}示例书目。'})
            if created:
                book.authors.set(book_authors)

        self.stdout.write(self.style.SUCCESS(f'Demo data ready. Admin: {admin.email}, student: {student.email}'))

    @staticmethod
    def _user(email, name, role, password):
        user, created = User.objects.get_or_create(email=email, defaults={'name': name, 'role': role})
        if created:
            user.set_password(password)
            user.save(update_fields=['password'])
        return user
