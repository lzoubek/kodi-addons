#!/usr/bin/python
# coding: utf-8

"""Wrapper pro Drtinová Veselovský TV
"""

import httplib
import json
from urlparse import urlparse
import os.path
import HTMLParser
import re
import urllib
import xml.etree.ElementTree as ET
import email.utils as eut
import time

__author__ = "Štěpán Ort"
__license__ = "MIT"
__version__ = "1.0.0"
__email__ = "stepanort@gmail.com"



class Video():
    def __init__(self, title, image, qualities):
        self.title = title
        self.image = image
        self.qualities = qualities

class Programme():
    
    def __init__(self, link, title=None, description=None, image=None, date=None):
        self.link = link
        self._description = description
        if title and image:
            self._title = title
            self._image = image
            self._date = date
        else:
            page = _fetch_dvtv(self.link)
            self._parse_video_page(page)
    
    def title(self):
        if not self._title:
            page = _fetch_dvtv(self.link)
            self._parse_video_page(page)
        return self._title
    
    def description(self):
        if not self._description:
            page = _fetch_dvtv(self.link)
            self._parse_video_page(page)
        return self._description
      
    def date(self):
        return self._date
    
    def image(self):
        if not self._image:
            page = _fetch_dvtv(self.link)
            self._parse_video_page(page)
        return self._image
    
    def playlist(self):
        if not self._playlist:
            page = _fetch_dvtv(self.link)
            self._parse_video_page(page)  
        return self._playlist
 
    def _parse_video_page(self, data):
        videos = re.compile('{[^i]*?image.*?sources:[^]]*?][^}]*?}', re.S).findall(data)
        keywords_re = re.compile('<a.*href=".*?\/l~i:keyword:([0-9]*)\/".*?>([^<]*)<').findall(data)
        for keyword_re in keywords_re:
            keyword_id = int(keyword_re[0])
            keyword_name = _toString(keyword_re[1])
            keyword_check(keyword_name, keyword_id)
            
        if videos:
            self._playlist = []
            for video in videos:
                image = 'http:' + re.compile('image: ?\'([^\']*?)\'').search(video).group(1).strip()
                title = _unescape(re.compile('title: ?\'([^\']*?)\'').search(video).group(1)).strip() 
                sources = re.compile('sources: ?(\[[^\]]*?])', re.S).search(video).group(1)
                if sources:
                    versions = re.compile('{[^}]*?}', re.S).findall(sources)
                    if versions:
                        qualities = []
                        for version in versions:
                            url = re.compile('file: ?\'([^\']*?)\'').search(version).group(1).strip()
                            mime = re.compile('type: ?\'([^\']*?)\'').search(version).group(1).strip()
                            quality = re.compile('label: ?\'([^\']*?)\'').search(version).group(1).strip()
                            qualities.append(Quality(url, mime, quality))
                self._playlist.append(Video(title=title, image=image, qualities=qualities))
                            
        
def _unescape(text):
    out = _toString(text)
    out = out.replace('&iacute;', _toString('í'))
    out = out.replace('&aacute;', _toString('á'))
    out = out.replace('&scaron;', _toString('š'))
    out = out.replace('&eacute;', _toString('ě'))
    out = out.replace('&yacute;', _toString('ý'))
    out = out.replace('&quot;', _toString('"'))
    out = out.replace('&lt;', _toString('<'))
    out = out.replace('&gt;', _toString('>'))
    out = out.replace('&amp;', _toString('&'))
    out = _toString(out)
    try:
        out = HTMLParser().unescape(out)
    except:
        pass
    return out

class Quality():
    def __init__(self, url, mime, quality):
        self.url = url
        self.mime = mime
        self.quality = quality

class Keyword():
    def __init__(self, keyword_id, name=None):
        self.name = name
        self.keyword_id = keyword_id
        
    def list(self, offset=None):
        return _listProgrammes(offset=None, keyword_id=self.keyword_id)

    

def _toString(text):
    if type(text).__name__=='unicode':
        output = text.encode('utf-8')
    else:
        output = str(text)
    return output

def _upload_new_keyword(name, keyword_id):
    conn = httplib.HTTPSConnection('script.google.com')
    req_data = urllib.urlencode({ 'name' : name, 'id' : keyword_id})
    headers = {"Content-type": "application/x-www-form-urlencoded"}
    conn.request(method='POST', url='/macros/s/AKfycbzUtiQOZVJ9Kr3gyvtEFDCuFBCxwu5dGo8D3ivRumLocAoMVRg/exec', body=req_data, headers=headers)
    resp = conn.getresponse()
    while resp.status >= 300 and resp.status < 400:
        location = resp.getheader('Location')
        o = urlparse(location ,allow_fragments=True)
        host = o.netloc
        conn = httplib.HTTPSConnection(host)
        url = o.path + "?" + o.query
        conn.request(method='GET', url=url)
        resp = conn.getresponse()
    if resp.status >= 200 and resp.status < 300:
        resp_body = resp.read()
        json_body = json.loads(resp_body)
        status = json_body['status']
        if status == 'ok':
            _update_keywords_cache()
        elif status == 'already contains this id':
            _update_keywords_cache()
    
