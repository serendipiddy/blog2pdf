import argparse, sys
import pulldata
import activity
import parse_blog
from discover import *
import pickle
import cmd
import re
import datetime
import post
import textwrap
import dicttoxml
from tex_export import data2tex
import json
import os
from touchup_json import PostLinkFixer
from os import listdir
from os.path import isfile, join

from makepage import generate_indices

# def get_args():
    # parser = argparse.ArgumentParser(description='Tool for creating a PDF from a user\'s Blog data.')
    # parser.add_argument('username', help='Username of user')
    # parser.add_argument('-d', '--dump', action='store_true', help='Include to simply dump all user day and image data as HTML')
    
    # return parser.parse_args()

# def main():
    # # parse args, get user name
    # parser = get_args()
    # print('User: %s' % parser.username)
    
    # if parser.dump:
        # show_users_pickle(parser.username)
        # sys.exit(0)
        
    # get_data(parser.username)
    
def get_data(username, use_s3=False):
    print('This will take a long time ~~')
    print('Initiating spider')
    try:
        # create blog_puller
        ds = blog_spider(username, export=True, use_s3=use_s3)
    except UserNotFoundError as e:
        print('Exception occurred: %s' % e)
        return
    
    ds.process_profile()
    ds.discover_posts()
    ds.read_post_data()
    ds.download_images()
    ds.download_videos()
    # generate_indices(ds.get_userdata())
    
    return ds.get_userdata()
    
def show_users_pickle(username):
    user = load_user_data('%s_data.pickle' % username)
    print(user['name'])
    print(user['activity'])

def save_user_data(data, filename):
    with open(filename, 'wb') as f:
        pickle.dump(data, f)
    
def load_user_data(filename):
    data = ''
    if not os.path.exists(filename):
        return None
    with open(filename, 'rb') as f:
        data = pickle.load(f)
    return data
    
def most_recent_day(activity):
    """ Searches an activity for the most recent day. Returns a (yyyy, ddd) tuple """
    max_year = max(activity.years.keys())
    max_day = max(activity.years[max_year].days.keys())
    
    return (max_year, max_day)
    
def search_for_new_comments(activity):
    """ Searches all stored data links for new comments 
          adds any new comments to activity """
    # TODO
    return
    
def update_data(username, activity):
    """ Updates the user data from the most recent available day """
    
    # get most recent day
    day = most_recent_day(activity)
    # update_all_from( that date )
    data = update_all_from(username, activity, day[0], day[1])
    # notify operation is complete
    print('loaded data has been updated')
    # prompt user to save the data
    print('type "save" to write changes to disc')
    
    return data
    
def update_all_from(username, activity, year, day):
    """ Replaces the existing given day with the latest version """
    
    print('updating date of "%s" from %d day # %d' % (username, year, day))
    
    print('Initiating spider')
    # obtain URL of day (if exists -- else... just take all from most recent month)
    try:
        ds = blog_spider(username)
    except UserNotFoundError as e:
        print('Exception occurred: %s' % e)
        return
    
    ds.process_profile()
    
    date = get_date(year, day)
    # discover posts from the year and month
    ds.discover_posts(update_from={'year':year,'month':date.month})
    
    # filter list of days to include only those from days including and after the given day
    data_day = get_day(activity, year, day)
    if not data_day:
        print('error finding day to update from')
        return  # TODO just start from the beginning
    recent_url = data_day.link
    print('recent url: %s' % recent_url)
    
    new_list = list()
    existing_url_list 
    for url in ds.day_urls:
        print('testing against: %s' % url)
        new_list.append(url)
        # if url == recent_url:
            # break
    
    # begin updating from there as normal
    ds.read_post_data(urls=new_list)
    ds.download_images()
    
    return ds.get_userdata()
    
def get_date(year, day):
    """ given YYYY and DDD of that year, returns a datetime.date object """
    year_start = datetime.date(year, 1, 1).toordinal()
    day_ordinal = year_start + day
    return datetime.date.fromordinal(day_ordinal)
    
def get_day(activity, year, day):
    """ Prints the selected day's text to the CLI """
    if year not in activity.years:
      print('year %d not found' % year)
      return
    y = activity.years[year]
    if day not in y.days:
      print('day %d not found' % day)
      return
    
    return y.days[day]
    
def print_day(day):
    assert type(day) == activity.Day
    
    print( 'Title: %s' % day.title )
    # print( 'Date: %s' % datetime.strftime(day.date) )
    print( 'Date: %s' % day.date )
    print( 'Link: %s' % day.link )
    print( '%d Likes %d posts %d comments\n' % (day.likes, len(day.posts), len(day.comments)) )
    
    for post in day.posts:
        print ( post.text )
        
def print_comments(day):
    assert type(day) == activity.Day
    
    print("Comments for day %d" % day.day_num)
    for comment in day.comments:
        print ( 'By: @%s\n%s\n' % (comment.username, '\n'.join(textwrap.wrap(comment.text, 80)) ) )
        
def get_json(data):
    data_json = json.loads(BlogJSONEncoder().encode(data))
    data_json['activity'] = json.loads(BlogJSONEncoder().encode(data['activity'].all_days()))
    
    return data_json
    
class BlogJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if "__dict__" in dir(o):
            return o.__dict__
        return o.__str__()
    
