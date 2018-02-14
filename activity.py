from post import Post, Comment
from datetime import datetime
import re
import sys
from copy import deepcopy


# regex for weekdays: http://stackoverflow.com/a/21709043
date_regex = re.compile(r'(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day, \d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}')
date_format = '%A, %d %b %Y'  # Monday, 01 Dec 2014 ## DAY OF MONTH MUST BE ZERO PADDED the read HTML's aren't
month_labels = ('Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec')

class Activity(object):
    """ Holds the posts of a user: their blogging activity """
    def __init__(self):
        self.years = dict()
        self.hashtags = dict()  # '#tag' -> set() of days featuring it
        self.usertags = dict()  # '@user' -> set() of days featuring it
        
        # populate years, 2013..current
        this_year = datetime.utcnow().year
        for y in range(2013, this_year+1):
            self.years[y] = Year(y)
        
    def __str__(self):
        days = 0
        posts = 0
        for y in self.years:
            days += len(self.years[y].days)
            for d in self.years[y].days:
                posts += len(self.years[y].days[d].posts)
        return 'Activity: %d days %d posts %d hashtags %d usertags' % (days, posts, len(self.hashtags), len(self.usertags))
        
    def __repr__(self):
        return self.__str__()
    
    def all_days(self):
        """ Returns a sorted list of all the days of activity """
        days = list()
        for y in sorted(self.years.keys()):
            for d in sorted(self.years[y].days.keys()):
                days.append(self.years[y].days[d])
        return days
    
    def add_post(self, day, post):
        """ Add a post to the given day """
        assert type(day) == Day
        assert issubclass(type(post), Post)
        
        # create __day__ to year if it doesn't exist
        if day.day_num not in self.years[day.date.year].days:
            self.years[day.date.year].add_day(day)
            
        # place __post__ in day
        self.years[day.date.year].days[day.day_num].add_post(post)
        
        # audit tags
        for tag in post.hashtags:
            if tag not in self.hashtags:
                self.hashtags[tag] = list()
            self.hashtags[tag].append(day)
            
        for tag in post.usertags:
            if tag not in self.usertags:
                self.usertags[tag] = list()
            self.usertags[tag].append(day)
        
    def add_comment(self, day, comment):
        assert type(day) == Day
        assert type(comment) == Comment
        
        # create __day__ to year if it doesn't exist
        if day.day_num not in self.years[day.date.year].days:
            self.years[day.date.year].add_day(day)
            
        # place __post__ in day
        self.years[day.date.year].days[day.day_num].add_comment(comment)

        # audit tags
        for tag in comment.usertags:
            if tag not in self.usertags:
                self.usertags[tag] = list()
            self.usertags[tag].append(day)
        
    def get_day(self, year, day_num):
        """ Retrieve the given day """
        assert type(day_num) == int
        assert type(year) == int
        assert day_num > 0 and day_num <= 366
        assert year >= 2013 and year <= 9999
        
        if day_num in self.years[year].days:
            return self.years[year].days[day_num]
        else:
            return None
        
    def get_days(self, yd):
        """ Retrieves a sorted list of Day objects present given a sequence of (year, day) tuples """
        days = list()
        
        for y,d in yd:
            rv = self.get_day(y,d)
            if rv is not None:
                days.append(rv)
        
        return sorted(days, key=lambda d: '%d %03d' % (d.date.year, d.day_num))
        
    def get_day_range(self, year_from, day_from, year_to, day_to):
        """ Retrieves a sequence of days between numbers from and to (inclusive)"""
        assert type(day_from) == int and type(day_to) == int
        assert type(year_from) == int and type(year_to) == int
        assert year_to >= year_from
        assert day_from >= 1 and day_from <= 366
        assert year_to >= 2013 and year_to <= 9999
        assert year_from >= 2013 and year_from <= 9999
        
        days = list()
        for y in range(year_from, year_to+1):
            if y not in self.years:
                return days
            for d in range(day_from, day_to+1):
                rv = self.get_day(y,d)
                if rv is not None:
                    days.append(rv)
        return days

    def merge_new_days(self, days):
        """ Adds the list of days to this activity, replacing any days that exist already """
        
        for day in days:
            exists = self.get_day(day.date.year, day.day_num)
            if exists:
                # TODO.. not sure how to do this..
                # delete it ## can't simply delete.. tags etc
                # del self.years[day.date.year].days[day_num]
                continue
                
            for post in day.posts:
                self.add_post(deepcopy(day), post)
            for comment in day.comments:
                self.add_comment(deepcopy(day), comment)
    
