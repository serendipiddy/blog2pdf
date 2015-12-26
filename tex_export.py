""" Processes the selected data and creates a Tex file representation """

from pylatex import Document, Section, Subsection, Command, Figure, Package
from pylatex.utils import italic, NoEscape

import post


image_dir = 'images2/'

def data2tex(userdata, filename):
    """ Entrypoint. Converts saved user data to tex """
    
    doc = Document("basic")
    doc.packages.append(Package('float'))
    export_user(doc, userdata)
    export_activity(doc, userdata)
    doc.generate_tex('basic_maketitle')
    
    tex = doc.dumps()  # dump as string
    
def export_user(doc, userdata):
    
    doc.preamble.append(Command('title', userdata['name']))
    doc.preamble.append(Command('author', userdata['url']))
    doc.append(NoEscape(r'\clearpage'))
    doc.append(NoEscape(r'\maketitle'))
    
    return 
    
    
def export_activity(doc, userdata):
    with doc.create(Section('Activity', numbering=False)):
        for day in userdata['activity'].all_days():
            export_day(doc, day)
    return
    
def export_post(doc, _post):
    # doc.append(post)
    if type(_post) == post.Post:
        doc.append(_post.text)
    if type(_post) == post.Quote:
        doc.append(NoEscape(r'\begin{quote}'))
        doc.append(_post.text)
        doc.append(NoEscape(r'\end{quote}'))
    if type(_post) == post.Image: 
        with doc.create(Figure(position='H')) as image:
                image.add_image('%s%s' % (image_dir, _post.link), width='240px')
                if not _post.location == None:
                    image.add_caption(_post.location)
        doc.append(_post.text)
    if type(_post) == post.Sticker:
        with doc.create(Figure(position='H')) as image:
                image.add_image('%s%s' % (image_dir, _post.link), width='240px')
        doc.append(_post.text)
    if type(_post) == post.Location:
        doc.append(NoEscape(r'\begin{quote}'))
        doc.append(_post.name)
        doc.append(_post.address)
        doc.append(NoEscape(r'\end{quote}'))
        doc.append(_post.text)
    if type(_post) == post.YouTube_video:
        doc.append(NoEscape(r'\begin{quote}'))
        doc.append(_post.url)
        doc.append(NoEscape(r'\end{quote}'))
        doc.append(_post.text)
    if type(_post) == post.User_video:
        doc.append(NoEscape(r'\begin{quote}'))
        with doc.create(Figure(position='H')) as image:
                image.add_image('%s%s' % (image_dir, _post.preview_link), width='240px')
        doc.append(NoEscape(r'\end{quote}'))
        doc.append(_post.text)
    return
    
def export_day(doc, day):
    with doc.create(Subsection('Day %d - %s'  % (day.day_num ,day.title), numbering=False )):
        for p in day.posts:
            export_post(doc, p)
    # doc.append(day)
    return
    
def export_emoji(doc, emoji):
    
    return