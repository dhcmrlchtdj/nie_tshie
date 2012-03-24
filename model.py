#!/usr/bin/env python
# -*- coding: utf-8 -*-

from google.appengine.ext import db, deferred



class Tag(db.Model):
    # key name: tag
    count = db.IntegerProperty(default=1)

    def update_count(self):
        self.count = Bookmark.all().filter('tags =', self.key().name()).count(None)
        if self.count == 0:
            db.delete(self)
            return
        self.put()

    @staticmethod
    def update_tags(names):
        for name in names:
            tag = Tag.get_or_insert(name)
            tag.update_count()

    @staticmethod
    def get_all_tags(limit=1000):
        tags = Tag.all().fetch(limit)
        return [
            {'name': t.key().name(), 'count': t.count}
            for t in tags
        ]

    @classmethod
    def delete_tag(cls, name):
        bookmarks = Bookmark.all().filter('tags =', name).fetch(100)

        if not bookmarks:
            db.delete(db.Key.from_path('Tag', name))
            return

        for bookmark in bookmarks:
            tags = bookmark.tags
            while name in tags:
                tags.remove(name)
            bookmark.tags = tags
        db.put(bookmarks)

        deferred.defer(cls.delete_tag, name)

    @classmethod
    def move_tag(cls, from_name, to_name):
        bookmarks = Bookmark.all().filter('tags =', from_name).fetch(100)

        if not bookmarks:
            db.delete(db.Key.from_path('Tag', from_name))
            to_tag = cls.get_or_insert(to_name)
            to_tag.update_count()
            return

        for bookmark in bookmarks:
            tags = bookmark.tags
            while from_name in tags:
                tags.remove(from_name)
            if to_name not in tags:
                tags.append(to_name)
            bookmark.tags = tags
        db.put(bookmarks)

        deferred.defer(cls.move_tag, from_name, to_name)



class Bookmark(db.Model):
    url = db.StringProperty(required=True)
    tags = db.StringListProperty()
    title = db.StringProperty(required=True, indexed=False)
    desc = db.TextProperty()
    time = db.DateTimeProperty(auto_now_add=True)

    def to_dict(self):
        return {
            'url': self.url,
            'tags': ' '.join(self.tags),
            'title': self.title,
            'desc': self.desc,
            'time': self.time,
        }

    def delete_bookmark(self):
        tags_need_update = self.tags
        db.delete(self)
        Tag.update_tags(tags_need_update)

    def update_by_dict(self, entity):
        tags_need_update = set(self.tags + entity['tags'])
        self.tags = list(set(entity['tags']))
        self.title = entity['title']
        self.desc = entity['desc']
        self.put()
        Tag.update_tags(tags_need_update)

    @classmethod
    def create_by_dict(cls, entity):
        entity['tags'] = list(set(entity['tags']))
        cls(
            url=entity['url'],
            tags=entity['tags'],
            title=entity['title'],
            desc=entity['desc']
        ).put()
        Tag.update_tags(entity['tags'])

    @classmethod
    def input_bookmarks(cls, bookmarks):
        new_bookmarks = []
        tags_need_update = set()
        for b in bookmarks:
            new_bookmarks.append(
                cls(
                    url=b['url'],
                    tags=list(set(b['tags'])),
                    title=b['title'],
                    desc=b['desc']
                )
            )
            tags_need_update.update(b['tags'])
        db.put(new_bookmarks)
        Tag.update_tags(tags_need_update)

    @classmethod
    def output_bookmarks(cls, tag_names=[]):
        query = cls.all()
        for name in tag_names:
            query.filter('tags =', name)
        bookmarks = query.order('-time').fetch(None)
        return [b.to_dict() for b in bookmarks]

    @classmethod
    def get_by_url(cls, url):
        return cls.all().filter('url =', url).get()

    @classmethod
    def get_by_page(cls, page=1, limit=50):
        query = cls.all().order('-time')
        return cls.wrap_bookmarks(query, limit, page),\
                cls.page_count(query, limit)

    @classmethod
    def get_by_tags(cls, names, page=1, limit=50):
        query = cls.all()
        for name in names:
            query.filter('tags =', name)
        query.order('-time')
        return cls.wrap_bookmarks(query, limit, page),\
                cls.page_count(query, limit)

    @staticmethod
    def page_count(query, limit):
        q, r = divmod(query.count(None), limit)
        # 余数不为0 返回 页数+1
        # 余数为0 返回 页数(若页数为0则返回1)
        return q + 1 if r != 0 else q or 1

    @staticmethod
    def wrap_bookmarks(query, limit, page):
        offset = (page - 1) * limit
        bookmarks = query.fetch(limit, offset)
        return [b.to_dict() for b in bookmarks]