def keyword_check(name, keyword_id):
    keywords = _fetch_keywords()
    if keywords:
        for item in keywords:
            if item['id'] == keyword_id:
                return
    _upload_new_keyword(name, keyword_id)

addon_userdata_path = None;
def _update_keywords_cache():
    conn = httplib.HTTPSConnection('script.google.com')
    conn.request('GET', '/macros/s/AKfycbzUtiQOZVJ9Kr3gyvtEFDCuFBCxwu5dGo8D3ivRumLocAoMVRg/exec')
    resp = conn.getresponse()
    while resp.status >= 300 and resp.status < 400:
        location = resp.getheader('Location')
        o = urlparse(location ,allow_fragments=True)
        host = o.netloc
        conn = httplib.HTTPSConnection(host)
        url = o.path + "?" + o.query
        conn.request('GET', url)
        resp = conn.getresponse()
    data = resp.read()
    keyword_file = open(os.path.join(addon_userdata_path, 'keywords.json'), 'w')
    keyword_file.write(data)
    keyword_file.close()
    return data

def _fetch_keywords():
    json_data = None
    try:
        data = None
        if os.path.isfile(os.path.join(addon_userdata_path, 'keywords.json')):
            data = open(os.path.join(addon_userdata_path, 'keywords.json'), 'r').read()
        json_data = json.loads(data)
    except:
        try:
            data = _update_keywords_cache()
            json_data = json.loads(data)
        except: 
            return None
    return json_data

def _fetch_dvtv(url):
    u = urlparse(url, allow_fragments=True)
    host = u.netloc
    path = u.path 
    if u.query:
        path += "?" + u.query
    conn = httplib.HTTPConnection(host)
    headers = { "User-Agent" : "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3" }
    conn.request("GET", url=path, headers=headers)
    resp = conn.getresponse()
    while resp.status >= 300 and resp.status < 400:
        location = resp.getheader("Location")
        u = urlparse(location, allow_fragments=True)
        host = u.netloc
        path = u.path 
        if u.query:
            path += "?" + u.query
        conn = httplib.HTTPConnection(host)
        conn.request("GET", url=path, headers=headers)
        resp = conn.getresponse()
    return resp.read()

def _listProgrammes(offset=None, keyword_id=None):
    url = "http://video.aktualne.cz/rss/"
    if keyword_id:
        url += "l~i:keyword:" + _toString(keyword_id) + "/"
    if offset:
        url += "?offset=" + _toString(offset)
    rss = _fetch_dvtv(url)
    root = ET.fromstring(rss)
    programmes = []
    for item in root.find('channel').findall('item'):
        link  = item.find('link').text
        title = item.find('title').text
        description = item.find('description').text
        contentEncoded = item.find('{http://purl.org/rss/1.0/modules/content/}encoded').text
        datetime = eut.parsedate(item.find('pubDate').text)
        date = time.strftime('%d.%m.%Y', datetime)
        image = re.compile('<img.+?src="([^"]*?)"').search(contentEncoded).group(1)
        programmes.append(Programme(link=link, title=title, description=description, image=image, date=date))
    return programmes

def list_recommended():
    programmes = []
    url = "http://video.aktualne.cz/"
    page = _fetch_dvtv(url)
    video_of_the_day_block = re.compile('<h2>video dne</h2>.*?(<a.*?</a>)', re.S).search(page).group(1)
    root = ET.fromstring(video_of_the_day_block)
    link = "http://video.aktualne.cz" + root.get("href")
    title = root.find("em").text
    image = "http:" + root.find("img").get("src")
    programmes.append(Programme(link=link, title=title, image=image))
    recommended_block = re.compile('id="qa-doporucujeme".*?(<ul.*?</ul>)', re.S).search(page).group(1)
    root = ET.fromstring(recommended_block)
    for li in root.findall("li"):
        link = "http://video.aktualne.cz" + li.find("a").get("href")
        title = li.find("a/em").text
        image = "http:" + li.find("a/img").get("src")
        image = image.replace("_r3:2_w232_h154_", "_r16:9_w480_h270_")
        programmes.append(Programme(link=link, title=title, image=image))
    return programmes

def list_latest(offset=None):
    return _listProgrammes(offset)

_keywords = None
def keywords():
    global _keywords
    if _keywords:
        return _keywords
    json_data = _fetch_keywords()
    if len(json_data) > 0:
        _keywords = []
        for item in json_data:
            name =_toString(item['name'])
            keyword_id = item['id']
            _keywords.append(Keyword(keyword_id, name))
    return _keywords

