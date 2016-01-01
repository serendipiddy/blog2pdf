import requests
from bs4 import BeautifulSoup as bs
import pulldata as pull
import parse_blog as parser
import activity
import sys
import os
import urlparse, shutil
from time import strptime

blog_url = "https://dayre.me/"
PARSER = 'lxml'
static_imgs = 'images2'

class blog_spider(object):
    
    def __init__(self, username, dummy = False):
        assert type(username) is str or type(username) is unicode
        self.username = username
        
        self.session = requests.Session()
        self.userdata = dict()
        self.image_urls = set()  # images to download
        self.day_urls = set()  # day name -- (yyyy_ddd) -> url
        self.userdata['activity'] = activity.Activity()
        
        url = "%s%s" % (blog_url, username)
        
        if dummy: return 
        
        while( True ):
            sys.stdout.write('GET: %s' % url)
            sys.stdout.flush()
            # Avoid connection error ending everything
            try:
                r = self.session.get(url)
                break
            except requests.exceptions.ConnectionError as e:
                print('\nConnection Error: %s' % e)
                print('Refreshing session..')
                self.session = requests.Session()
        
        sys.stdout.write(' -- SUCCESS\n')
        sys.stdout.flush()
        
        soup = bs(r.text, PARSER)
        
        if r.status_code is 200:
            self.root_soup = soup
        else:
            raise UserNotFoundError(r.status_code, username, soup.title)
            
    def __str__(self):
        return 'blog_puller for %s' % self.username
    
    def process_profile(self):
        """ Reads the profile and follow data of the user
            Raises Not200ErrorException """
        
        print('Process profile and follows')
        self.userdata.update( parser.parse_profile(self.root_soup) )
        
        # add cover and avatar images
        avatar_url = self.root_soup.find_all(id='badge_avatar')[0].img[u'src'].replace('-50p','')
        cover_url = self.root_soup.find_all(id='profiletop_cover')[0].img[u'src'].replace('-50p','')
        self.image_urls.add(avatar_url)
        self.image_urls.add(cover_url)
        
        fers_url = '%s%s/followers?id=%s' % (blog_url, self.userdata['username'], self.userdata['user_id'])
        fing_url = '%s%s/following?id=%s' % (blog_url, self.userdata['username'], self.userdata['user_id'])
        followers_soup = pull.get_soup(fers_url, self.session)
        following_soup = pull.get_soup(fing_url, self.session)
            
        # extract data from the pages
        self.userdata['followers'] = parser.parse_follows(followers_soup)
        self.userdata['following'] = parser.parse_follows(following_soup)
        
        # search for desired images
        self.image_urls.update( pull.get_image_urls( followers_soup.find_all(id='follow_container')[0] ) )
        self.image_urls.update( pull.get_image_urls( following_soup.find_all(id='follow_container')[0] ) )
        
    def month_to_int(self, month_str):
        """ convert a month's string form into its integer form """
        if len(month_str) == 3:
            return strptime(month_str,'%b').tm_mon
        if len(month_str) > 3:
            return strptime(month_str,'%B').tm_mon
        else: 
            print(" not a real month string \"%s\"" % month_str)
            return 0
        
    def discover_posts(self, update_from = None):
        """ Populates self.day_urls with user's days. 
            update_from updates posts from and including the given day.
                of the form {year: int(YYYY), month: int(MM)) """
                
        if update_from:
            u_year = update_from['year']
            u_month = update_from['month']
        
        print('Discovering user activity')
        # iterate through years and months, discovering posts' URLs
        year_urls = pull.find_active_years(self.root_soup, self.session)
        if len(year_urls) is 0:
            print('no active years found')
            return
            
        print('Discovered %d years of activity' % (len(year_urls) + 1))
        
        # iterate through years
        month_urls = list()
        year_soup = self.root_soup  # root is already the latest year
            
        for url in year_urls:
            y = url.split('/')[-1]
            sys.stdout.write('%d...' % (int(y) + 1) )
            sys.stdout.flush()
            
            # if len(month_urls == 1):  # use year's url, the month (../2016/01) seems broken for january 2016.. so use the /2016 instead
            pulled = pull.find_active_months(year_soup)
            if len(pulled) == 1:
                month_urls.append((str(int(y) + 1), '%s%s' % (blog_url, self.userdata['username'])))  # bug for 404 on "../2016/01", using "../2016" instead
                year_soup = pull.get_soup(url, self.session) # get next year
                continue
                
            """ continue to months if using update_from is active 
                  and the current soup is for an earlier year """
            if update_from: 
                if int(y)+1 < u_year:  
                    break
                elif int(y)+1 == u_year:
                    for m in pulled:
                        month_int =  self.month_to_int(m[0])
                        if (month_int >= u_month):
                            month_urls.append( m )
                else:
                    month_urls.extend( pulled )
            else:
                month_urls.extend( pull.find_active_months(year_soup) )
            year_soup = pull.get_soup(url, self.session) # get next year
        del year_soup  # be a tidy kiwi

        #  iterate through months
        print('Beginning working through months (%d)' % len(month_urls))
        for name, url in month_urls:
            print('%s - %s' % (name, url))
            month_soup = pull.get_soup(url, self.session)
            self.day_urls.update( pull.find_day_urls(month_soup, self.session) )
            sys.stdout.write('%-3s - total %2.d URLs...' % (name[:3], len(self.day_urls)))
            sys.stdout.flush()
        
        sys.stdout.write('\nComplete\n')
        sys.stdout.flush()
        
    def read_post_data(self, urls=None):
        """ Reads data from URLs, adding to users Activities.
            If no URLs are given, iterates through discovered URLs"""
        
        if urls is None:
            urls = self.day_urls
        
        print('Reading post data for %d pages' % len(urls))
        # iterate through urls, parsing the page and capturing image urls
        i = 0
        for url in urls:
            sys.stdout.write('%4d/%d days ' % (i+1, len(urls)))
            sys.stdout.flush()
            i += 1
            
            day_soup = pull.get_soup(url, self.session)
            
            # capture img urls, replacing them with just their names
            img_tags = day_soup.find_all('img')
            video_tags = day_soup.find_all('video')
            for tag in img_tags:
                src = tag[u'src']
                self.image_urls.add(src)
                # if u'http://cdnjs.cloudflare.com/ajax/libs/twemoji/1.4.1/36x36/1f1ef-1f1f4.png' == src: print(url)  # TODO: where is this image coming from?
                tag[u'src'] = pull.url2filename(src)
            for tag in video_tags:
                src = tag.get('poster')
                self.image_urls.add(src)
                tag[u'poster'] = pull.url2filename(src)
                
            # parse the page
            try:
                day_page = parser.parse_day_page(day_soup)
            except Exception as e:
                print("\nError Occurred Parsing: %s\nDay url:%s\nContinuing from next post" % (e.message, url))
                continue
            today = activity.Day(day_page['title'], day_page['day_num'], day_page['likes'], day_page['date'], day_page['link'])
            
            for post in day_page['posts']:
                self.userdata['activity'].add_post(today, post)
                sys.stdout.write('.')
                sys.stdout.flush()
            for comment in day_page['comments']:
                self.userdata['activity'].add_comment(today, comment)
                sys.stdout.write('.' % ())
                sys.stdout.flush()
                
            sys.stdout.write('\r')
            sys.stdout.flush()
            
        sys.stdout.write('\n')
        sys.stdout.flush()
        
    def download_images(self, urls=None):
        """ Reads images from URLs, saving to hdd.
            If no URLs are given, iterates through discovered image URLs"""
        
        if urls is None:
            urls = self.image_urls
            
        print('Downloading image files (%d images)' % len(urls))
        
        if not os.path.exists(static_imgs):
            os.makedirs(static_imgs)
        
        # using requests to dl images: http://stackoverflow.com/a/13137873
        i = 0
        for imgurl in urls:
            sys.stdout.write('%6d/%d imgs ' % (i+1, len(urls)))
            sys.stdout.flush()
            i += 1
            
            # check it's a relatively legitimate URL
            url = urlparse.urlparse(imgurl)
            if url.scheme == '':
                imgurl = 'http:%s' % imgurl
                
            fpath = os.path.join(static_imgs, pull.url2filename(imgurl))
            if not os.path.exists(fpath):
                while( True ):
                    sys.stdout.write('GET: %s' % imgurl)
                    sys.stdout.flush()
                    # Avoid connection error ending everything
                    try:
                        r = self.session.get(imgurl, stream=True)
                        sys.stdout.write(' -- SUCCESS\n')
                        break
                    except requests.exceptions.ConnectionError as e:
                        print('\nConnection Error: %s' % e)
                        print('Refreshing session..')
                        self.session = requests.Session()
                        
                if r.status_code == 200:
                    with open(fpath, 'wb') as f:
                        r.raw.decode_content = True
                        shutil.copyfileobj(r.raw, f)
            else: 
                sys.stdout.write(' -- Exists\r')
                sys.stdout.flush()
                
        sys.stdout.write('\n')
        sys.stdout.flush()
        
    def get_userdata(self):
        return self.userdata
        
class UserNotFoundError(Exception):
    def __init__(self, status_code, username, title):
        self.status_code = status_code
        self.username = username
        self.title = title
        self.message = '%d: User "%s" not found' % (status_code, username)
        
    def __str__(self):
        return "UserNotFound: '%s' (%d) %s" % (self.username, self.status_code, self.title)
        
    def __repr__(self):
        return self.__str__()
            
    