class d2pcli(cmd.Cmd):
    def __init__(self):
        cmd.Cmd.__init__(self)
        self.data = ''
        self.username = ''
        self.selectedday = ''
        self.use_s3 = True
        
    def check_user(self):
        if self.username == '':
            print('No user set')
            return False
        return True

    def check_data(self):
        if self.data == '':
            print('no data')
            return False
        return True
        
    def do_autoget(self, line):
        """ auto_get -- Finds and pulls all blog data for currently set username, saving images and dumping a data file """
        if not self.check_user(): return
        self.data = get_data(self.username, self.use_s3)
        
    def do_set(self, username):
        """ set -- Selects the given user """
        self.username = username
        print('set user to: %s' % self.username)
        
    def do_login(self, line):
        """ logs in as the given user """
        username, password = line.split(" ")
        pulldata.set_login(username, password)
        
    def do_uses3(self, line):
        """ toggles using and not using S3 as export location """
        self.use_s3 = not self.use_s3
        print("use_s3: {}".format(self.use_s3))
        
    def do_load(self, line):
        """ load -- Reads the selected user's data file if it exists. Replaces any open user files """
        if not self.check_user(): return
        filename = '%s_data.pickle' % self.username
        if not os.path.exists(filename):
            print('file "%s" not found' % filename)
            return
        self.data = load_user_data(filename)
        print ('load complete')
        
    def do_save(self, line):
        """ Saves the currently loaded user's data to file. """
        if not self.check_user(): return
        if not self.check_data(): return
        filename = '%s_data.pickle' % self.username
        save_user_data(self.data, filename)
        print ('save complete')
        
    def do_summary(self, line):
        """ Prints a summary of user """
        if not self.check_user(): return
        if not self.check_data(): return
        d = self.data
        print('Name: %s\nURL: %s\nBio: %s\n%s ' % (d['name'], d['url'], d['bio'], d['activity']))
    
    def do_makeindex(self, line):
        """ Generates html files for years and months """
        
        if not self.check_user(): return
        if not self.check_data(): return
        
        # generate_indices(self.data)
    
    def do_fixjson(self, line):
        ''' converts the links of an exported json to use an s3 bucket and folder structure '''
        if not self.check_user(): return

        name_in = '{}_data.json'.format(self.username)
        name_out = 'fixed_{}_data.json'.format(self.username)
        
        # check json for the current user exists
        if os.path.exists(name_in):
            with open(name_in, 'r') as f:
                jsondata = json.loads(f.read())
        else:
            print("user json hasn't been created (try command 'json' first)")
            return
        
        p = PostLinkFixer(bucket_name, jsondata)
        p.fix_links()
        p.dump_json(name_out)
        
        print("exported fixed json to {}".format(name_out))
    
    def do_update(self, line):
        """ Updates the stored data with recent posts """
        if not self.check_user(): return
        if not self.check_data(): return
        print("Coming soon..")
        return
        
        
        data = update_data(self.data['username'], self.data['activity'])
        
        # merge activities..
        new_days = data['activity'].all_days()
        self.data['activity'].merge_new_days(new_days)
        
        # TODO
        """ This function can be used with periodic saving to tmp while pulling data to avoid errors ruining an autoget() download """
        # print("Coming soon..")
        
    def do_lastday(self, line):
        """ Prints the most recent day in stored data """
        if not self.check_user(): return
        if not self.check_data(): return
        day=most_recent_day(self.data['activity'])
        print("%d day #%d" % (day[0], day[1]))
        
    def do_getday(self, day):
        """ Accepts "YYYY DDD" index of a day, prints that day's data and holds """
        
        result = re.search(r'(\d{4}) (\d{1,3})', day)
        if result is None:
            print('invalid format. use "YYYY DDD"')
            return
        year = int(result.group(1))
        day = int(result.group(2))
        
        self.selectedday = get_day(self.data['activity'], year, day)
        print('selected -- %s' % self.selectedday)
        
        return
        
    def do_printday(self, line):
        if self.selectedday == '':
            print('no day selected')
        else:
            print_day(self.selectedday)
        return
        
    def do_printcomments(self, line):
        if self.selectedday == '':
            print('no day selected')
        else:
            print_comments(self.selectedday)
        return
        
    def do_xml(self, line):
        if not self.check_user(): return
        if not self.check_data(): return
        
        data_json = get_json( self.data )
        xml = dicttoxml.dicttoxml(data_json, attr_type=False)
        
        with open('%s_data.xml' % self.data['username'], 'w') as f:
            f.write(xml)
        
        print('saved as xml file')
    
    def do_fixall(self, line):
        """ fixes all json file in directory """
        
        onlyfiles = [f for f in listdir(".") if isfile(join(".", f))]
        
        for file in onlyfiles:
            if '_data.json' in file and 'fixed' not in file:
                username = file.replace("_data.json","")
                print("running fixjson on {}".format(username))
                self.do_set(username)
                self.do_fixjson(None)
    
    def do_summaryall(self, line):
        """ prints all summaries for files in current directory """
    
        onlyfiles = [f for f in listdir(".") if isfile(join(".", f))]
        
        for file in onlyfiles:
            if '_data.pickle' in file and 'fixed' not in file:
                username = file.replace("_data.pickle","")
                print("\nrunning summary on {}".format(username))
                self.do_set(username)
                self.do_load(None)
                self.do_summary(None)
    
    def do_json(self, line):
        """ export user data as a json file """
        if not self.check_user(): return
        if not self.check_data(): return
        
        data_json = get_json( self.data )
        
        with open('{}_data.json'.format(self.data['username']), 'w') as f:
            f.write(json.dumps(data_json, indent=4))
        print('saved as json file')
        return
        
    def do_tex(self, line):
        """ Exports the selected data to a tex file """
        if not self.check_user(): return
        if not self.check_data(): return
        print('Experimental..!')
        data2tex(self.data, '%s_out' % self.data['username'])
        return
        
    def do_EOF(self, line):  # C-d exits
        print('exiting..')
        return True
    

if __name__ == "__main__":
    # main()
    d2pcli().cmdloop()