class Year(object):
    """ Holds a years activity information """
    
    def __init__(self, year):
        assert type(year) is int
        assert year >= 1 and year <= 9999
        self.year = year
        
        self.days = dict()  # for referencing
        # self.days_list = list()  # for ordered iteration
        self.months = dict()
        for m in month_labels:
            self.months[m] = list()  # set of days in each month
        self.active = False
        
    def __str__(self):
        return 'year: %d, %03d days' % (self.year, len(self.days))
        
    def __repr__(self):
        return self.__str__()
        
    def has_activity(self):
        """ Returns whether there are any posts made in this year """
        return self.active
        
    def is_leap_year(self, year):  # somewhat redundant..
        """ Return whether the given year is a leap year """
        # leap year calculation: https://support.microsoft.com/en-us/kb/214019
        assert type(year) == int
        if year % 4 is 0:
            if year % 100 is 0:
                # not leap if divisible by 100 and not 400
                return year % 400 is 0  
            else:
                return True
        else:
            return False
            
    def add_day(self, day):
        """ Adds the pre-constructed day to this year """
        assert type(day) == Day
        if day.day_num not in self.days:
            self.days[day.day_num] = day
            
            if not self.active:
                self.active = True
            
            # add to months
            date = datetime.strptime('%03d%d' % (day.day_num, self.year),'%j%Y')
            m = month_labels[date.month-1]
            # custom contains using ANY: http://stackoverflow.com/a/9898639
            if not any(day_num_equals(day, li) for li in self.months[m]):
                self.months[m].append(day)
            else:
                print ("day %d already exists" % day.day_num)
        else:
            print('day %d already existing in year.days' % day.day_num)
            
    def get_month(self, month):
        """ Retrieve the ordered list of day object in the given month """
        assert type(month) == str or type(month) == int
        if type(month) == str:
            assert month in month_labels
        else:  # is int
            assert month <= 12 and month >= 1
            month = month_labels[month-1]
        # sorting functions with key lambda function
        return sorted(list(self.months[month]), key=lambda d: d.day_num)

def check_day_parameters(title, day_num, likes, date, link):
    """ Checks parameters for creating a day """
    assert type(title) is str or type(date) is unicode         # : print('invalid title')
    assert type(day_num) is int        # : print('invalid day number')
    assert type(likes) is int          # : print('invalid likes number')
    assert type(link) is str or type(date) is unicode          # : print('invalid link')
    assert type(date) is str or type(date) is unicode          # : print('invalid date type')
    assert date_regex.match(date) is not None  # : print('invalid date format: %s' % date)
    
def day_num_equals(day1, day2):
    """ Compares if two day numbers are the same """
    return day2.day_num == day1.day_num and day2.date.year == day1.date.year
    
class Day(object):
    """ Holds the information for a day's entries """
    
    def __init__(self, title, day_num, likes, date, link):
        check_day_parameters(title, day_num, likes, date, link)
        self.title = title
        self.day_num = day_num
        self.likes = likes
        self.date = datetime.strptime(date, date_format).date()
        self.link = link
        
        self.posts = list()
        self.comments = list()
        self.hashtags = dict()  # #tag  -> set posts featuring it
        self.usertags = dict()  # @user -> set posts featuring it
    
    def __str__(self):
        return "%d Day %d, %d posts, %d comments '%s'" % (self.date.year, self.day_num, len(self.posts), len(self.comments), self.title)
        
    def __repr__(self):
        return self.__str__()
        
    def add_post(self, post):
        """ Add a post  to this day """
        assert issubclass(type(post), Post)
        
        # audit post, extracting hashtags and usertags
        for tag in post.hashtags:
            if tag not in self.hashtags:
                self.hashtags[tag] = list()
            self.hashtags[tag].append(post)
            
        for tag in post.usertags:
            if tag not in self.usertags:
                self.usertags[tag] = list()
            self.usertags[tag].append(post)
        
        self.posts.append(post)
        
    def add_comment(self, comment):
        """ Add a post  to this day """
        assert type(comment) is Comment
        
        # audit post, extracting usertags
        for tag in comment.usertags:
            if tag not in self.usertags:
                self.usertags[tag] = list()
            self.usertags[tag].append(comment)
        
        self.posts.append(comment)
    
    def add_comment(self, comment):
        assert type(comment) == Comment
        
        for tag in comment.usertags:
            if tag not in self.usertags:
                self.usertags[tag] = list()
            self.usertags[tag].append(comment)
        
        self.comments.append(comment)

