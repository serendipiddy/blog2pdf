from bs4 import BeautifulSoup as bs
from activity import (Day, Activity)
import post
from urllib.parse import urlparse
import os


PARSER = 'lxml'
youtube_link = 'youtu.be/'
date_format = '%A, %d %b %Y'  # Monday, 01 Dec 2014


""" External functions, pass in whole HTML document """

def get_user(soup_user, soup_followers, soup_following):
    """ Returns a dict() representation of a user from the HTML """
    
    user = parse_profile(soup_user)
    user['followers'] = parse_follows(soup_followers)
    user['following'] = parse_follows(soup_following)
    
    return user
    
def parse_day_page(soup):
    """ Parse the page for a day, returning the Day and Post objects """
    # title, day_num, likes, date, link
    day_data = dict()
    meta = soup.find_all(id='post_meta')
    if meta:
        meta = meta[0]
        
        if not soup.find_all(id='post_header_title'): 
            title = ''  # find_with_attr(soup, 'meta', 'property', 'og:title').get('content')
        else:
            title = soup.find_all(id='post_header_title')[0].text
        day_num = meta.find_all(id='post_header_day_no')[0].text.split(' ')[-1]
        likes = meta.find_all(class_='ajax_like_count')[0].text
        date = meta.find_all(id='post_header_date')[0].text
        link = find_with_attr(soup, 'meta', 'property', 'og:url').get('content')
        
        day_data['title'] = title
        day_data['day_num'] = int( day_num )
        day_data['likes'] = int( likes )
        day_data['date'] = date
        day_data['link'] = link

    container = soup.find_all(id='post_main_container')[0]
    
    # get p tags, each representing a post
    posts = list()
    
    # remove the empty children
    # TODO this doesn't work in python3 / anymore.. weird
    for child in container.children:
        if str(child) == u'\n':
            child.extract()
    
    for p in container.find_all('p'):
        if p.get('class') is not None:
            # skip the video compatibility message, which isn't a post
            if u'vjs-no-js' in p.get('class'):
                continue  
        
        replace_emoji(p)
        
        # post's type is determined by the previous element
        
        prev = p.previous_sibling
        while prev == '\n':
            prev.extract()
            prev = p.previous_sibling
        
        # common line of execution here, so avoids doing it in all the subsequent function calls
        if prev == None or prev.name == 'p':  # this is a text or quote post
            if p.get('class') is not None and p.get('class')[0] == 'quotation':
                posts.append(parse_quote(p))
            else:
                posts.append(parse_text(p))
            continue
        elif p.get('class') is not None and 'private_post' in p.get('class'):  # private post
            posts.append(parse_private(p))
        elif 'action_image' in prev.get('class'):     # this is an image post
            posts.append(parse_image(p))
        elif 'action_sticker' in prev.get('class'):     # this is a sticker
            posts.append(parse_sticker(p))
        elif 'action_location' in prev.get('class'):     # this is a location, (class is 'map_label_address' with text 'address')
            posts.append(parse_location(p))
        elif 'action_video' in prev.get('class'):       # is a user video or youtube
            if prev.video is not None:  # difference between video and youtube
                posts.append(parse_video(p))
            else:
                posts.append(parse_youtube(p))
    
    # discover comments
    comment_container = soup.find_all(id='comments_list')[0]
    
    comments = list()
    for c in comment_container.find_all(class_='comment'):
        comments.append(parse_comment(c))
        
    rv = {'posts': posts, 'comments': comments}
    rv.update(day_data)
    return rv
    
    
""" Internal functions, pass in a section of an HTML document """

""" Primary parse """
    
def parse_profile(soup):
    user = dict()
    names = get_content(soup, 'meta', 'name', 'keywords').split(', ')
    user['name'] = names[0]
    user['username'] = names[1]
    user['url'] = soup.find_all('p', class_='dayre_link')[0].text
    user['user_id'] = get_content(soup, 'meta', 'name', 'userId')
    avatar_link = soup.find_all('div', id='badge_avatar')[0]
    user['avatar_link'] = avatar_link.img.get('src')
    user['bio'] = get_content(soup, 'meta', 'name', 'description')
    return user

