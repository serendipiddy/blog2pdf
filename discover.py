import requests
from bs4 import BeautifulSoup as bs
import pulldata as pull
import parse_dayre as parser
import activity
import sys
import os
import urlparse, shutil

dayre_url = "https://dayre.me/"
PARSER = 'lxml'
static_imgs = 'images2'

class dayre_spider(object):
    
    def __init__(self, username, dummy = False):
        assert type(username) is str or type(username) is unicode
        self.username = username
        
        self.session = requests.Session()
        self.userdata = dict()
        self.image_urls = set()  # images to download
        self.day_urls = set()  # day name -- (yyyy_ddd) -> url
        self.userdata['activity'] = activity.Activity()
        
        url = "%s%s" % (dayre_url, username)
        
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
        return 'dayre_puller for %s' % self.username
    
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
        
        fers_url = '%s%s/followers?id=%s' % (dayre_url, self.userdata['username'], self.userdata['user_id'])
        fing_url = '%s%s/following?id=%s' % (dayre_url, self.userdata['username'], self.userdata['user_id'])
        followers_soup = pull.get_soup(fers_url, self.session)
        following_soup = pull.get_soup(fing_url, self.session)
            
        # extract data from the pages
        self.userdata['followers'] = parser.parse_follows(followers_soup)
        self.userdata['following'] = parser.parse_follows(following_soup)
        
        # search for desired images
        self.image_urls.update( pull.get_image_urls( followers_soup.find_all(id='follow_container')[0] ) )
        self.image_urls.update( pull.get_image_urls( following_soup.find_all(id='follow_container')[0] ) )
        
    def discover_posts(self):
        """ Populates self.day_urls with user's days """
        
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
            month_urls.extend( pull.find_active_months(year_soup) )
            year_soup = pull.get_soup(url, self.session) # get next year
        del year_soup  # be a tidy kiwi

        print('Beginning working through months (%d)' % len(month_urls))
        #  iterate through months
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
            for tag in img_tags:
                src = tag[u'src']
                self.image_urls.add(src)
                tag[u'src'] = pull.url2filename(src)
            
            # parse page
            day_page = parser.parse_day_page(day_soup)
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
                        break
                    except requests.exceptions.ConnectionError as e:
                        print('\nConnection Error: %s' % e)
                        print('Refreshing session..')
                        self.session = requests.Session()
                        
                sys.stdout.write(' -- SUCCESS\n')
                sys.stdout.flush()
                
                if r.status_code == 200:
                    with open(fpath, 'wb') as f:
                        r.raw.decode_content = True
                        shutil.copyfileobj(r.raw, f)
              
    def get_userdata(self):
        return self.userdata
        
class UserNotFoundError(Exception):
    def __init__(self, status_code, username, title):
        self.status_code = status_code
        self.username = username
        self.title = title
        
    def __str__(self):
        return "UserNotFound: '%s' (%d) %s" % (self.username, self.status_code, self.title)
        
    def __repr__(self):
        return self.__str__()
            
    
