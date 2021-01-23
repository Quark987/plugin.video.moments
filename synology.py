import requests
from urllib import urlencode, quote
import xbmc

class SynologyMoments(object):

    def __init__(self):
        self.session = requests.session()


    def login(self, username, password, nas_name, nas_port, browse_shared_lib):
        self.username = username
        self.password = password
        self.nas_name = nas_name
        self.nas_port = nas_port
        self.browse_shared_lib = (browse_shared_lib == 'true')

        data = {'OTPcode':'', 'logintype':'local', 'passwd':password, 'rememberme':1, 'timezone':'+01:00', 'username':username, 'enable_device_token':'no'}
        url = 'http://{}:{}/webman/login.cgi?enable_syno_token=yes'.format(nas_name, nas_port)
        response = self.session.post(url, data=data, verify=False)

        if 'success' in response.json() and response.json()['success'] == True:
            self.cookies = response.cookies
            self.syno_token = response.json()['SynoToken']
            self.headers = {'Connection':'keep-alive', 'X-SYNO-TOKEN' : self.syno_token}

            if self.browse_shared_lib and self.shared_library_populated():
                self.api = 'SYNO.PhotoTeam'
                return 'success'
            elif self.browse_shared_lib and not self.shared_library_populated():
                self.api = 'SYNO.Photo'
                return 'Shared library empty'
            else:            
                self.api = 'SYNO.Photo'
                return 'success'

        return 'Failed to log in'


    def kodi_header(self):
        header = ''             # This is to transmit the cookie in Kodi format
        for element in self.cookies.get_dict():
            header += element + '=' + self.session.cookies[element] + ';'
        header = header[:-1]    # Drop trailing semicolon

        return '|'+'Cookie='+quote(header)+'&'+urlencode(self.session.headers)      # also add the standard headers


    def shared_library_populated(self):
        url = 'http://{}:{}/webapi/entry.cgi'.format(self.nas_name, self.nas_port)
        data = {'api':'SYNO.PhotoTeam.Browse.Timeline', 'method':'get', 'version':1}

        try:
            photos = self.session.post(url, data=data, verify=False, cookies=self.cookies, headers=self.headers).json()
            if len(photos['data']['list']) > 0:
                return True
        except:
            return False
        
        return False


    def get_categories(self):
        url = 'http://{}:{}/webapi/entry.cgi'.format(self.nas_name, self.nas_port)
        data = {'api':self.api+'.Browse.Category', 'method':'get', 'version':1}

        categories = self.session.post(url, data=data, verify=False, cookies=self.cookies, headers=self.headers).json() # list the albums
        
        temp = ['album']
        for element in categories['data']['list']:
            temp.append(element['id'])

        temp.append('search')
        return temp


    def get_albums(self, category, keyword=None):
        url = 'http://{}:{}/webapi/entry.cgi'.format(self.nas_name, self.nas_port)

        # video and recently_added are immediately forwarded to get_photos as there are no subalbums
        params = {'api':self.api+'.Thumbnail', 'type':'"unit"', 'size':'sm', 'method':'get','version':1, 'SynoToken':self.syno_token}
        if category == 'shared_with_others':    # Depending on the category, a different request is send
            data = {'api':self.api+'.Browse.Album', 'method':'list', 'version':2, 'limit':500, 'shared':'true', 
                'offset':'0', 'sort_by':'start_time', 'sort_direction':'desc', 'additional':'["thumbnail"]'}
        elif category == 'shared_with_me':
            data = {'api':self.api+'.Sharing', 'method':'list_shared_with_me', 'version':1, 'limit':500, 'offset':0, 
                'additional':'["thumbnail", "sharing_info"]'}
        elif category =='person':
            data = {'api':self.api+'.Browse.Person', 'method':'list', 'version':2, 'limit':500, 'offset':0, 
                'additional':'["thumbnail"]', 'show_hidden':'false'}
            params = {'api':self.api+'.Thumbnail', 'type':'"person"', 'method':'get','version':1, 'SynoToken':self.syno_token}
        elif category == 'concept':
            data = {'api':self.api+'.Browse.Concept', 'method':'list', 'version':1, 'limit':500, 'offset':0, 
                'additional':'["thumbnail"]'}
        elif category == 'geocoding':
            data = {'api':self.api+'.Browse.Geocoding', 'method':'list', 'version':2, 'limit':500, 'offset':0, 
                'additional':'["thumbnail"]'}
        elif category == 'general_tag':
            data = {'api':self.api+'.Browse.GeneralTag', 'method':'list', 'version':1, 'limit':500, 'offset':0, 
                'additional':'["thumbnail"]'}
        elif category == 'search':
            data = {'api':self.api+'.Search', 'method':'list_album', 'version':3, 'limit':500, 'offset':0, 
                'additional':'["thumbnail"]', 'keyword': keyword}
        else:       # List personal albums, is not a synology category
            data = {'api':self.api+'.Browse.Album', 'method':'list', 'version':2, 'limit':500, \
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

                if 'passphrase' in albums['data']['list'][k].keys():                    # Required for shared_with_me albums
                    params['passphrase'] = albums['data']['list'][k]['passphrase']

                albums['data']['list'][k]['url'] = url + '?' + urlencode(params) + kodi_header
            else:
                albums['data']['list'][k]['url'] = ''
        
        return albums['data']['list']


    def get_photos(self, list_id, keyword=None, passphrase=None):
        url = 'http://{}:{}/webapi/entry.cgi'.format(self.nas_name, self.nas_port)

        if list_id == 'recently_added':
            data = {'api':self.api+'.Browse.RecentlyAdded', 'method':'list', 'version':3, 'limit':5000, 'offset':0, 
                    'additional':'["thumbnail","resolution","orientation","video_convert","video_meta"]'}
        elif list_id == 'video':
            data = {'api':self.api+'.Browse.Item', 'method':'list', 'version':3, 'limit':5000, 'offset':0, 'type':'video', 
                'additional':'["thumbnail","resolution","orientation","video_convert","video_meta"]', 'sort_by':'start_time'}
        elif list_id == 'search':
            data = {'api':self.api+'.Search', 'method':'list_item', 'version':3, 'limit':5000, 'offset':0, 'keyword':keyword, 
                'additional':'["thumbnail","resolution","orientation","video_convert","video_meta"]', 'sort_by':'start_time'}
        elif passphrase is not None:    # shared_with_me photos
            data = {'api':self.api+'.Browse.Item', 'method':'list', 'version':3, 'limit':5000, 'passphrase':passphrase,
                'offset':0, 'additional':'["thumbnail","resolution","orientation","video_convert","video_meta"]'}
        else:
            data = {'api':self.api+'.Browse.Item', 'method':'list', 'version':3, 'limit':5000, 
                    'offset':0, 'additional':'["thumbnail","resolution","orientation","video_convert","video_meta"]'}

            id_key, id_value = list_id.split('=')
            if id_key.startswith('search') or id_key.startswith('shared'):
                id_key = 'album_id'

            data[id_key] = id_value # Add the proper id (geocoding_id, person_id, album_id, ...)

        photos = self.session.post(url, data=data, verify=False, cookies=self.cookies, headers=self.headers).json() # list the photos (and videos)

        params = {'api':self.api+'.Thumbnail', 'type':'"unit"', 'size':'sm', 'method':'get','version':1, 'SynoToken':self.syno_token}

        if passphrase is not None:
            params['passphrase'] = passphrase

        kodi_header = self.kodi_header()

        for k in range(len(photos['data']['list'])):
            params['id'] = str(photos['data']['list'][k]['additional']['thumbnail']['unit_id'])
            params['cache_key'] = str(photos['data']['list'][k]['additional']['thumbnail']['cache_key'])
            photos['data']['list'][k]['url'] = url + '?' + urlencode(params) + kodi_header

        return photos['data']['list']
    

    def get_photo_url(self, list_id, photo_id, photo_cache_key, passphrase=None):
        kodi_header = self.kodi_header()

        params = {'api':self.api+'.Thumbnail', 'method':'get', 'version':1, 'SynoToken':self.syno_token, \
                'size':'xl', 'cache_key':photo_cache_key, 'id':photo_id, 'type':'unit'}
        
        if passphrase is not None:
            params['passphrase'] = passphrase

        base_url = "http://{}:{}/webapi/entry.cgi.jpg?".format(self.nas_name, self.nas_port)

        return base_url + urlencode(params) + kodi_header


    def get_video_url(self, video_id, quality):
        kodi_header = self.kodi_header()

        params = {'type':'item', 'quality':'\"'+quality+'\"','use_mov':'true', 'api':self.api+'.Streaming',
            'method':'streaming', 'version':'1', 'SynoToken':self.syno_token, 'id':video_id}
        base_url = "http://{}:{}/webapi/entry.cgi?".format(self.nas_name, self.nas_port)

        return base_url + urlencode(params) + kodi_header
