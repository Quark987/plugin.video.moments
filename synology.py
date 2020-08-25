import requests
from urllib import urlencode, quote
import xbmc

class SynologyMoments(object):

    def __init__(self):
        self.session = requests.session()


    def login(self, username, password, nas_name, nas_port):
        self.username = username
        self.password = password
        self.nas_name = nas_name
        self.nas_port = nas_port

        data = {'OTPcode':'', 'logintype':'local', 'passwd':password, 'rememberme':1, 'timezone':'+01:00', 'username':username, 'enable_device_token':'no'}
        url = 'http://{}:{}/webman/login.cgi?enable_syno_token=yes'.format(nas_name, nas_port)
        response = self.session.post(url, data=data, verify=False)

        if 'success' in response.json() and response.json()['success'] == True:
            self.cookies = response.cookies
            self.syno_token = response.json()['SynoToken']
            self.headers = {'Connection':'keep-alive', 'X-SYNO-TOKEN' : self.syno_token}

            return 'success'
        return 'failed'


    def kodi_header(self):
        header = ''             # This is to transmit the cookie in Kodi format
        for element in self.cookies.get_dict():
            header += element + '=' + self.session.cookies[element] + ';'
        header = header[:-1]    # Drop trailing semicolon

        return '|'+'Cookie='+quote(header)+'&'+urlencode(self.session.headers)      # also add the standard headers


    def get_categories(self):
        url = 'http://{}:{}/webapi/entry.cgi'.format(self.nas_name, self.nas_port)
        data = {'api':'SYNO.Photo.Browse.Category', 'method':'get', 'version':1}

        categories = self.session.post(url, data=data, verify=False, cookies=self.cookies, headers=self.headers).json() # list the albums
        temp = ['album']
        for element in categories['data']['list']:
            temp.append(element['id'])

        temp.append('search')
        return temp


    def get_albums(self, category, keyword=None):
        url = 'http://{}:{}/webapi/entry.cgi'.format(self.nas_name, self.nas_port)

        # video and recently_added are immediately forwarded to get_photos as there are no subalbums
        params = {'api':'SYNO.Photo.Thumbnail', 'type':'"unit"', 'size':'sm', 'method':'get','version':1, 'SynoToken':self.syno_token}
        if category == 'shared':    # Depending on the category, a different request is send
            data = {'api':'SYNO.Photo.Browse.Album', 'method':'list', 'version':2, 'limit':500, 'shared':'true', \
                'offset':'0', 'sort_by':'start_time', 'sort_direction':'desc', 'additional':'["thumbnail"]'}    # Shared with me
            
            # data = {'api':'SYNO.Photo.Sharing', 'method':'22list_shared_with_me', 'version':1, 'limit':500, 'offset':0, \
            #     'additional':'["thumbnail", "22sharing_info"]'}       # Shared with others
        elif category =='person':
            data = {'api':'SYNO.Photo.Browse.Person', 'method':'list', 'version':2, 'limit':500, 'offset':0, 
                'additional':'["thumbnail"]', 'show_hidden':'false'}
            params = {'api':'SYNO.Photo.Thumbnail', 'type':'"person"', 'method':'get','version':1, 'SynoToken':self.syno_token}
        elif category == 'concept':
            data = {'api':'SYNO.Photo.Browse.Concept', 'method':'list', 'version':1, 'limit':500, 'offset':0, 
                'additional':'["thumbnail"]'}
        elif category == 'geocoding':
            data = {'api':'SYNO.Photo.Browse.Geocoding', 'method':'list', 'version':2, 'limit':500, 'offset':0, 
                'additional':'["thumbnail"]'}
        elif category == 'general_tag':
            data = {'api':'SYNO.Photo.Browse.GeneralTag', 'method':'list', 'version':1, 'limit':500, 'offset':0, 
                'additional':'["thumbnail"]'}
        elif category == 'search':
            data = {'api':'SYNO.Photo.Search', 'method':'list_album', 'version':3, 'limit':500, 'offset':0, 
                'additional':'["thumbnail"]', 'keyword': keyword}
        else:       # List personal albums, is not a synology category
            data = {'api':'SYNO.Photo.Browse.Album', 'method':'list', 'version':2, 'limit':500, \
                'offset':'0', 'sort_by':'start_time', 'sort_direction':'desc', 'additional':'["thumbnail"]'}

        albums = self.session.post(url, data=data, verify=False, cookies=self.cookies, headers=self.headers).json() # list the albums
        kodi_header = self.kodi_header()

        for k in range(len(albums['data']['list'])):
            if albums['data']['list'][k]['item_count'] > 0:
                if category == 'person':
                    params['id'] = str(albums['data']['list'][k]['id'])
                else:
                    params['id'] = str(albums['data']['list'][k]['additional']['thumbnail']['unit_id'])
                params['cache_key'] = str(albums['data']['list'][k]['additional']['thumbnail']['cache_key'])
                albums['data']['list'][k]['url'] = url + '?' + urlencode(params) + kodi_header
            else:
                albums['data']['list'][k]['url'] = ''
        
        return albums['data']['list']


    def get_photos(self, list_id, keyword=None):
        url = 'http://{}:{}/webapi/entry.cgi'.format(self.nas_name, self.nas_port)

        if list_id == 'recently_added':
            data = {'api':'SYNO.Photo.Browse.RecentlyAdded', 'method':'list', 'version':3, 'limit':5000, 'offset':0, 
                    'additional':'["thumbnail","resolution","orientation","video_convert","video_meta"]'}
        elif list_id == 'video':
            data = {'api':'SYNO.Photo.Browse.Item', 'method':'list', 'version':3, 'limit':5000, 'offset':0, 'type':'video', 
                'additional':'["thumbnail","resolution","orientation","video_convert","video_meta"]', 'sort_by':'start_time'}
        elif list_id == 'search':
            data = {'api':'SYNO.Photo.Search', 'method':'list_item', 'version':3, 'limit':5000, 'offset':0, 'keyword':keyword, 
                'additional':'["thumbnail","resolution","orientation","video_convert","video_meta"]', 'sort_by':'start_time'}
        else:
            data = {'api':'SYNO.Photo.Browse.Item', 'method':'list', 'version':3, 'limit':5000, \
                'offset':0, 'additional':'["thumbnail","resolution","orientation","video_convert","video_meta"]'}

            id_key, id_value = list_id.split('=')
            if id_key == 'search_id':
                id_key = 'album_id'

            data[id_key] = id_value # Add the proper id (geocoding_id, person_id, album_id, ...)

        photos = self.session.post(url, data=data, verify=False, cookies=self.cookies, headers=self.headers).json() # list the photos (and videos)
        base_url = "http://{}:{}/webapi/entry.cgi?".format(self.nas_name, self.nas_port)
        params = {'api':'SYNO.Photo.Thumbnail', 'type':'"unit"', 'size':'sm', 'method':'get','version':1, 'SynoToken':self.syno_token}

        kodi_header = self.kodi_header()

        for k in range(len(photos['data']['list'])):
            params['id'] = str(photos['data']['list'][k]['additional']['thumbnail']['unit_id'])
            params['cache_key'] = str(photos['data']['list'][k]['additional']['thumbnail']['cache_key'])
            photos['data']['list'][k]['url'] = base_url + urlencode(params) + kodi_header

        return photos['data']['list']
    

    def get_photo_url(self, photo_id, photo_cache_key):
        kodi_header = self.kodi_header()

        params = {'api':'SYNO.Photo.Thumbnail', 'method':'get', 'version':1, 'SynoToken':self.syno_token, \
                'size':'xl', 'cache_key':photo_cache_key, 'id':photo_id, 'type':'unit'}
        base_url = "http://{}:{}/webapi/entry.cgi?".format(self.nas_name, self.nas_port)

        return base_url + urlencode(params) + kodi_header


    def get_video_url(self, video_id, quality):
        kodi_header = self.kodi_header()

        params = {'type':'item', 'quality':'\"'+quality+'\"','use_mov':'true', 'api':'SYNO.Photo.Streaming',
            'method':'streaming', 'version':'1', 'SynoToken':self.syno_token, 'id':video_id}
        base_url = "http://{}:{}/webapi/entry.cgi?".format(self.nas_name, self.nas_port)

        return base_url + urlencode(params) + kodi_header
