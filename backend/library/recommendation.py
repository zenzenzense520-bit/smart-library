import math
from collections import Counter, defaultdict

from django.db.models import Count
from django.utils import timezone

from .models import Book, Loan, User


class RecommendationEngine:
    @staticmethod
    def get_user_profile(user):
        """
        构建用户借阅与阅读画像：
        - 累计借阅量、当前在借、已归还
        - 准时归还率（守信履约率）
        - 偏好分类分布与百分比
        - 偏好作者排行
        - 阅读画像标签（Reading DNA）及深度分析评语
        """
        loans = Loan.objects.filter(user=user).select_related('book__category').prefetch_related('book__authors')
        total_loans = loans.count()
        returned_loans = [l for l in loans if l.returned_at or l.status == Loan.Status.RETURNED]
        active_loans = [l for l in loans if l.status in [Loan.Status.BORROWED, Loan.Status.OVERDUE]]

        on_time_count = sum(1 for l in returned_loans if l.returned_at and l.returned_at <= l.due_at)
        on_time_rate = round((on_time_count / len(returned_loans) * 100), 1) if returned_loans else 100.0

        category_counts = Counter()
        author_counts = Counter()
        for loan in loans:
            if loan.book and loan.book.category:
                category_counts[loan.book.category.name] += 1
            if loan.book:
                for author in loan.book.authors.all():
                    author_counts[author.name] += 1

        top_categories = []
        for cat_name, cnt in category_counts.most_common(5):
            pct = round((cnt / total_loans * 100), 1) if total_loans > 0 else 0
            top_categories.append({'name': cat_name, 'count': cnt, 'percentage': pct})

        top_authors = [
            {'name': author, 'count': cnt}
            for author, cnt in author_counts.most_common(5)
        ]

        # 动态读者画像标签
        if total_loans == 0:
            dna_label = '🌱 新锐启航 · 探索新读者'
            dna_desc = '您刚刚开启在知行书院的阅读之旅，快去书目馆探索心仪的书籍吧！'
        else:
            top_cat = top_categories[0]['name'] if top_categories else ''
            if any(k in top_cat for k in ['计算', '软件', '技术', '算法', '信息']):
                dna_label = '💻 极客先锋 · 数字技术探索者'
                dna_desc = '您在计算机与工程前沿沉浸深入，对技术构建与架构演进拥有敏锐嗅觉。'
            elif any(k in top_cat for k in ['文学', '艺术', '诗歌', '散文']):
                dna_label = '📖 文心墨韵 · 沉浸思辨漫游者'
                dna_desc = '您钟情于文字与故事的肌理，在字里行间探索人类丰沛的情感与思想共鸣。'
            elif any(k in top_cat for k in ['社会', '历史', '经济', '哲学', '政治']):
                dna_label = '🌐 洞悉经纬 · 社会人文洞察者'
                dna_desc = '您关注现实关怀与文明脉络，在宏阔的历史与社会维度中审视当下。'
            elif len(top_categories) >= 3:
                dna_label = '🎯 博雅贯通 · 跨界通识博学者'
                dna_desc = '您的阅读涉猎极为广泛，在多学科的交汇点上碰撞出跨界灵感火花。'
            else:
                dna_label = '📚 笃行好学 · 专注钻研者'
                dna_desc = '您在专注的知识领域稳扎稳打，借阅轨迹清晰而坚定。'

        return {
            'total_loans': total_loans,
            'active_loans_count': len(active_loans),
            'returned_loans_count': len(returned_loans),
            'on_time_return_rate': on_time_rate,
            'top_categories': top_categories,
            'top_authors': top_authors,
            'reading_dna_label': dna_label,
            'reading_dna_desc': dna_desc,
        }

    @staticmethod
    def get_recommendations_for_user(user, limit=6):
        """
        混合推荐引擎（Hybrid Recommendation）：
        1. 协同过滤（ItemCF）：基于借阅共现矩阵计算图书相似度，发现相似读者偏好；
        2. 基于内容的推荐（Content-based）：用户偏好类目与作者匹配打分；
        3. 热度加权（Popularity Bias）：借阅频次全局加权；
        4. 冷启动保护（Cold Start）：新读者采用借阅热度 Top 榜与新书混合兜底。
        """
        user_borrowed_ids = set(Loan.objects.filter(user=user).values_list('book_id', flat=True))

        candidate_books = Book.objects.exclude(id__in=user_borrowed_ids).select_related('category').prefetch_related('authors')
        if not candidate_books.exists():
            return []

        # 冷启动分支
        if not user_borrowed_ids:
            popular_books = candidate_books.annotate(
                borrow_count=Count('loans')
            ).order_by('-borrow_count', '-created_at')[:limit]

            results = []
            for b in popular_books:
                results.append({
                    'id': str(b.id),
                    'title': b.title,
                    'author': ', '.join(a.name for a in b.authors.all()) or '未知作者',
                    'category': b.category.name if b.category else '未分类',
                    'isbn': b.isbn,
                    'summary': b.summary,
                    'available_copies': b.available_copies,
                    'total_copies': b.total_copies,
                    'recommend_reason': '🔥 全馆热门借阅榜'
                })
            return results

        # 1. 协同过滤（ItemCF 基于借阅共现与 Jaccard 相似度）
        book_borrowers = defaultdict(set)
        for b_id, u_id in Loan.objects.values_list('book_id', 'user_id'):
            book_borrowers[b_id].add(u_id)

        cf_scores = defaultdict(float)
        for my_book_id in user_borrowed_ids:
            my_users = book_borrowers[my_book_id]
            if not my_users:
                continue
            for cand in candidate_books:
                cand_users = book_borrowers[cand.id]
                if not cand_users:
                    continue
                intersection = len(my_users & cand_users)
                if intersection > 0:
                    union = len(my_users | cand_users)
                    cf_scores[cand.id] += intersection / union

        # 2. 基于内容的偏好匹配
        user_cat_counts = Counter(
            Loan.objects.filter(user=user).values_list('book__category_id', flat=True)
        )
        total_user_loans = len(user_borrowed_ids)
        fav_categories = {cat_id: cnt / total_user_loans for cat_id, cnt in user_cat_counts.items()}

        user_author_counts = Counter(
            Loan.objects.filter(user=user).values_list('book__authors__id', flat=True)
        )

        # 3. 全局热度字典
        popularity_dict = dict(
            Book.objects.annotate(bc=Count('loans')).values_list('id', 'bc')
        )

        scored_candidates = []
        for book in candidate_books:
            score = 0.0
            reasons = []

            # 协同过滤打分
            if cf_scores[book.id] > 0:
                score += cf_scores[book.id] * 5.0
                reasons.append('借阅过相似书籍的读者也在读')

            # 类目偏好打分
            if book.category_id in fav_categories:
                cat_weight = fav_categories[book.category_id]
                score += cat_weight * 3.2
                reasons.append(f'匹配您偏好的「{book.category.name}」类目')

            # 作者偏好打分
            matching_authors = [a for a in book.authors.all() if a.id in user_author_counts]
            if matching_authors:
                score += len(matching_authors) * 2.8
                reasons.append(f'来自您常读的作者（{matching_authors[0].name}）')

            # 热度平滑打分
            bc = popularity_dict.get(book.id, 0)
            score += math.log1p(bc) * 0.6

            if not reasons:
                reasons.append('馆藏精选力荐好书')

            scored_candidates.append((score, reasons[0], book))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, reason, b in scored_candidates[:limit]:
            results.append({
                'id': str(b.id),
                'title': b.title,
                'author': ', '.join(a.name for a in b.authors.all()) or '未知作者',
                'category': b.category.name if b.category else '未分类',
                'isbn': b.isbn,
                'summary': b.summary,
                'available_copies': b.available_copies,
                'total_copies': b.total_copies,
                'recommend_reason': reason
            })
        return results

    @staticmethod
    def get_related_books(target_book, limit=4):
        """
        书目详情页相关推荐（相似图书）：
        - 同作者关联
        - 同分类关联
        - 读者协同借阅共现
        """
        target_users = set(Loan.objects.filter(book=target_book).values_list('user_id', flat=True))
        candidates = Book.objects.exclude(id=target_book.id).select_related('category').prefetch_related('authors')
        scored = []

        target_authors = set(target_book.authors.values_list('id', flat=True))

        for b in candidates:
            score = 0.0
            reason = '馆藏相关精选'

            b_authors = set(b.authors.values_list('id', flat=True))
            shared_authors = target_authors & b_authors
            if shared_authors:
                score += 4.5
                reason = '同作者代表作'

            if target_book.category_id and b.category_id == target_book.category_id:
                score += 2.5
                if not shared_authors:
                    reason = f'同属于「{target_book.category.name}」精选'

            if target_users:
                b_users = set(Loan.objects.filter(book=b).values_list('user_id', flat=True))
                co_borrow_count = len(target_users & b_users)
                if co_borrow_count > 0:
                    score += co_borrow_count * 2.2
                    reason = '经常被读者一同借阅'

            scored.append((score, reason, b))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, reason, b in scored[:limit]:
            results.append({
                'id': str(b.id),
                'title': b.title,
                'author': ', '.join(a.name for a in b.authors.all()) or '未知作者',
                'category': b.category.name if b.category else '未分类',
                'isbn': b.isbn,
                'summary': b.summary,
                'available_copies': b.available_copies,
                'total_copies': b.total_copies,
                'relation_reason': reason
            })
        return results
