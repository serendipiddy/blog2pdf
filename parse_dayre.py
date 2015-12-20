from bs4 import BeautifulSoup as bs
from activity import (Day, Activity)
import post
import urlparse
import os


PARSER = 'lxml'
youtube_link = 'youtu.be/'


""" External functions, pass in whole HTML document """

def get_user(soup_user, soup_followers, soup_following):
    """ Returns a dict() representation of a user from the HTML """
    
    user = parse_profile(soup_user)
    user['followers'] = parse_follows(soup_followers)
    user['following'] = parse_follows(soup_following)
    
    return user
    
def parse_day_page(soup):
    """ Parse the page for a day, returning the Day and Post objects """
    container = soup.find_all(id='post_main_container')[0]
    
    # get p tags, each representing a post
    posts = list()
    for p in container.find_all('p'):
        # skip the video compatibility message, which isn't a post
        if p.get('class') is not None:
            if p.get('class') == 'vjs-no-hs':
                continue  
        
        # post type is determined by the previous element
        prev = get_prev_elem(p).name 
        
        # common line of execution here, so avoids doing it in all the subsequent function calls
        replace_emoji(p)
        
        if prev == 'p' or prev == 'br':  # this is a text or quote post
            if p.get('class') is not None and p.get('class')[0] == 'quotation':
                posts.append(parse_quote(p))
            else:
                posts.append(parse_text(p))
        elif prev == 'img':     # this is a sticker or image post
            posts.append(parse_image(p))
            # use parent to check
        elif prev == 'div':     # this is a location, (class is 'map_label_address' with text 'address')
            posts.append(parse_location(p))
        elif prev == 'a':       # is a user video
            posts.append(parse_video(p))
        elif prev == 'iframe':  # is a YouTube video
            posts.append(parse_youtube(p))
    
    # discover comments
    comment_container = soup.find_all(id='comments_list')[0]
    
    comments = list()
    for c in comment_container.find_all(class_='comment'):
        comments.append(parse_comment(c))
        
    return {'posts': posts, 'comments': comments}
    
    
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
        url = urlparse.urlparse(all_names[i].a.get('href'))
        user['url'] = '%s%s'%(url.netloc, url.path)
        user['avatar_link'] = all_avatars[i].img.get('src')
        users.append(user)
    
    return users
        
def parse_comment(soup):
    username = soup.find_all(class_='comment_author')[0].text
    text = ''.join(list(soup.p.strings)[1:]) # will remove any tags within!!
    avatar_link = soup.a.img.get('src')
    return post.Comment(username, text, avatar_link)
    
""" Secondary parse """
    
def parse_text(soup):
    """ Returns a Post object of type text from the <p> soup """
    return post.Post(soup.text)

def parse_location(soup):
    """ Given the text of a location post returns a Location object"""
    map_label = get_prev_elem(soup).parent
    name = map_label.find_all(class_='map_label_name')[0].text.strip()
    address = map_label.find_all(class_='map_label_address')[0].text.strip()
    coo = map_label.parent.iframe.get('src').split('/')[-2:]
    
    return post.Location(soup.text, name, address, {'lat':float(coo[0]),'long':float(coo[1])})
    
def parse_video(soup):
    actual_link = get_prev_elem(soup).parent.parent.get('src')
    preview_image = get_prev_elem(soup).parent.parent.parent.get('poster')
    return post.User_video(soup.text, preview_image, actual_link)
    
def parse_youtube(soup):
    embed_url =  urlparse.urlparse(get_prev_elem(soup).get('src'))
    video_id = '%s%s' % (youtube_link, os.path.basename(embed_url.path))
    return post.YouTube_video(soup.text, video_id)
    
def parse_sticker(soup):
    link  = get_prev_elem(soup).get('src')
    return post.Sticker(soup.text, link)
    
def parse_quote(soup):
    return post.Quote(soup.text)
    
def parse_image(soup):
    """ Given the text of an image post, produces an Image object """
    
    # extract URL and text
    link = get_prev_elem(soup).get('src')
    text = soup.text
    
    return post.Image(text, link)
    
""" Helper functions """
    
def get_prev_elem(soup):
    """ Skips the newline chars to get to the previous element """
    s = soup.previous_element
    while s.name is None:
        s = s.previous_element
    return s
    
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
        emoji.replace_with(alt)
    