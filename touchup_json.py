from urllib.parse import urlparse
import json
 
'''
Post types | Has Link | prefix
-----------|----------|-----
* Text     |    F     |
* Quote    |    F     |
* Location |    F     |
* Image    |    T     | http://<bucket_name>/<username>/images/
* Sticker  |    T     | http://<bucket_name>/<username>/images/
* Youtube  |    F     |
* user     |    T     | http://<bucket_name>/<username>/videos/

'''

class PostLinkFixer:
    blog_domain = 'dayre.me'

    def __init__(self, bucket_name, data):
        self.bucket_name = bucket_name
        self.data = data
        
        self.user_prefix = 'http://{}/{}'.format(self.bucket_name, self.data['name'])
        self.image_prefix = '{}/images'.format(self.user_prefix)
        self.video_prefix = '{}/videos'.format(self.user_prefix)


    def fix_links(self):
        """ starts the link fixing """

        # fix the links in each day's post
        for day in self.data['activity']:
            # change day link?
            for post in day['posts']:
                if 'link' in post:
                    # append with bucket name, username [and folder]
                    if post['post_type'] in ['Image','Sticker']:
                        self.fix_image_link(post)
                    elif post['post_type'] == 'User_video':
                        self.fix_video_link(post)
                    
                    for comment in post['comments']:
                        self.fix_avatar_link(comment)
        
        # change the follow{er|ing} avatar urls but keep the link to their profile the same
        for follower in self.data['followers']:
            self.fix_avatar_link(follower)
        for follower in self.data['followering']:
            self.fix_avatar_link(follower)
        
        # fix the user's profile avatar link
        self.fix_avatar_link(self.data)

    def dump_json(self, filename):
        """ saves the current json to disk """

        with open(filename, "w") as f:
            f.write(json.dumps(self.data))


    def fix_avatar_link(self, item):
        """ fix the link to a days page """
        item['avatar_link'] = '{}/{}'.format(self.image_prefix, item['avatar_link'])


    def fix_image_link(self, post):
        """ fix the link for a image """
        post['link'] = '{}/{}'.format(self.image_prefix, post['link'])


    def fix_video_link(self):
        """ fix the link for a video """
        post['link'] = '{}/{}'.format(self.video_prefix, post['link'])


if __name__ == "__main__":
    # name of json as arg
    # name of bucket from arg
    fixer = PostLinkFixer(bucket_name)
    fixer.load_json(filename)
    fixer.fix_links()
    fixer.dump_json(output_name)

