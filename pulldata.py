from bs4 import BeautifulSoup as bs
import requests, os, bisect, re, shutil, sys
from urlparse import urlparse

# import multiprocessing

dayre_url = "https://dayre.me/"
dayre_first_year = 2013
verbose = False
PARSER = 'lxml'

static_imgs = 'images'

# control codes: http://stackoverflow.com/a/12586667  # delete previous line print(CURSOR_UP_ONE + ERASE_LINE)

def dump_file(filename, contents, force=False):
    """Dumps the contents with the given filename. If it exists, use force=True to override """
    if not os.path.exists(filename) or force:
        with open(filename, 'w') as file:
            file.write(contents.encode('utf8'))
        
def download_img(imgurl, session):
    """ Downloads the file at imgurl and saves to filesystem """
    # using requests to dl images: http://stackoverflow.com/a/13137873
    
    # check it's a relatively legitimate URL
    url = urlparse(imgurl)
    if url.scheme == '':
        imgurl = 'http:%s' % imgurl
    
    fpath = os.path.join(static_imgs, url2filename(imgurl))
    if not os.path.exists(fpath):
        if verbose: print('downloading %s' % url2filename(imgurl))
        r = session.get(imgurl, stream=True)
        if r.status_code == 200:
                with open(fpath, 'wb') as f:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, f)
        
def filter_html(soup):
    soup.find_all('link')

def get_day(url, session):
    """ Downloads the html file at url including images """
    soup = bs(session.get(url).text, PARSER)
    imgs = get_and_replace_img_urls(soup)
    
    # filter_html(soup)
    day_name = '%s_%s' % (soup.find_all(id='post_header_day_no')[0].text, soup.find_all(id='post_header_date')[0].text)
    dump_file('%s_%s.html' % (day_name, url2filename(url)), soup.prettify())  # change this to use the day number, not the hashed value
    
    for img in imgs:  
        download_img(img, session)
        
    if verbose: print('done - %s' % soup.title.text)
    
def relative_html_url(img_name, directory):
    """ Returns the relative URL of a file """
    # commonprefix http://stackoverflow.com/a/7288019
    common_prefix = os.path.commonprefix([directory, os.getcwd()])
    relative_to_cwd = os.path.relpath(common_prefix)
    return '%s/%s/%s' % (relative_to_cwd, directory[len(common_prefix):], img_name)
    
def url2filename(file_url):
    """ Extracts the file name from a URL, removing QueryString parameters """
    return os.path.basename(urlparse(file_url).path) # .netloc for domains
    
def get_and_replace_img_urls(soup):
    """ Replaces the image urls with their local counterpart. Returns list of urls without duplicates. 
        Note: this modifies the BSoup object, so will work only once to return URLs """
    img_tags = soup.find_all('img')
    img_urls = set()
    for tag in img_tags: 
        src = tag[u'src'].replace('-50p','')
        img_urls.add(src)  # pull img urls
        tag[u'src'] = relative_html_url(url2filename(src), static_imgs)  # replace html src with local path
    return list(img_urls)  # return list of urls
    
def get_active_months_links(soup):
    """Gets a list of the months for the current year that the user was active"""
    
    # filter to html list of months
    months = soup.find_all(id='months')
    if not months or 1 > len(months):
        print("-- Error getting active months: \"%s\" -- cannot find list of months" % soup.title)
        
    months = months[0].find_all('li')
    if 13 is not len(months):
        print("-- Error getting active months: \"%s\" -- not enough months" % soup.title)
        
    # iterate through, recording those that are active
    links = list()
    i = 1
    while i < 13:
        # li tag has class 'disabled' for inactive months
        if not (months[i].has_attr('class') and u'disabled' in months[i].get('class')):  
            links.append((months[i].a.stripped_strings.next(), months[i].a[u'href']))
        i += 1
    
    return links
    
def get_current_days(soup):
    """ Gets links to the currently visible days """
    links = list()
    for tag in soup.find_all('div'):
        if tag.has_attr('class') and u'summary_container' in tag.get('class'): 
            # print(tag.get('class'))
            # print('%s - %s' % (tag.a.text, tag.a.attrs[u'href']))
            links.append((tag.a.text, tag.a.attrs[u'href']))
    return links
            
def next_days_url(soup):
    """ Returns the url of the next page, False if no more pages """
    next = soup.find_all(id='load_more_no_js')
    if next and len(next) > 0: 
        return next[0].a[u'href']
    else: 
        return False
            
def get_day_urls(soup, session):
    """Iterates through the current month, pulling the links for the days within that month"""
    day_links = list()  # avoid duplicate days

    while (True):
        day_links.extend(get_current_days(soup))
        
        # check for more days
        url = next_days_url(soup)
        if not url: 
            break
        else:
          r = session.get(url)
          soup = bs(r.text, PARSER)
          
    return day_links
    
def get_prev_year(url, session):
    """Returns the soup tag object for the link to the previous year""" 
    soup = bs(session.get(url).text, PARSER)
    year = soup.find_all(id='year')
    
    if not year or 1 > len(year):
        print("-- Error getting active year: \"%s\" -- cannot find year element" % soup.title)
        return False
    
    return year[0].a
    
