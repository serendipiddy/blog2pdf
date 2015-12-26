""" Processes the selected data and creates an XML file representation for importing into Adobe InDesign """

from lxml import etree

def data2xml(userdata, filename):
    """ Entrypoint. Converts saved user data to xml, ready for importing into Adobe InDesign """
    
    user_xml = etree.Element("userdata")
    profile
    user_to_xml(user_xml, userdata)
    activity_to_xml(user_xml, userdata)
    
    
def user_to_xml(userdata):
    
    return 
    
    
def activity_to_xml(userdata):
    return
    
def post_to_xml(post):
    return
    
    
def day_to_xml(day):
    return
    
    
def emoji_to_xml_link(unicode):
    return
    