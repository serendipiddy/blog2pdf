import argparse, sys
import pulldata
import activity
import parse_dayre
from discover import *
import pickle


def get_args():
    parser = argparse.ArgumentParser(description='Tool for creating a PDF from a user\'s Dayre data.')
    parser.add_argument('username', help='Username of user')
    parser.add_argument('-d', '--dump', action='store_true', help='Include to simply dump all user day and image data as HTML')
    
    return parser.parse_args()

def main():
    # parse args, get user name
    parser = get_args()
    print('User: %s' % parser.username)
    
    if parser.dump:
        show_users_pickle(parser.username)
        sys.exit(0)
        
    get_data(parser.username)
    
def get_data(username):
    print('Initiating spider')
    try:
        # create dayre_puller
        ds = dayre_spider(username)
    except UserNotFoundError as e:
        print('Exception occurred:' % e)
    
    
    ds.process_profile()
    if u'http://cdnjs.cloudflare.com/ajax/libs/twemoji/1.4.1/36x36/1f1ef-1f1f4.png' in ds.image_urls:
        print('found img')
    ds.discover_posts()
    ds.read_post_data()
    ds.download_images()
    
    user = ds.get_userdata()
    
    filename = '%s_test.pickle' % username
    save_user_data(user, filename)
    show_users_pickle(username)
    
def show_users_pickle(username):
    user = load_user_data('%s_test.pickle' % username)
    print(user['name'])
    print(user['activity'])

def save_user_data(data, filename):
    with open(filename, 'w') as f:
        pickle.dump(data, f)
    
def load_user_data(filename):
    data = ''
    with open(filename, 'rb') as f:
        data = pickle.load(f)
    return data
    
if __name__ == "__main__":
    main()
    
    