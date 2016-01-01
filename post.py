import datetime
import re

hashtag_re = r'#(\w+)'
usertag_re = r'@(\w+)'

class Post(object):
    def __init__(self, text):
        assert type(text) is str or type(text) is unicode
        # assert len(text.strip()) < 500
        self.text = text.strip()
        
        self.hashtags = list()
        self.usertags = list()
        
        # audit hash and user tags
        for tag in re.findall(hashtag_re, text):
            if tag not in self.hashtags:
                self.hashtags.append(tag)
        for tag in re.findall(usertag_re, text):
            if tag not in self.usertags:
                self.usertags.append(tag)
    
    def __str__(self):
        text_length = min(len(self.text), 20)
        return '%s: %s' % (type(self).__name__, self.text[:text_length])
        
    def __repr__(self):
        return self.__str__()
    
class Comment(object):
    def __init__(self, username, text, avatar_link):
        assert type(username) is str or type(username) is unicode
        assert type(text) is str or type(text) is unicode
        assert type(avatar_link) is str or type(avatar_link) is unicode
        self.username = username
        self.avatar_link = avatar_link
        self.text = text
        
        self.usertags = list()
        
        # audit user tags
        for tag in re.findall(usertag_re, text):
            if tag not in self.usertags:
                self.usertags.append(tag)
        
    def __str__(self):
        text_length = min(len(self.text), 20)
        return '%s: %s' % (self.username, self.text[:text_length])
        
    def __repr__(self):
        return self.__str__()

class Quote(Post):
    def __init__(self, text):
        super(self.__class__, self).__init__(text)

class Image(Post):
    def __init__(self, text, link, location=None):
        super(self.__class__, self).__init__(text)
        self.link = link
        self.location = location

class Location(Post):
    def __init__(self, text, name, address, coordinates):
        super(self.__class__, self).__init__(text)

        assert type(name) == str or type(name) == unicode
        assert type(address) == str or type(address) == unicode
        assert type(coordinates['lat']) == float
        assert type(coordinates['long']) == float
        # TODO assertions on coordinates (limits of lat and long -180:180?)
        
        self.name = name
        self.address = address
        self.coordinates = coordinates

class Sticker(Post):
    def __init__(self, text, link):
        super(self.__class__, self).__init__(text)
        assert type(link) == str
        self.link = link
        
class YouTube_video(Post):
    def __init__(self, text, url):
        super(self.__class__, self).__init__(text)
        assert type(url) == str
        self.url = url

class User_video(Post):
    def __init__(self, text, preview_link, link):
        super(self.__class__, self).__init__(text)
        assert type(preview_link) == str
        assert type(link) == str
        self.preview_link = preview_link
        self.link = link