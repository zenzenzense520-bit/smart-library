from django.contrib import admin

from .models import Author, AuditLog, Book, BookAuthor, Category, Loan, Reservation, User

admin.site.register([User, Category, Author, Book, BookAuthor, Loan, Reservation, AuditLog])