def parse_follows(soup):
    """ Returns a list of user dictionaries.
        soup can be either followers or following """
        
    follows = soup.find_all('div', class_='user')
    
    # assumes the order of each will be the same between each search..
    all_usernames = soup.find_all('span', class_=['username'])
    all_names = soup.find_all('span', class_=['fullname'])
    all_avatars = soup.find_all('div', class_=['user_avatar'])
    
    users = list()
    for i in range(len(follows)):
        user = dict()
        user['username'] = all_usernames[i].a.text
        user['name'] = all_names[i].a.text
        url = urlparse(all_names[i].a.get('href'))
        user['url'] = '%s%s'%(url.netloc, url.path)
        user['avatar_link'] = all_avatars[i].img.get('src')
        users.append(user)
    
    return users
        
def parse_comment(soup):
    username = soup.find_all(class_='comment_author')[0].text
    replace_emoji(soup.p)
    text = ''.join(list(soup.p.strings)[1:])[1:]  # will remove any tags within!! # skip first element, it's the username
    avatar_link = soup.a.img.get('src')
    return post.Comment(username, text, avatar_link)
    
""" Secondary parse """
    
def parse_text(soup):
    """ Returns a Post object of type text from the <p> soup """
    return post.Post(soup.text)
    
def parse_private(soup):
    return "Private post"

def parse_location(soup):
    """ Given the text of a location post returns a Location object"""
    map_label = soup.previous_sibling.find_all(class_='map_label')[0]
    name = map_label.find_all(class_='map_label_name')[0].text.strip()
    address = map_label.find_all(class_='map_label_address')
    if len(address) > 0:
        address = address[0].text.strip()
    else:
        address = ''
    coo = map_label.parent.iframe.get('src').split('/')[-2:]
    
    return post.Location(soup.text, name, address, {'lat':float(coo[0]),'long':float(coo[1])})
    
def parse_video(soup):
    actual_link = soup.previous_sibling.source.get('src')
    preview_image = soup.previous_sibling.video.get('poster')
    return post.User_video(soup.text, preview_image, actual_link)
    
def parse_youtube(soup):
    embed_url =  urlparse(soup.previous_sibling.div.iframe.get('src'))
    video_id = '%s%s' % (youtube_link, os.path.basename(embed_url.path))
    return post.YouTube_video(soup.text, video_id)
    
def parse_sticker(soup):
    link  = soup.previous_sibling.img.get('src')
    return post.Sticker(soup.text, link)
    
def parse_quote(soup):
    return post.Quote(soup.text)
    
def parse_image(soup):
    """ Given the text of an image post, produces an Image object """
    
    # extract URL and text
    the_div = soup.previous_sibling
    link = the_div.img.get('src')
    text = soup.text
    location = None
    
    # check for location
    if len(the_div.find_all(class_='location_caption')) > 0:
        location = the_div.find_all(class_='location_caption')[0].text
    
    return post.Image(text, link, location)
    
""" Helper functions """
    
# def get_prev_elem(soup):
    # """ Skips the newline chars to get to the previous element """
    # s = soup.previous_element
    # while s.name is None:
        # s = s.previous_element
    # return s
    
def find_with_attr(soup, tag, attr, val):
    """ Returns the first occurrence of a tag 'tag' with the attribute 'attr' of value 'val' """
    found = soup.find_all(tag)
    for i in found:
        if i.get(attr) == val:
            return i
    return None

def get_content(soup, tag, attr, val):
    """ Returns the content value of the found tag, or None if not found """
    found = find_with_attr(soup, tag, attr, val)
    if found is None:
        return None
    return found.get('content')
    
def replace_emoji(soup):
    """ checks for and replaces any emoji tags with Unicode equivalent """
    
    for emoji in soup.find_all(class_='emoji'):
        alt = emoji.get('alt')  # stores the Unicode equivalent
        src = os.path.basename(urlparse(emoji.get('src')).path)
        tag = '<emoji alt="%s" src="%s" />' % (alt, src)
        emoji.replace_with(alt)
        
    
