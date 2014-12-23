# coding: utf-8
import os
import sys
import httplib
from urlparse import urlparse
import traceback
import json
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib
import re
import time
import dvtv
from datetime import datetime

params = None
try:
    ###############################################################################
    REMOTE_DBG = False
    # append pydev remote debugger
    if REMOTE_DBG:
        try:
            sys.path.append(os.environ['HOME']+r'/.xbmc/system/python/Lib/pysrc')
            import pydevd
            pydevd.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True)
        except ImportError:
            sys.stderr.write("Error: Could not load pysrc!")
            sys.exit(1)
    ###############################################################################
    _addon_ = xbmcaddon.Addon('plugin.video.dvtv')
    # First run
    if not (_addon_.getSetting("settings_init_done") == "true"):
        DEFAULT_SETTING_VALUES = { "send_errors" : "false", 
                                   "quality": "720p",
                                   "format": "MP4" }
        for setting in DEFAULT_SETTING_VALUES.keys():
            val = _addon_.getSetting(setting)
            if not val:
                _addon_.setSetting(setting, DEFAULT_SETTING_VALUES[setting])
        _addon_.setSetting("settings_init_done", "true")
    ###############################################################################
    _profile_ = xbmc.translatePath(_addon_.getAddonInfo('profile'))
    setattr(dvtv, 'addon_userdata_path', _profile_) 
    _lang_   = _addon_.getLocalizedString
    _scriptname_ = _addon_.getAddonInfo('name')
    _quality_ = _addon_.getSetting('quality')
    _first_error_ = (_addon_.getSetting('first_error') == "true")
    _send_errors_ = (_addon_.getSetting('send_errors') == "true")
    _format_ = 'video/' + _addon_.getSetting('format').lower()
    _icon_ = xbmc.translatePath( os.path.join(_addon_.getAddonInfo('path'), 'icon.png' ) )
    _next_ = xbmc.translatePath( os.path.join(_addon_.getAddonInfo('path'), 'resources/media/next.png' ) )
    _previous_ = xbmc.translatePath( os.path.join(_addon_.getAddonInfo('path'), 'resources/media/previous.png' ) )
    _handle_ = int(sys.argv[1])
    _baseurl_ = sys.argv[0]
    ###############################################################################
    def log(msg, level=xbmc.LOGDEBUG):
        if type(msg).__name__=='unicode':
            msg = msg.encode('utf-8')
        xbmc.log("[%s] %s"%(_scriptname_,msg.__str__()), level)
    
    def logDbg(msg):
        log(msg,level=xbmc.LOGDEBUG)
    
    def logErr(msg):
        log(msg,level=xbmc.LOGERROR)
    ###############################################################################
    
    def mainMenu():
        addDirectoryItem(_lang_(30051), _baseurl_+ "?menu=" + urllib.quote_plus("recommended"))
        addDirectoryItem(_lang_(30052), _baseurl_+ "?menu=" + urllib.quote_plus("latest"))
        addDirectoryItem(_lang_(30106), _baseurl_+ "?keyword=" + urllib.quote_plus(_toString(109800)))
        addDirectoryItem(_lang_(30101), _baseurl_+ "?keyword=" + urllib.quote_plus(_toString(109)))
        addDirectoryItem(_lang_(30102), _baseurl_+ "?keyword=" + urllib.quote_plus(_toString(2464)))
        addDirectoryItem(_lang_(30103), _baseurl_+ "?keyword=" + urllib.quote_plus(_toString(18)))
        addDirectoryItem(_lang_(30104), _baseurl_+ "?keyword=" + urllib.quote_plus(_toString(13)))
        addDirectoryItem(_lang_(30105), _baseurl_+ "?keyword=" + urllib.quote_plus(_toString(349)))
        addDirectoryItem(_lang_(30053), _baseurl_+ "?menu=" + urllib.quote_plus("keywords"))
        xbmcplugin.endOfDirectory(_handle_, updateListing=False)
    
    def listItems(offset, keyword=None):
        next_url = _baseurl_ + "?menu=" + urllib.quote_plus("latest") + "&offset=" + _toString(offset+30)
        previous_url = _baseurl_ + "?menu=" + urllib.quote_plus("latest") + "&offset=" + _toString(offset-30)
        if keyword:
            previous_url += "&keyword=" + _toString(keyword)
            next_url += "&keyword=" + _toString(keyword)
        if offset > 0:
            addDirectoryItem('[B]<< ' + _lang_(30007) + '[/B]',  previous_url, image=_previous_)
        if keyword:
            _list(dvtv.Keyword(keyword).list(offset))
        else:
            _list(dvtv.list_latest(offset))
        addDirectoryItem('[B]' +_lang_(30006) +' >> [/B]',  next_url, image=_next_)
        xbmcplugin.endOfDirectory(_handle_, updateListing=(offset>0), cacheToDisc=False)
            
    def _getQualityName(title, mime, quality):
        return re.compile("video/(.*)").search(mime).group(1).upper() + ": " + quality
    
    def playProgramme(link, skipAutoQuality=False):
        programme = dvtv.Programme(link)
        pl=xbmc.PlayList(1)
        pl.clear()
        for video in programme.playlist():
            if len(programme.playlist()) > 0 and skipAutoQuality:
                addDirectoryItem(video.title, None, isFolder=False)
            li = xbmcgui.ListItem(video.title)
            li.setThumbnailImage(video.image)
            for quality in video.qualities:
                if skipAutoQuality:
                    quality_name = _getQualityName(video.title, quality.mime, quality.quality)
                    addDirectoryItem(label=quality_name, url=quality.url, title=video.title, image=video.image, isFolder=False)
                else:
                    if (quality.quality == _quality_ and quality.mime == _format_):
                        xbmc.PlayList(1).add(quality.url, li)
        if skipAutoQuality:
            xbmcplugin.endOfDirectory(_handle_, updateListing=False,cacheToDisc=False)
        else:
            xbmc.Player().play(pl)
    
    def _list(programmeList):
        xbmcplugin.setContent(_handle_, 'episodes')
        for programme in programmeList:
            addDirectoryItem(programme.title(), _baseurl_+ "?play=" + urllib.quote_plus(programme.link), programme.description(), programme.title(), programme.date(), image=programme.image(), isFolder=False)
    
    def addDirectoryItem(label, url, plot=None, title=None, date=None, icon=_icon_, image=None, fanart=None, isFolder=True):
        li = xbmcgui.ListItem(label)
        if not title:
            title = label
        liVideo = {'title': title}
        if plot:
            liVideo['plot'] = plot
        if date:
            dt = datetime.fromtimestamp(time.mktime(time.strptime(date, "%d.%m.%Y")))
            liVideo['premiered'] = dt.strftime("%Y-%m-%d")
        if image:
            li.setThumbnailImage(image)
        li.setIconImage(icon)
        li.setInfo("video", liVideo)
        if not isFolder and url:
            cm = []
            cm.append((_lang_(30013), "XBMC.Container.Update(" + url + "&skip_auto=1)"))
            li.addContextMenuItems(cm)
        xbmcplugin.addDirectoryItem(handle=_handle_, url=url, listitem=li, isFolder=isFolder)
    
    def listRecommended():
        _list(dvtv.list_recommended())
        xbmcplugin.endOfDirectory(_handle_, updateListing=False, cacheToDisc=False)
    
    def listKeywords():
        for keyword in dvtv.keywords():
            addDirectoryItem(keyword.name, _baseurl_+ "?keyword=" + urllib.quote_plus(_toString(keyword.keyword_id)))
        xbmcplugin.endOfDirectory(_handle_, updateListing=False,cacheToDisc=False)
    
    
    def _toString(text):
        if type(text).__name__=='unicode':
            output = text.encode('utf-8')
        else:
            output = str(text)
        return output
    
    def _sendError(params, exc_type, exc_value, exc_traceback):
        try:
            conn = httplib.HTTPSConnection('script.google.com')
            req_data = urllib.urlencode({ 'addon' : _scriptname_, 'params' : _toString(params), 'type' : exc_type, 'value' : exc_value, 'traceback' : _toString(traceback.format_exception(exc_type, exc_value, exc_traceback))})
            headers = {"Content-type": "application/x-www-form-urlencoded"}
            conn.request(method='POST', url='/macros/s/AKfycbyZfKhi7A_6QurtOhcan9t1W0Tug-F63_CBUwtfkBkZbR2ysFvt/exec', body=req_data, headers=headers)
            resp = conn.getresponse()
            while resp.status >= 300 and resp.status < 400:
                location = resp.getheader('Location')
                o = urlparse(location, allow_fragments=True)
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
                    return True
        except:
            pass
        return False
    
    def get_params():
            param=[]
            paramstring=sys.argv[2]
            if len(paramstring)>=2:
                    params=sys.argv[2]
                    cleanedparams=params.replace('?','')
                    if (params[len(params)-1]=='/'):
                            params=params[0:len(params)-2]
                    pairsofparams=cleanedparams.split('&')
                    param={}
                    for i in range(len(pairsofparams)):
                            splitparams={}
                            splitparams=pairsofparams[i].split('=')
                            if (len(splitparams))==2:
                                    param[splitparams[0]]=splitparams[1]
            return param             
    def assign_params(params):
        for param in params:
            try:
                globals()[param]=urllib.unquote_plus(params[param])
            except:
                pass
    
    play=None
    keyword=None
    menu=None
    offset=0
    skip_auto=None
    params=get_params()
    assign_params(params)


    if play:
        skip_auto = (skip_auto is not None and skip_auto != "0")
        playProgramme(play, skip_auto)
    elif menu or keyword:
        if menu == "recommended":
            listRecommended()
        elif menu == "keywords":
            listKeywords()
        else:
            listItems(int(offset), keyword)
    else:
        mainMenu()
except Exception as ex:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    xbmcgui.Dialog().notification(_scriptname_, _toString(exc_value), xbmcgui.NOTIFICATION_ERROR)
    if not _first_error_:
        if xbmcgui.Dialog().yesno(_scriptname_, _lang_(30500), _lang_(30501)):
            _addon_.setSetting("send_errors", "true")
            _send_errors_ = (_addon_.getSetting('send_errors') == "true")
        _addon_.setSetting("first_error", "true")
        _first_error_ = (_addon_.getSetting('first_error') == "true")
    if _send_errors_:
        if _sendError(params, exc_type, exc_value, exc_traceback):
            xbmcgui.Dialog().notification(_scriptname_, _lang_(30502), xbmcgui.NOTIFICATION_INFO)
        else:
            xbmcgui.Dialog().notification(_scriptname_, _lang_(30503), xbmcgui.NOTIFICATION_ERROR)