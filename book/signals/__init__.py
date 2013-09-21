'''
Created on Jul 30, 2013

@author: antipro
'''
from django import dispatch
import pdb
from book.models.user_log_model import UserLog
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from book.models.chapter_model import Chapter
from django.utils import timezone
from django.contrib.auth.models import User

# when user read a chapter
chapter_read_signal = dispatch.Signal(providing_args=["user", "chapter", "page"])

# when user thank a chapter
chapter_thank_signal = dispatch.Signal(providing_args=["user", "chapter"])

# book listing signal
pre_listing_book = dispatch.Signal(providing_args=["user", "books"])

# require login to do something
def require_login_simple(func):
    def decorator(*args, **kwargs):
        user = kwargs.get('user')
        if not user or not user.is_authenticated():
            return
        func(*args, **kwargs)
    return decorator

@dispatch.receiver(chapter_read_signal)
@require_login_simple
def log_user_read_book(sender, **kwargs):
    user = kwargs.get('user')
    page = kwargs.get('page')
    chapter = kwargs.get('chapter')
    book = chapter.book

    try:
        userLog = UserLog.objects.get(user=user, book=book)
        userLog.page = page
        userLog.last_update = timezone.now()
    except ObjectDoesNotExist:
        userLog = UserLog(user=user, book=book, page=page)

    userLog.save()

@dispatch.receiver(chapter_read_signal)
@require_login_simple
def set_thanked_status(sender, **kwargs):
    user = kwargs.get('user')
    chapter = kwargs.get('chapter')

    from book.models import ChapterThank
    try:
        chapterThank = ChapterThank.objects.get(user=user, chapter=chapter)  # @UnusedVariable
        chapter.thanked_by_current_user = True
    except ObjectDoesNotExist:
        chapter.thanked_by_current_user = False


@dispatch.receiver(chapter_read_signal)
@require_login_simple
def set_rated_status(sender, **kwargs):
    user = kwargs.get('user')
    chapter = kwargs.get('chapter')
    chapter.book.rated_by_current_user = chapter.book.is_rated_by(user)

@dispatch.receiver(chapter_read_signal)
@require_login_simple
def set_favorited_status(sender, **kwargs):
    user = kwargs.get('user')
    chapter = kwargs.get('chapter')
    chapter.book.favorited_by_current_user = chapter.book.is_favorited_by(user)

@dispatch.receiver(post_save, sender=Chapter)
def new_chapter(sender, **kwargs):
    if kwargs.get('created'):
        chapter = kwargs.get('instance')

        # increase user post
        chapter.user.book_profile.chapters_count += 1
        chapter.user.book_profile.save()

        # increase book last update
        chapter.book.last_update = timezone.now()
        chapter.book.save()

@dispatch.receiver(pre_listing_book)
def mark_unread_for_book(sender, **kwargs):
    user = kwargs.get('user')
    # assert isinstance(user, User)
    if not user.is_authenticated():
        return
    for book in kwargs.get('books'):
        if not book.is_read:
            book.is_read_by_current_user = book.is_read_by_user(user)
