""" Processes the selected data and creates a Tex file representation """

from pylatex import Document, Section, Subsection, Command, Figure, Package
from pylatex.utils import italic, NoEscape, bold

import post
from datetime import datetime


image_dir = 'images2/'
image_width = '200px'

def data2tex(userdata, filename):
    """ Entrypoint. Converts saved user data to tex """
    
    doc = Document(documentclass=Command('documentclass',arguments='article',options='10pt,a4paper,twocolumn'))
    doc.packages.append(Package('float'))
    doc.packages.append(Package('parskip', options=['parfill']))
    export_user(doc, userdata)
    export_activity(doc, userdata)
    doc.generate_tex(filename)
    
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
            export_day(doc, day, userdata['username'])
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
                image.add_image('%s%s' % (image_dir, _post.link), width=image_width)
                if not _post.location == None:
                    image.add_caption(_post.location)
        doc.append(_post.text)
    if type(_post) == post.Sticker:
        with doc.create(Figure(position='H')) as image:
                image.add_image('%s%s' % (image_dir, _post.link), width=image_width)
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
                image.add_image('%s%s' % (image_dir, _post.preview_link), width=image_width)
        doc.append(NoEscape(r'\end{quote}'))
        doc.append(_post.text)
    return
    
def export_day(doc, day, username):
    if day.title == '':
        daytitle = 'Day %d'  % (day.day_num)
    else:
        daytitle = 'Day %d - %s'  % (day.day_num, day.title)
    
    with doc.create(Subsection(daytitle, numbering=False )):
        doc.append(bold( day.date.strftime('%A, %d %b %Y') ))
        for p in day.posts:
            export_post(doc, p)
    # doc.append(day)
    return
    
def export_emoji(doc, emoji):
    
    return