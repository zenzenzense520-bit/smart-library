from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import AuditLog, Book, Loan, Notification, Reservation


class NotificationService:
    @staticmethod
    def send(user, title, content, notification_type=Notification.Type.SYSTEM, related_book=None):
        return Notification.objects.create(
            user=user,
            title=title,
            content=content,
            notification_type=notification_type,
            related_book=related_book
        )


class ReservationService:
    @staticmethod
    def get_hold_hours():
        return getattr(settings, 'RESERVATION_HOLD_HOURS', 48)

    @classmethod
    def check_and_release_expired_reservations(cls, book_id=None):
        """
        检查处于 NOTIFIED（到馆待取）且已超过 hold_expires_at 的预约。
        标记为 EXPIRED，发送超时失效通知；
        若队列中有后续排队者，自动顺延激活下一位并重设保留截止时间；
        若队列中已无排队者，将锁定的馆藏配额归还至 available_copies。
        """
        now = timezone.now()
        query = Reservation.objects.select_for_update().select_related('book', 'user').filter(
            status=Reservation.Status.NOTIFIED,
            hold_expires_at__lt=now
        )
        if book_id:
            query = query.filter(book_id=book_id)

        expired_list = list(query)
        released_count = 0
        cascaded_count = 0

        for res in expired_list:
            res.status = Reservation.Status.EXPIRED
            res.save(update_fields=['status'])
            released_count += 1

            NotificationService.send(
                user=res.user,
                title=f"【预约失效】《{res.book.title}》预约资格已超时释放",
                content=(
                    f"很遗憾，您预约的图书《{res.book.title}》在到馆保留期限"
                    f"（截止 {res.hold_expires_at.strftime('%Y-%m-%d %H:%M')}）内未能借取，"
                    "系统已自动释放配额并顺延。"
                ),
                notification_type=Notification.Type.RESERVATION_EXPIRED,
                related_book=res.book
            )

            # 顺延检查队列下一位
            next_waiting = Reservation.objects.select_for_update().select_related('book', 'user').filter(
                book=res.book,
                status=Reservation.Status.WAITING
            ).order_by('reserved_at').first()

            if next_waiting:
                next_waiting.status = Reservation.Status.NOTIFIED
                next_waiting.notified_at = now
                next_waiting.hold_expires_at = now + timedelta(hours=cls.get_hold_hours())
                next_waiting.save(update_fields=['status', 'notified_at', 'hold_expires_at'])
                cascaded_count += 1

                NotificationService.send(
                    user=next_waiting.user,
                    title=f"【到馆提醒】您排队的《{res.book.title}》已到馆待取",
                    content=(
                        f"您排队的图书《{res.book.title}》已就绪！系统已为您优先锁定保留至 "
                        f"{next_waiting.hold_expires_at.strftime('%Y-%m-%d %H:%M')}（保留 {cls.get_hold_hours()} 小时），"
                        "请及时前往服务台或在系统内一键借阅取书。"
                    ),
                    notification_type=Notification.Type.RESERVATION_ARRIVED,
                    related_book=res.book
                )
            else:
                Book.objects.filter(id=res.book_id).update(
                    available_copies=F('available_copies') + 1,
                    updated_at=now
                )

        return released_count, cascaded_count

    @classmethod
    def on_book_returned(cls, book):
        """
        借阅归还时调用（运行在 transaction.atomic() 内部）。
        检查是否有排队等待中的预约。
        如果有：优先分配给第一位排队者，转换为 NOTIFIED 状态并锁定副本，发送到馆通知；
        如果没有：公开增加可借副本数量 available_copies。
        """
        now = timezone.now()
        cls.check_and_release_expired_reservations(book.id)

        waiting = Reservation.objects.select_for_update().select_related('book', 'user').filter(
            book=book,
            status=Reservation.Status.WAITING
        ).order_by('reserved_at').first()

        if waiting:
            waiting.status = Reservation.Status.NOTIFIED
            waiting.notified_at = now
            waiting.hold_expires_at = now + timedelta(hours=cls.get_hold_hours())
            waiting.save(update_fields=['status', 'notified_at', 'hold_expires_at'])

            NotificationService.send(
                user=waiting.user,
                title=f"【到馆提醒】您预约的《{book.title}》已到馆待取",
                content=(
                    f"您排队预约的图书《{book.title}》已被归还，系统已为您优先锁定保留至 "
                    f"{waiting.hold_expires_at.strftime('%Y-%m-%d %H:%M')}（保留 {cls.get_hold_hours()} 小时）。"
                    "请在此期限内前往借取，逾期将自动顺延给后续排队读者。"
                ),
                notification_type=Notification.Type.RESERVATION_ARRIVED,
                related_book=book
            )
            return waiting
        else:
            Book.objects.filter(id=book.id).update(
                available_copies=F('available_copies') + 1,
                updated_at=now
            )
            return None

    @classmethod
    def cancel_reservation(cls, user, reservation_id):
        """
        用户主动取消预约。如果取消的是已到馆保留（NOTIFIED）状态，
        需自动顺延给下一位排队者或归还可用库存。
        """
        with transaction.atomic():
            res = Reservation.objects.select_for_update().select_related('book', 'user').filter(id=reservation_id).first()
            if not res:
                return None, '预约记录不存在'
            if user.role != 'admin' and res.user_id != user.id:
                return None, '无权操作此预约'
            if res.status not in [Reservation.Status.WAITING, Reservation.Status.NOTIFIED]:
                return None, f'当前状态（{res.get_status_display()}）无法取消'

            old_status = res.status
            res.status = Reservation.Status.CANCELLED
            res.save(update_fields=['status'])

            AuditLog.objects.create(
                actor_user=user,
                action='cancel_reservation',
                target_type='reservation',
                target_id=str(res.id)
            )

            # 若取消的是正在锁定的副本，顺延或返还
            if old_status == Reservation.Status.NOTIFIED:
                now = timezone.now()
                next_waiting = Reservation.objects.select_for_update().select_related('book', 'user').filter(
                    book=res.book,
                    status=Reservation.Status.WAITING
                ).order_by('reserved_at').first()

                if next_waiting:
                    next_waiting.status = Reservation.Status.NOTIFIED
                    next_waiting.notified_at = now
                    next_waiting.hold_expires_at = now + timedelta(hours=cls.get_hold_hours())
                    next_waiting.save(update_fields=['status', 'notified_at', 'hold_expires_at'])

                    NotificationService.send(
                        user=next_waiting.user,
                        title=f"【到馆提醒】您排队的《{res.book.title}》已就绪",
                        content=(
                            f"因前序读者取消预约，系统已为您优先锁定保留《{res.book.title}》，"
                            f"请于 {next_waiting.hold_expires_at.strftime('%Y-%m-%d %H:%M')} 前来馆借取。"
                        ),
                        notification_type=Notification.Type.RESERVATION_ARRIVED,
                        related_book=res.book
                    )
                else:
                    Book.objects.filter(id=res.book_id).update(
                        available_copies=F('available_copies') + 1,
                        updated_at=now
                    )

            return res, None

    @classmethod
    def claim_or_borrow(cls, user, book_id):
        """
        借阅处理（支持普通借阅与到馆预约核销借阅）：
        1. 优先校验该用户是否有本图书的 NOTIFIED 保留预约；
           若有，将预约标记为 FULFILLED，直接创建借阅（不消耗公共可用库存）。
        2. 若无保留预约，要求 available_copies > 0，扣减 1 份可用库存并创建借阅。
        """
        with transaction.atomic():
            cls.check_and_release_expired_reservations(book_id=book_id)

            book = Book.objects.select_for_update().filter(id=book_id).first()
            if not book:
                return None, '书目不存在。', 404

            active_loan = Loan.objects.filter(
                user=user,
                book=book,
                status__in=[Loan.Status.BORROWED, Loan.Status.OVERDUE]
            ).exists()
            if active_loan:
                return None, '你已经借阅了这本书。', 409

            # 检查是否有属于当前用户的到馆保留预约
            held_res = Reservation.objects.select_for_update().filter(
                user=user,
                book=book,
                status=Reservation.Status.NOTIFIED
            ).first()

            if held_res:
                held_res.status = Reservation.Status.FULFILLED
                held_res.save(update_fields=['status'])

                loan = Loan.objects.create(
                    user=user,
                    book=book,
                    due_at=timezone.now() + timedelta(days=30)
                )
                AuditLog.objects.create(
                    actor_user=user,
                    action='claim_reserved_borrow',
                    target_type='loan',
                    target_id=str(loan.id)
                )
                return loan, None, 201

            # 普通外借：必须有可用副本
            if book.available_copies < 1:
                return None, '当前无可借副本，请先预约。', 409

            # 如果用户有处于 WAITING 的预约，直接满足并标记
            waiting_res = Reservation.objects.filter(
                user=user,
                book=book,
                status=Reservation.Status.WAITING
            ).first()
            if waiting_res:
                waiting_res.status = Reservation.Status.FULFILLED
                waiting_res.save(update_fields=['status'])

            book.available_copies -= 1
            book.save(update_fields=['available_copies', 'updated_at'])

            loan = Loan.objects.create(
                user=user,
                book=book,
                due_at=timezone.now() + timedelta(days=30)
            )
            AuditLog.objects.create(
                actor_user=user,
                action='borrow_book',
                target_type='loan',
                target_id=str(loan.id)
            )
            return loan, None, 201
