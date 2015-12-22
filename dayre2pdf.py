import argparse, sys
import pulldata
import activity
import parse_dayre
from discover import *


def get_args():
    parser = argparse.ArgumentParser(description='Tool for creating a PDF from a user\'s Dayre data.')
    parser.add_argument('username', help='Username of user')
    parser.add_argument('-d', '--dump', action='store_true', help='Include to simply dump all user day and image data as HTML')
    
    return parser.parse_args()

def main():
    # parse args, get user name
    parser = get_args()
    print('User: %s' % parser.username)
    
    # if parser.dump: 
        # # get users data and save it to fs (can take a while.. do it under restrictions.. may get blocked..)
        # if not pulldata.get_user_posts(parser.username):
            # print('error..exiting')
            # sys.exit(0)
        # else:
            # print('dump successful')
    
    print('Initiating spider')
    try:
        # create dayre_puller
        ds = dayre_spider(parser.username)
    except UserNotFoundError as e:
        print('Exception occurred:' % e)
    
    
    ds.process_profile()
    ds.discover_posts()
    ds.read_post_data()
    ds.download_images()
    
    user = ds.get_userdata()
    print(user['name'])
    print(user['activity'])
    
    # allow a user to select the 

if __name__ == "__main__":
    main()
    
    