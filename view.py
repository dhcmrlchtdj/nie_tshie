#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.web

from model import Tag, Bookmark


class Base(tornado.web.RequestHandler):
    pass


class Redirect(Base):
    def get(self):
        self.redirect('/main')

    def post(self):
        self.redirect('/main')


class Main(Base):
    def get(self, page):
        # 获取bookmark
        self.page = int(page or 1)
        self.bookmarks, self.page_count = Bookmark.get_by_page(self.page)

        if self.page > self.page_count:
            # url要求的页数超出了总页数
            self.redirect('/main/' + str(self.page_count))
            return

        # 获取tag
        self.tags = Tag.get_all_tags()

        self.render('main.html', title=self.page_count, contents={
            'bookmarks': self.bookmarks, 'tags': self.tags})


class Filter(Base):
    def get(self, tag_names, page):
        # 获取页数
        self.page = int(page or 1)

        # 获取tag列表
        self.tags = tag_names.replace('+', ' ').split()
        self.bookmarks, self.page_count = \
                Bookmark.get_by_tags(self.tags, self.page)

        if self.page > self.page_count:
            # url要求的页数超出了总页数
            self.redirect('/tag/{0}/{1}'.format(
                '+'.join(self.tags), self.page_count))
            return

        self.tags = Tag.get_all_tags()

        self.render('filter.html', title=tag_names, contents={
            'bookmarks': self.bookmarks, 'tags': self.tags})


class BookmarkUtil(Base):
    def validate_url(self, url):
        """检查url是否完整，若url错误则返回None"""

        if not url: return

        import re
        re_url = re.compile(
            r'''(?ix)
            ^((ht|f)tps?://)?           # protocol
            (                           #! group(1)
                [-.a-z0-9_]+            # google/youtube/... or ddd.ddd.ddd
                \.                      # . (dot)
                ([a-z]{2,4}|\d{1,3})    # com/net/... or ddd
                (:\d{2,5})?             # port
            )
            (/.*)?$                     # pathname
            ''')
        match_url = re_url.match(url)

        if not match_url: return

        # 补上缺少的http://
        return url if match_url.group(1) else 'http://' + url


class New(BookmarkUtil):
    def get(self):
        self.url = self.validate_url(self.get_argument('url', ''))

        # /get
        if not self.url:
            self.render('new.html', title='new', contents=None)
            return

        # /get/XXXX
        # 已收藏
        if Bookmark.get_by_url(self.url):
            self.redirect('/bookmark/get/' + self.url)
            return


        self.title = self.get_title(self.url)

        self.render('new.html', title='new', contents={
            'url': self.url, 'title': self.title})


    def post(self):
        self.url = self.validate_url(self.get_argument('url', ''))

        # 错误的url
        if not self.url:
            self.redirect('/main')
            return

        # 未收藏
        if not Bookmark.get_by_url(self.url):
            self.title = self.get_argument('title', '') or self.url
            self.desc = self.get_argument('desc', '')
            self.tags = self.get_argument('tags', '').split()

            Bookmark.create_by_dict({
                'url': self.url,
                'tags': self.tags,
                'title': self.title,
                'desc': self.desc
            })

        self.redirect('/bookmark/get/' + self.url)


    @staticmethod
    def get_title(url):
        """从所给的url获取页面标题，没找到标题就返回url"""

        from google.appengine.api import urlfetch
        try:
            result = urlfetch.fetch(url, allow_truncated=True)
        except:
            # 下载页面失败
            return url

        if result.status_code == 200:
            import re

            # 获取页面编码
            re_charset = re.compile(
                r'''(?ix)
                charset=                # charset="UTF-8" OR charset=UTF-8"
                ('|")?
                ([-._:()0-9a-z]{3,})    #! charset
                ('|")?
                ''')

            match_charset = re_charset.search(result.content)

            charset = match_charset.group(2) if match_charset else 'gbk'
            # 对utf8以外的网页重新编码
            if charset not in ['utf8', 'utf-8', 'UTF8', 'UTF-8']:
                result.content = result.content.decode(charset, 'ignore')

            # 获取页面标题
            re_title = re.compile(
                r'''(?ix)
                <title>
                ([^<]+)     #! title
                </title>
                ''')
            match_title = re_title.search(result.content)

            if match_title:
                return match_title.group(1)
        else:
            # 寻找标题时出错
            return url



class Get(BookmarkUtil):
    def get(self, url):
        self.url = self.validate_url(url)

        # 错误的url
        if not url:
            self.redirect('/main')
            return

        self.bookmark = Bookmark.get_by_url(self.url)
        # 未收藏
        if not self.bookmark:
            self.redirect('/bookmark/new/' + self.url)
            return

        self.render('get.html', title='get', contents=self.bookmark.to_dict())



