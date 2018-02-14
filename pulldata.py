from bs4 import BeautifulSoup as bs
import requests, os, bisect, re, shutil, sys
from urllib.parse import urlparse

# import multiprocessing

blog_url = "https://dayre.me/"
blog_first_year = 2013
verbose = False
PARSER = 'lxml'

static_imgs = 'images'

# control codes: http://stackoverflow.com/a/12586667  # delete previous line print(CURSOR_UP_ONE + ERASE_LINE)

""" Getting URLs """
    
def find_active_years(soup, session):
    """ Finds years with activity between most recent post and the first year of blog 
        Doesn't add the current year, only the rest. """
    year_urls = list()
    year_ = soup.find_all(id='year')
    
    if not year_ or 1 > len(year_):
        print("-- Error getting active year: \"%s\" -- cannot find year element" % soup.title)
        return False
    
    # append current year, without url (is currently loaded in soup)
    prev_year = year_[0].a
    while (prev_year.has_attr('class') and u'disabled' not in prev_year.get('class')):
        url = prev_year[u'href']
        year_urls.append(url)
        prev_year = find_prev_year(url, session)
    
    return year_urls
    
def find_prev_year(url, session):
    """Returns the soup tag object for the link to the previous year""" 
    soup = get_soup(url, session)
    year = soup.find_all(id='year')
    
    if not year or 1 > len(year):
        print("-- Error getting active year: \"%s\" -- cannot find year element" % soup.title)
        return False
    
    return year[0].a

def find_active_months(soup):
    """ Returns a list of months (month, url) for the given year that the user was active """
    
    # filter to html list of months
    months = soup.find_all(id='months')
    if not months or 1 > len(months):
        print("-- Error getting active months: \"%s\" -- cannot find list of months" % soup.title)
        
    months = months[0].find_all('li')[1:]  # ignore the ALL link
    if 12 is not len(months):
        print("-- Error getting active months: \"%s\" -- not enough months" % soup.title)
        
    # iterate through, recording those that are active (not li.class = 'disabled')
    links = list()
    for tag in reversed(months):
        if not (tag.has_attr('class') and u'disabled' in tag.get('class')):  
            month = next(tag.a.stripped_strings)
            url = tag.a[u'href']
            links.append((month, url))
            # break  # for testing
    
    return links
    
def get_soup(url, session):
    """ Performs error checking before returning the 
        soup object of the given URL """
    
    while( True ):
        sys.stdout.write('GET: %s' % url)
        sys.stdout.flush()
        # Avoid connection error ending everything
        try:
            r = session.get(url)
            break
        except requests.exceptions.ConnectionError as e:
            print('\nConnection Error: %s' % e)
            print('Refreshing session..')
            session = requests.Session()
            
    soup = bs( r.text, PARSER )
    if r.status_code is not 200:
        raise Not200ErrorException(r.status_code, soup.title)
    
    sys.stdout.write(' -- SUCCESS\n')
    sys.stdout.flush()
    return soup
        
class Not200ErrorException(Exception):
    def __init__(self, code, text):
        self.code = code
        self.text = text
    
    def __str__(self):
        return 'Not200Error: %d %s' % (self.code, self.text)
        
def get_image_urls(soup):
    """ Extracts the web addresses for images to download """
    img_tags = soup.find_all('img')
    img_urls = set()
    for tag in img_tags: 
        src = tag[u'src']
        img_urls.add(src)  
    return list(img_urls)
    
def find_day_urls(soup, session):
    """Iterates through the current month, pulling the links for the days within that month"""
    day_links = list()  # avoid duplicate days

    while (True):
        # get the visible days' links
        for tag in soup.find_all('div'):
            if tag.has_attr('class') and u'summary_container' in tag.get('class'): 
                # day_links.append((tag.a.text, tag.a.attrs[u'href']))
                day_links.append(tag.a.attrs[u'href'])
        
        # check for more days
        next_day = soup.find_all(id='load_more_no_js')
        if next_day and len(next_day) > 0: 
            url = next_day[0].a[u'href']
            soup = get_soup(url, session)
        else: 
            break # no more days to load
          
    return day_links
    
    
    
    
""" Helper functions """

def relative_html_url(img_name, directory):
    """ Returns the relative URL of a file """
    # commonprefix http://stackoverflow.com/a/7288019
    common_prefix = os.path.commonprefix([directory, os.getcwd()])
    relative_to_cwd = os.path.relpath(common_prefix)
    return '%s/%s/%s' % (relative_to_cwd, directory[len(common_prefix):], img_name)
    
def url2filename(file_url):
    """ Extracts the file name from a URL, removing QueryString parameters """
    return os.path.basename(urlparse(file_url).path) # .netloc for domains
    
   

