from ebooklib import epub

class EBookMaker:
    
    def __init__(self, userjson):
        
        self.book = epub.EpubBook()
        self.chapters = []

        # set metadata
        book.set_identifier('id123456')
        book.set_title('{} Dayre'.format(username))
        book.set_language('en')

        book.add_author(userjson['name'])
        # book.add_author('Danko Bananko', file_as='Gospodin Danko Bananko', role='ill', uid='coauthor')



    def day_to_xml(self, day):
        ''' returns an xml representation of the given day '''
        


    def post_to_xml(self, post):
        ''' returns an xml representation of the given post '''
        


    def image_to_xml(self, post):
        ''' returns an xml representation of the given image '''
        


    def location_to_xml(self, location):
        ''' returns an xml representation of the given image '''
        

    def create_book(self, output_name):
        ''' returns an xml representation of the given image '''
        
        
        style = self.get_style()
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)

        # create chapter
        c1 = epub.EpubHtml(title='Intro', file_name='intro.xhtml', lang='en')
        c1.content=u'<h1>Intro heading</h1><p>Zaba je skocila u baru.</p>'
        
        c2 = epub.EpubHtml(title='Second Intro', file_name='chap_02.xhtml')
        c2.content=u'<h1>Second intro heading</h1><p>Baru yang molly.</p>'
        
        c3 = epub.EpubHtml(title='Second Intro', file_name='chap_02.2.xhtml')
        c3.content=u'<h2>About her</h2><p>Butterfly hunter molly.</p>'

        # add chapter
        book.add_item(c1)
        book.add_item(c2)
        book.add_item(c3)

        # define Table Of Contents
        book.toc = (
            epub.Link('chap_01.xhtml', 'Introduction', 'intro'),
            (epub.Section('Simple book'),
                (c1, )),
            (epub.Section('Simple book 2'),
                (c2, c3))
        )

        # add default NCX and Nav file
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())


        # add CSS file
        book.add_item(nav_css)

        # basic spine
        book.spine = ['nav', c1, c2]

        # write to the file
        epub.write_epub('test.epub', book, {})


    def get_style(self):
        return '''
@namespace epub "http://www.idpf.org/2007/ops";
body {
    font-family: Cambria, Liberation Serif, Bitstream Vera Serif, Georgia, Times, Times New Roman, serif;
}
h2 {
     text-align: left;
     text-transform: uppercase;
     font-weight: 200;     
}
ol {
        list-style-type: none;
}
ol > li:first-child {
        margin-top: 0.3em;
}
nav[epub|type~='toc'] > ol > li > ol  {
    list-style-type:square;
}
nav[epub|type~='toc'] > ol > li > ol > li {
        margin-top: 0.3em;
}
'''