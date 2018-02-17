import boto3
import os

import pulldata as pull

from bs4 import BeautifulSoup as bs
from urllib.parse import urlparse, parse_qs, urlencode

'''
Takes an existing dayre dump and reconstructs it on AWS S3
'''

'''
index.html
followers.html
following.html
posts
 |
 |- 2018
     |
     | - january
          |
          | - images  ?
               |
               | - a.jpg
               | - b.jpg
     | - february
 ...
'''

PARSER = 'lxml'
blog_netloc = "dayre.me"

## dumpers expect soup-object html
class local_dumper():
    def __init__(self, user, root_directory):
        self.user = user
        self.root_directory = "{}/{}".format(root_directory, user)

        if not os.path.exists(self.root_directory):
            os.makedirs(self.root_directory)

    def dump_html(self, html, filename, year='', month=''):
        '''saves the given html document'''
        
        # TODO get date and name from html
        # TODO update image and post links
        # TODO use urlparse instead of hardcoded directory names
        

        output_name = "{}".format(self.root_directory)
        if year != '':
            output_name = "{}/{}".format(output_name, year)
            if not os.path.exists(output_name):
                os.makedirs(output_name)
            if month != '':
                output_name = "{}/{}".format(output_name, month)
                if not os.path.exists(output_name):
                    os.makedirs(output_name)
        output_name = "{}/{}".format(output_name, filename)

        print("Received dump for {}".format(output_name))
        
        with open(output_name, 'w') as f:
            f.write(html.prettify())

class s3_dumper():
    def __init__(self, user, s3_bucket_name, image_directory="images", video_directory="videos"):
        self.user = user
        self.image_directory = image_directory
        self.video_directory = video_directory
        self.bucket_name = s3_bucket_name

        self.s3 = boto3.resource('s3')
        self.bucket = self.s3.Bucket(self.bucket_name)
        self.path = "{}".format(user)

    def url2key(self, url):
        ''' converts a URL into an S3 object key string
                * removes query "id"
                * replaces ? with _
                * blanks protocol and netloc
        '''
        
        url_ = urlparse(url)
        
        if url_.path == "":
            # just "blog.com"
            return url
        
        url_ = url_._replace(scheme="", netloc="")
        qs = parse_qs(url_.query)
        qs.pop('id', None)
        qs.pop('v', None)
        url_ = url_._replace(query = urlencode(qs, True))
        
        filename = url_.geturl()
        
        # remove any leading /, which comes from urlparse.path
        # print("{}->{} path:".format(filename, url, url_.path))
        while filename[0] == "/":
            filename = filename[1:]
        filename = filename.replace("?","_")
            
        return filename
        
    def dump_html(self, html, url):
        filename = self.url2key(url)
        html = self.adjust_urls(html)
        self.bucket.put_object(Key=filename, Body=html.prettify(), ContentType=content_types['html'])
        
    def dump_image(self, image_data, filename):
    
        output_name = self.get_image_key(filename)
        content_type = guess_content_type(filename, image_data, image=True)
        
        self.bucket.put_object(Key=output_name, Body=image_data, ContentType=content_type)
        
    def get_image_key(self, filename):
        ''' Gets the key name for an image file in S3 '''
        return "{}/{}".format(self.path, filename)
        
    def check_exists(self, object_key):
        # print("checking for " + object_key)
        # check if image exists first
        objs = list(self.bucket.objects.filter(Prefix=object_key))
        return len(objs) > 0 and objs[0].key == object_key

    def adjust_urls(self, html):
        '''modifies URL to point to local files'''
        
        html = bs(str(html), PARSER)
        
        s3_prefix = "http://{}/{}".format(self.bucket_name,self.user)
        
        # html mimics that on the blog
        for a in html.find_all("a"):
            parsed = urlparse(a["href"])
            if parsed.netloc == blog_netloc:
                # cos the bucket can't use https via the CNAME
                # need to change host portion too
                parsed = urlparse(self.url2key(a["href"]))
                parsed = parsed._replace(netloc = self.bucket_name, scheme = "http")
                a["href"] = parsed.geturl()
        
        # css, javascript and favicon
        meta_files = dict()
        for link in html.find_all("link"):  # css and favicon
            url_ = urlparse(link.get('href'))
            if blog_netloc in url_.netloc:
                url_ = urlparse(self.url2key(link.get('href')))
                url_ = url_._replace(scheme="http", netloc=self.bucket_name)
                meta_files[str(link['href'])] = url_.geturl()
                link['href'] = url_.geturl()
                
        for link in html.find_all("script"):  # scripts
            if link.get('src'):
                url_ = urlparse(link.get('src'))
                if blog_netloc in url_.netloc:
                    url_ = urlparse(self.url2key(link.get('src')))
                    url_ = url_._replace(scheme="http", netloc=self.bucket_name)
                    meta_files[str(link['src'])] = url_.geturl()
                    link['src'] = url_.geturl() 
                
        # download files and push to s3
        for web_url, s3_url in meta_files.items():
            # print("web {} s3 {}".format(web_url, s3_url))
            s3_key = self.url2key(s3_url)
            # print("exists? {}".format(self.check_exists(s3_key)))
            if not self.check_exists(s3_key):
                # print("pulling it")
                content = pull.get_text_file(web_url)
                self.bucket.put_object(Key=s3_key, Body=content, ContentType=guess_content_type(s3_key, content))
        
        # images go to /images
        for img in html.find_all("img"):
            img["src"] = "{}/{}/{}".format(s3_prefix, self.image_directory, pull.url2filename(img["src"]))

        for video in html.find_all("video"):
            src = video.find_all("source")
            if len(src) > 0:
                the_video_link = src[0]["src"]
                src[0]["src"] = "{}/{}/{}".format(s3_prefix, self.video_directory, pull.url2filename(the_video_link))

        return html


content_types = {
    'json':'application/json',
    'doc':'application/msword',
    'pdf':'application/pdf',
    'zip':'application/zip',
    'bmp':'image/bmp',
    'css':'text/css',
    'ogg':'audio/ogg',
    'html':'text/html', 
    'htm':'text/html',
    'js':'text/javascript',
    'txt':'text/plain',
    'md':'text/plain',
    'rtf':'text/rtf',
    'gif':'image/gif',
    'png':'image/png',
    'PNG':'image/png',
    'jpeg':'image/jpeg',
    'jpg':'image/jpeg',
    'JPEG':'image/jpeg',
    'JPG':'image/jpeg',
    'tiff':'image/tiff',
    'mpeg':'audio/mpeg',
    'mp4':'video/mp4'
    }
default_type = 'binary/octet-stream'


def guess_content_type(name, content, image=False):
    ''' Figure out the content type of the blob '''
    
    extn = name.split('.')[-1]
    if extn in content_types:
        return content_types[extn]
    elif image:
        return content_types['jpeg']  # default image format
    
    if isinstance(content, str):
        data = content
    else:
        data = str(content, "utf-8")
    
    if '<html>' in data:
        # by checking this, can pick up html files that lack an extension
        return 'text/html'
     
    else:
        return default_type
        
# content_type = guess_content_type(blob_name, blob_content)
# bucket.put_object(Key=blob_name, Body=blob_content, ContentType=content_type)