class Set(BookmarkUtil):
    def get(self):
        self.redirect('/dashboard')

    def post(self):
        self.url = self.validate_url(self.get_argument('url', ''))

        # 错误的url
        if not self.url:
            self.redirect('/main')
            return

        self.bookmark = Bookmark.get_by_url(self.url)
        # 未收藏
        if not self.bookmark:
            self.redirect('/bookmark/new/' + self.url)
            return

        self.title = self.get_argument('title', '') or self.url
        self.desc = self.get_argument('desc', '')
        self.tags = self.get_argument('tags', '').split()

        self.bookmark.update_by_dict({
            'tags': self.tags,
            'title': self.title,
            'desc': self.desc
        })

        self.redirect('/bookmark/get/' + self.url)



class Del(BookmarkUtil):
    def get(self, url):
        self.url = self.validate_url(url)

        if self.url:
            self.bookmark = Bookmark.get_by_url(self.url)
            if self.bookmark:
                self.bookmark.delete_bookmark()

        # 错误的url / 未收藏 / 成功删除
        self.redirect('/main')



class MoveTag(Base):
    def get(self):
        # 获取要修改的tag
        self.from_name = self.get_argument('from_name', '').strip()

        if self.from_name:
            self.to_name = self.get_argument('to_name', '').strip()
            # 有目标tag，移动/重命名
            # 没目标tag，删除
            if self.to_name:
                Tag.move_tag(self.from_name, self.to_name)
            else:
                Tag.delete_tag(self.from_name)
        self.redirect('/dashboard')



class DeleteTag(Base):
    def get(self):
        self.tag_name = self.get_argument('tag_name', '').strip()
        if self.tag_name:
            Tag.delete_tag(self.tag_name)
        self.redirect('/dashboard')



class Input(Base):
    def get(self):
        self.redirect('/dashboard')


    def post(self):
        if self.request.files and self.request.files['bookmark_file']:
            self.bookmark_file = self.request.files['bookmark_file'][0]

            if self.bookmark_file['content_type'] == 'text/html':
                # 解析上传的html 编码上有点小问题
                self.bookmarks = self.parser_input(
                    self.bookmark_file['body'].decode('utf-8', 'ignore'))

                # 添加到数据库
                Bookmark.input_bookmarks(self.bookmarks)

        self.redirect('/dashboard')


    @classmethod
    def parser_input(cls, bookmark_file):
        """解析上传的文件
        返回一个字典列表
        [{'url': url, 'tags': tags, 'title': title, 'desc': desc'}, ...]
        """

        # 检查是否为 netscape bookmark file
        flag = bookmark_file.find('<!DOCTYPE NETSCAPE-Bookmark-file-1>')
        return [] if flag == -1 else cls.parser_netscape_html(bookmark_file)


    @staticmethod
    def parser_netscape_html(bookmark_file):
        """解析netscape bookmark file
        返回字典列表
        [{'url': url, 'tags': tags, 'title': title, 'desc': desc'}, ...]
        """
        bookmarks = []
        tags = []

        import re

        re_markup = re.compile(
            r'''(?ix)
            <(                                  # <
            (                                   #OR match <A HREF=""></A>
                (?P<a>A)                        # A             group('a')
                \s[^>]*                         # whitespace
                HREF=                           # HREF=
                "(?P<url>(f|ht)tps?://[^"]+)"   # "http://..."  group('url')
                [^>]+>                          # ...>
                (?P<title>[^<]+)                # title         group('title')
                </A                             # </A
            ) | (                               #OR match <H3></H3>
                (?P<h3>H3)                      # H3            group('h3')
                [^>]+>                          # ...>
                (?P<folder>[^<]+)               # folder's name group('folder')
                </H3                            # </H3
            ) | (                               #OR match </DL><P>
                /DL>                            # /DL>
                <(?P<p>P)                       # <P            group('p')
            )
            )>                                  # >
            ''')

        m_markup = re_markup.finditer(bookmark_file)
        for match in m_markup:
            if match.group('a'):
                # <A>
                bookmarks.append({
                    'url': match.group('url'),
                    'tags': tags,
                    'title': match.group('title'),
                    'desc': '',
                })
            elif match.group('h3'):
                # <H3>
                tags = tags + [match.group('folder')]
            elif match.group('p'):
                # </DL><P>
                tags = tags[:-1]

        return bookmarks



class Output(Base):
    def get(self, tag_names):
        # 从output?tags=a，跳转到output/a
        self.filter_bookmark = self.get_argument('filter', '')
        if self.filter_bookmark:
            self.tags = '+'.join(self.get_arguments('tags'))
            self.redirect('/dashboard/output/' + self.tags)
            return

        # 如果有传入tag，针对tag过滤输出
        self.tags = tag_names.replace('+', ' ').split() if tag_names else []
        self.bookmarks = Bookmark.output_bookmarks(self.tags)

        from datetime import datetime
        output_time = datetime.now()

        self.render('netscape_bookmark_file.html', time=output_time,
                    contents=self.bookmarks)



class Dashboard(Base):
    def get(self):
        self.tags = Tag.get_all_tags()
        self.render('dashboard.html', title='dashboard', contents=self.tags)
