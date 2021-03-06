#! ~/Envs/oac/bin/jython

import base64
import urllib
import urllib2
post_url = "http://daxdev.services.brown.edu:8081/oac_web_service/create"
params = {  'oax_style_uri'         : u'info:fedora/test:1000010118',
            'body_inline'           : u'some inline body text',
            'oa_selector_type_uri'  : u'oa:FragmentSelector',
            'generator'             : u'OAC TEI Demo web application',
            'dc_title'              : u'Florence',
            'source_uri'            : u'info:fedora/changeme:35',
            'oa_selector'           : u'/TEI[1]/text[1]/body[1]/div1[1]/div2[1]/p[2]/name[1]',
            'annotator'             : u'aashton@brown.edu',
            'fragment_type'         : u'http://dbpedia.org/resource/XPath'}

encoded_data = urllib.urlencode( params )
request = urllib2.Request( post_url, encoded_data )
# Authenticate with OAC credentials (defined in the OAC configuration file)
username = ""
password = ""
base64_auth_string = base64.encodestring( '%s:%s' % (username, password) )[:-1]
request.add_header( "Authorization", "Basic %s" % base64_auth_string )
response = urllib2.urlopen( request )
print response.read()

