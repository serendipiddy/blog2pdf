import requests
from bs4 import BeautifulSoup as bs
import pulldata as pull
import parse_blog as parser
import activity
import sys
import os
import shutil
from urllib.parse import urlparse
from time import strptime, sleep
from datetime import datetime,timedelta
import traceback
import dumpers
from io import BytesIO

blog_url = "https://dayre.me/"
PARSER = 'lxml'
static_imgs = 'images'
videos = 'videos'
default_local_folder = "export_html"

wait_time = 20  # seconds between retry after a GET fails
retry_limit = 10  # attempts
delay_time = timedelta(seconds=1)  # seconds between successive requests
next_request_time = datetime.now()

bucket_name = "dayre.iddy.kiwi"

class blog_spider(object):
    
    def __init__(self, username, dummy = False, export = False, export_location = "local", use_s3=False):
        assert type(username) is str or type(username) is unicode
        self.username = username
        
        self.session = requests.Session()
        pull.login(self.session)
        
        self.userdata = dict()
        self.image_urls = set()  # images to download
        self.video_urls = set()  # images to download
        self.day_urls = set()  # day name -- (yyyy_ddd) -> url
        self.userdata['activity'] = activity.Activity()
        self.export = export
        self.export_location = export_location
        self.use_s3 = use_s3
        
        pull.set_cookie(self.session)
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
                pull.set_cookie(self.session)
        
        sys.stdout.write(' -- SUCCESS\n')
        sys.stdout.flush()
        
        soup = bs(r.text, PARSER)
        
        if r.status_code is 200:
            self.root_soup = soup
        else:
            raise UserNotFoundError(r.status_code, username, soup.title)
        
        if export_location == "local":
            self.dumper = dumpers.local_dumper(username, default_local_folder) 
        if export_location == "s3" or self.use_s3: ## export_location: == "s3":
            self.dumper = dumpers.s3_dumper(username, bucket_name)
            
    def __str__(self):
        return 'blog_puller for %s' % self.username
    
    def process_profile(self, save_html=False):
        """ Reads the profile and follow data of the user
            Raises Not200ErrorException """
        
        print('Process profile and follows')
        
        # add cover and avatar images
        avatar = self.root_soup.find_all(id='badge_avatar')[0]
        cover = self.root_soup.find_all(id='profiletop_cover')[0]
        avatar_url = avatar.img[u'src'].replace('-50p','')
        cover_url = cover.img[u'src'].replace('-50p','')
        # add
        self.image_urls.add( avatar_url )
        self.image_urls.add( cover_url )
        # localise
        avatar.img[u'src'] = pull.url2filename(avatar_url)
        cover.img[u'src'] = pull.url2filename(cover_url)

        if self.export:
            self.dumper.dump_html(self.root_soup, self.username.strip())
        self.userdata.update( parser.parse_profile(self.root_soup) )
        
        # Followers
        fers_url = '%s%s/followers?id=%s' % (blog_url, self.userdata['username'].strip(), self.userdata['user_id'])
        fing_url = '%s%s/following?id=%s' % (blog_url, self.userdata['username'].strip(), self.userdata['user_id'])
        
        if self.export:
            dumper = self.dumper
        else:
            dumper = None
        followers_soup = pull.get_soup(fers_url, self.session, dumper=dumper)
        following_soup = pull.get_soup(fing_url, self.session, dumper=dumper)
        
        # extract data from the pages
        # search for and update url for desired images
        for tag in set(followers_soup.find_all(id='follow_container')[0].find_all('img')):
            src = tag[u'src']
            self.image_urls.add(src)
            tag[u'src'] = pull.url2filename(src)
        
        for tag in set(following_soup.find_all(id='follow_container')[0].find_all('img')):
            src = tag[u'src']
            self.image_urls.add(src)
            tag[u'src'] = pull.url2filename(src)

        # if self.export:
            # self.dumper.dump_html(followers_soup, "followers.html")
            # self.dumper.dump_html(following_soup, "following.html")
        self.userdata['followers'] = parser.parse_follows(followers_soup)
        self.userdata['following'] = parser.parse_follows(following_soup)
        
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
        if self.export:
            year_urls = pull.find_active_years(self.root_soup, self.session, dumper=self.dumper)
        else:
            year_urls = pull.find_active_years(self.root_soup, self.session)
        if len(year_urls) is 0:
            print('no active years found')
            return
            
        print('Discovered %d years of activity' % len(year_urls))
        
        # iterate through years
        year_soup = self.root_soup  # root is already the latest year
        # update_from = 2017
        
        for url in sorted(year_urls, reverse=True):
            month_urls = list()
            y = url.split('/')[-1]
            
            ## JUST FOR DEBUG
            # if int(y) != 2018:
                # continue

            sys.stdout.write('{}...'.format(y))
            # sys.stdout.write('%d...' % (int(y) + 1) )
            sys.stdout.flush()
            
            # bug seems fine now.. # if len(month_urls == 1):  # use year's url, the month (../2016/01) seems broken for january 2016.. so use the /2016 instead
            # pulled = pull.find_active_months(year_soup)
            # print("Year_soup: {} len:{}".format(y,pulled))
            # if len(pulled) == 1:
                # temp_url = "{}{}/{}".format(blog_url, self.userdata['username'], int(y), )
                # print("temp: {}".format(temp_url))
                # month_urls.append(temp_url)  # bug for 404 on "../2016/01", using "../2016" instead
                # if self.export:
                    # year_soup = pull.get_soup(url, self.session, dumper=self.dumper) # get next year
                # else:
                    # year_soup = pull.get_soup(url, self.session) # get next year
                # continue
                
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
                
            if self.export:
                year_soup = pull.get_soup(url, self.session, dumper=self.dumper) # get next year
            else:
                year_soup = pull.get_soup(url, self.session) # get next year
            
            # if self.export and len(month_urls) > 0:
                # self.dumper.dump_html(year_soup, int(year))
                
            #  iterate through months
            print('Beginning working through months (%d)' % len(month_urls))
            for name, url in month_urls:
                print('%s - %s' % (name, url))
                if self.export:
                    month_soup = pull.get_soup(url, self.session, dumper=self.dumper)
                else:
                    month_soup = pull.get_soup(url, self.session)
                self.day_urls.update( pull.find_day_urls(month_soup, self.session, img_list=self.image_urls) )
                sys.stdout.write('%-3s - total %2.d URLs...' % (name[:3], len(self.day_urls)))
                sys.stdout.flush()
                
                # if self.export:
                    # self.dumper.dump_html(month_soup, self.month_to_int(name), year=int(y)+1)
            
        # del year_soup  # be a tidy kiwi

        
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
            
            if self.export:
                day_soup = pull.get_soup(url, self.session, dumper=self.dumper)
            else:
                day_soup = pull.get_soup(url, self.session)
            
            # capture img urls, replacing them with just their names
            img_tags = day_soup.find_all('img')
            video_tags = day_soup.find_all('video')
            for tag in img_tags:
                src = tag['src']
                self.image_urls.add(src)
                # if u'http://cdnjs.cloudflare.com/ajax/libs/twemoji/1.4.1/36x36/1f1ef-1f1f4.png' == src: print(url)  # TODO: where is this image coming from?
                tag['src'] = pull.url2filename(src)
            for tag in video_tags:
                src = tag.get('poster')
                self.image_urls.add(src)
                tag['poster'] = pull.url2filename(src)
                
                vsrc = tag.find_all("source")
                if len(vsrc) > 0:
                    src = vsrc[0]['src']
                    self.video_urls.add(src)
                    vsrc[0]['src'] = pull.url2filename(src)
                
            # parse the page
            try:
                day_page = parser.parse_day_page(day_soup)
            except Exception as e:
                print("\nError Occurred Parsing: %s\nDay url:%s\nContinuing from next post" % (e, url))
                print(traceback.format_exc())
                continue
            today = activity.Day(day_page['title'], day_page['day_num'], day_page['likes'], day_page['date'], day_page['link'])

            # if self.export:
                # page_title = os.path.join(static_imgs, pull.url2filename(today.link))
                # print("page title: "+page_title)
                # # page_title = today.link.split('/')[-1]
                # page_year = today.date.year
                # page_month = today.date.strftime("%B")
                # self.dumper.dump_html(day_soup, "{}.html".format(page_title), year=page_year, month=page_month)
            
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
        
    def download_videos(self, urls=None):
        """ Reads video from URLs, saving to hdd.
            If no URLs are given, iterates through discovered video URLs"""
            
        if urls == None:
            self.download_images(self.video_urls, path_prefix=videos)
        else:
            self.download_images(urls)
        
        
    def download_images(self, urls=None, next_request_time=next_request_time, path_prefix=static_imgs):
        """ Reads images from URLs, saving to hdd.
            If no URLs are given, iterates through discovered image URLs"""
        
        if urls is None:
            urls = self.image_urls
            
        print('Downloading image files (%d images)' % len(urls))
        
        if not os.path.exists(static_imgs) and not self.use_s3:
            os.makedirs(static_imgs)
        
        # using requests to dl images: http://stackoverflow.com/a/13137873
        i = 0
        for imgurl in urls:
            sys.stdout.write('%6d/%d imgs ' % (i+1, len(urls)))
            sys.stdout.flush()
            i += 1
            
            # check it's a relatively legitimate URL
            url = urlparse(imgurl)
            if url.scheme == '':
                imgurl = 'http:%s' % imgurl
                
            fpath = os.path.join(path_prefix, pull.url2filename(imgurl))
            if (not self.use_s3 and not os.path.exists(fpath)) or (self.use_s3 and not self.dumper.check_exists(self.dumper.get_image_key(fpath))):
                count = 0
                while( True ):
                    sys.stdout.write('GET: %s' % imgurl)
                    sys.stdout.flush()
                    # Avoid connection error ending everything

                    # delay successive requests
                    if datetime.now() < next_request_time:
                        sleep(1)
                    next_request_time = datetime.now() + delay_time

                    try:
                        r = self.session.get(imgurl, stream=True)
                        sys.stdout.write(' -- SUCCESS\n')
                        break
                    except requests.exceptions.ConnectionError as e:
                        print('\nConnection Error: %s' % e)
                        print('Refreshing session..')
                        self.session = requests.Session()
                        pull.set_cookie(self.session)

                    if r.status_code >= 500 and r.status_code <= 599 and count < retry_limit:
                        print("500 error downloading images, waiting to retry (attempt {} for {})".format(count, imgurl))
                        count += 1
                        sleep(wait_time)
                    if r.status_code >= 400 and r.status_code <=499:
                        print("{} error downloading image, skipping {}".format(r.status_code, imgurl))
                    if count > retry_limit:
                        break
                        
                if r.status_code == 200:
                    if self.use_s3:
                        self.dumper.dump_image(r.content, fpath)
                    else:
                        with open(fpath, 'wb') as f:
                            r.raw.decode_content = True
                            shutil.copyfileobj(r.raw, f)
                else:
                    print("Downloading image failed, status code:{}".format(r.status_code))
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
            

