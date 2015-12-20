import argparse, sys
import pulldata

def get_args():
    parser = argparse.ArgumentParser(description='Tool for creating a PDF from a user\'s Dayre data.')
    parser.add_argument('username', help='Username of user')
    
    return parser.parse_args()

def main():
    # parse args, get user name
    parser = get_args()
    print(parser.username)
    
    # get users data and save it to fs (can take a while.. do it under restrictions.. may get blocked..)
    if not pulldata.get_user_posts(parser.username):
        print('..exiting')
        sys.exit(0)
    
    # build data structures and objects from the user data
    # allow a user to select the 
    

if __name__ == "__main__":
    main()