def get_active_years(soup, session):
    """ Finds years with activity between most recent post and the first year of dayre """
    year_urls = list()
    year_ = soup.find_all(id='year')
    
    if not year_ or 1 > len(year_):
        print("-- Error getting active year: \"%s\" -- cannot find year element" % soup.title)
        return False
    
    year_urls.append((year_[0].span.text,'-'))  # append current year, without url (is currently loaded in soup)
    prev_year = year_[0].a
    
    while (prev_year.has_attr('class') and u'disabled' not in prev_year.get('class')):
        # print ('appending year %s - %s' % (prev_year[u'href'].split('/')[-1], prev_year[u'href']))
        year_urls.append((prev_year[u'href'].split('/')[-1], prev_year[u'href']))
        prev_year = get_prev_year(prev_year[u'href'], session)
    
    return year_urls
    
# trying stuff
def trying1():
    for para in soup.find_all('p'): 
        if [u'day'] == para.get('class'): 
            print(para)
            a = para
    
def get_profile(username, soup, session):
    """ Retrieves the home page, avatar, followers and following users """
    print('dumping index and follow pages')
    imgs = set()
    # get avatar
    avatar_url = soup.find_all(id='badge_avatar')[0].img[u'src'].replace('-50p','')
    cover_url = soup.find_all(id='profiletop_cover')[0].img[u'src'].replace('-50p','')
    soup.find_all(id='badge_avatar')[0].img[u'src'] = relative_html_url(url2filename(avatar_url), static_imgs)
    soup.find_all(id='profiletop_cover')[0].img[u'src'] = relative_html_url(url2filename(cover_url), static_imgs)
    imgs.add(avatar_url)
    imgs.add(cover_url)
    
    # follow pages
    followers = bs(session.get(soup.find_all(class_= u'count_modal_link')[0][u'href']).text, PARSER)
    following = bs(session.get(soup.find_all(class_= u'count_modal_link')[1][u'href']).text, PARSER)
    
    imgs.update(get_and_replace_img_urls(followers))
    imgs.update(get_and_replace_img_urls(following))
    
    for img in imgs:  
        big_img = img  # get in high resolution
        download_img(big_img, session)
    
    # download profile html, updating the file
    dump_file('%s.html' %  username, soup.prettify(), True)
    dump_file('followers.html', followers.prettify(), True)
    dump_file('following.html', following.prettify(), True)
    
def get_user_posts(username):
    """ Pulls users posts, placing them in a directory under their username """
    
    print('Accessing user account "%s" through web. This may take a while.' % username)
    s = requests.Session()
    
    # get and check user exists
    user_url = "%s%s" % (dayre_url, username)
    r = s.get(user_url)
    soup = bs(r.text, PARSER)
    
    if r.status_code is not 200:
        print("-- Error pulling data: %s" % soup.title)
        return False
    
    print('Account found..')
    
    # open fs, creating user directory # http://stackoverflow.com/a/1274465 
    if not os.path.exists(username):
        os.makedirs(username)
    if not os.path.exists(static_imgs):
        os.makedirs(static_imgs)
    
    # set the directory for images
    global static_imgs
    static_imgs = os.path.realpath(static_imgs)
    
    # dump the home html file to the user's directory
    os.chdir(username)
    get_profile(username, soup, s)
    
    #  pull links to years, months, days
    years = get_active_years(soup, s)
    if len(years) is 0:
        print('no active years found')
        sys.exit(0)
        
    #  create an index of years/months available.. display progress through these.
    print('found %d years of activity, beginning with most recent activity:' % len(years))
    
    '''
    TODO: Check for changes to most recent day
        * get most recent day from filesystem
        * extract the url from its filename or extract the day and flag it **
            * flagging the day would enable the application to stop instead of checking all
        
        But this should wait until step 2 is complete, as it will be easier and less redundancy at these early stages.
        Being able to parse the dayre posts and extract them makes it more powerful and a little simpler too.
    '''
    
    #  iterate through years
    for i in xrange(len(years)):
        sys.stdout.write('  %s - Discovering months\r' % years[i][0])
        sys.stdout.flush()
        
        months = get_active_months_links(soup)
        print('  %s - %2d months           ' % (years[i][0],len(months)))
        
        if len(months) == 0:
            continue
        
        if not os.path.exists(years[i][0]):
            os.makedirs(years[i][0])
        os.chdir(years[i][0])
        
        #  iterate through months of the current year
        for m in xrange(len(months), 0, -1):
            if not os.path.exists(months[m-1][0]):
                os.makedirs(months[m-1][0])
            os.chdir(months[m-1][0])
            
            month_soup = bs(s.get(months[m-1][1]).text, PARSER)
            days = get_day_urls(month_soup, s)
            #  if verbose: print('  %s - %s - %2.d days - %s' % (years[i][0], months[m-1][0][:3], len(days), months[m-1][1]))
            sys.stdout.write('    %s -  0/%2.d days \r' % (months[m-1][0][:3], len(days)))
            sys.stdout.flush()
            
            #  iterate through days of the current month, dumping the page and images of each day
            for d in xrange(len(days)):
                sys.stdout.write('    %s - %2.d/%2.d days \r' % (months[m-1][0][:3], d+1, len(days)))
                sys.stdout.flush()
                get_day(days[d][1], s)
                #  if verbose:  print('      %-3s - %s' % (days[d][0],days[d][1]))
        
            os.chdir('..')
        if i+1 < len(years): #  if not the last year, proceed to next year url
            soup = bs(s.get(years[i+1][1]).text, PARSER)
        os.chdir('..')
        
    print('finished!')
    
    return True
