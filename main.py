# -*- coding: utf-8 -*-
# Module: default
# Author: Roman V. M.
# Created on: 28.11.2014
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import sys
import os
from urllib import urlencode, quote
from urlparse import parse_qsl
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
from synology import SynologyMoments

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])
addon = xbmcaddon.Addon('plugin.video.moments')
moments = SynologyMoments()

category_titles = {'person':'People', 'shared':'Shared', 'concept':'Subjects', 'geocoding':'Places', 'recently_added':'Recently added',
            'general_tag':'Tags', 'album':'Personal albums', 'video':'Videos', 'search':'Search'}

def get_url(**kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param kwargs: "argument=value" pairs
    :type kwargs: dict
    :return: plugin call URL
    :rtype: str
    """
    return '{0}?{1}'.format(_url, urlencode(kwargs))


def list_categories():
    xbmcplugin.setPluginCategory(_handle, 'My Album Collection')
    xbmcplugin.setContent(_handle, 'images')
    categories = moments.get_categories()

    for category in categories:
        list_item = xbmcgui.ListItem(label=category_titles[category])

        addon_dir = xbmc.translatePath( addon.getAddonInfo('path') )
        art_url = os.path.join(addon_dir, 'resources', 'icon_'+category+'.png')
        
        list_item.setArt({'thumb': art_url,
                          'icon': art_url,
                          'fanart': art_url})

        url = get_url(action='show_category', category=category)
        is_folder = True
        xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)
    xbmcplugin.endOfDirectory(_handle)


def list_albums(category, keyword=None):
    xbmcplugin.setPluginCategory(_handle, category)
    xbmcplugin.setContent(_handle, 'videos')
    albums = moments.get_albums(category, keyword)
    
    for k in range(len(albums)):
        list_item = xbmcgui.ListItem(label=albums[k]['name'])

        list_item.setArt({'thumb': albums[k]['url'],
                          'icon': albums[k]['url'],
                          'fanart': albums[k]['url']})
                          
        list_item.setInfo('video', {'title': albums[k]['name'],
                                    'mediatype': 'video'})

        try:
            passphrase = albums[k]['passphrase']
        except:
            passphrase = ''

        url = get_url(action='show_album', list_id=urlencode({category+'_id':albums[k]['id']}), passphrase=passphrase)
        is_folder = True
        xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)

    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    # xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def list_photos(list_id, keyword=None, passphrase=None):        # Keyword for searches, passphrase for shared_with_me albums
    xbmcplugin.setPluginCategory(_handle, list_id)
    xbmcplugin.setContent(_handle, 'images')
    photos = moments.get_photos(list_id, keyword, passphrase)

    for k in range(len(photos)):
        list_item = xbmcgui.ListItem(label=photos[k]['filename'])

        list_item.setArt({'thumb': photos[k]['url'],
                          'icon': photos[k]['url'],
                          'fanart': photos[k]['url']})

        if photos[k]['type'] == 'video':
            list_item.setProperty('IsPlayable', 'true')
            list_item.setInfo('video', {'title': photos[k]['filename'],
                                    'mediatype': 'video'})

            try:
                quality = photos[k]['additional']['video_convert'][0]['quality']
            except:
                quality = 'medium'
            
            video_id = str(photos[k]['additional']['thumbnail']['unit_id'])

            url = moments.get_video_url(video_id, quality)
        else:
            list_item.setInfo('pictures', {'title':photos[k]['filename']})

            photo_cache_key = photos[k]['additional']['thumbnail']['cache_key']
            photo_id = str(photos[k]['additional']['thumbnail']['unit_id'])

            url = moments.get_photo_url(photo_id, photo_cache_key)

            list_item.setMimeType('image/'+photos[k]['filename'].split('.')[-1])    # Predefine the mime type, otherwise it takes ages
            
        is_folder = False
        xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    # xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def list_shared():
    xbmcplugin.setPluginCategory(_handle, 'Shared')
    xbmcplugin.setContent(_handle, 'images')

    list_item = xbmcgui.ListItem(label='Shared with others')
    url = get_url(action='shared_with_others')
    is_folder = True
    xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)

    list_item = xbmcgui.ListItem(label='Shared with me')
    url = get_url(action='shared_with_me')
    is_folder = True
    xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)

    xbmcplugin.endOfDirectory(_handle)


def list_search_results(keyword):
    xbmcplugin.setPluginCategory(_handle, 'Search')
    xbmcplugin.setContent(_handle, 'images')

    list_item = xbmcgui.ListItem(label='Albums')
    url = get_url(action='search_albums', keyword=keyword)
    is_folder = True
    xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)

    list_item = xbmcgui.ListItem(label='Items')
    url = get_url(action='search_items', keyword=keyword)
    is_folder = True
    xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)

    xbmcplugin.endOfDirectory(_handle)


def list_search_albums(keyword):
    return list_albums('search', keyword)


def list_search_items(keyword):
    return list_photos('search', keyword)


def get_user_input():   
    kb = xbmc.Keyboard()
    kb.doModal()            # Onscreen keyboard appears
    if not kb.isConfirmed():
        return
    query = kb.getText()    # User input
    return query

def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring

    :param paramstring: URL encoded plugin paramstring
    :type paramstring: str
    """
    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))
    if params and 'action' in params.keys():        # Check the parameters passed to the plugin
        if params['action'] == 'show_category':
            if (params['category'] == 'recently_added') or (params['category'] == 'video'):
                list_photos(params['category'])     # There are no albums in recently added or video
            elif params['category'] == 'search':
                keyword = get_user_input()
                if keyword is not None and len(keyword)>0:
                    list_search_results(keyword)
            elif params['category'] == 'shared':
                list_shared()
            else:
                list_albums(params['category'])     # List albums within each category
        elif params['action'] == 'search_albums':
            list_search_albums(params['keyword'])
        elif params['action'] == 'search_items':
            list_search_items(params['keyword'])
        elif params['action'] == 'show_album':
            if 'passphrase' in params.keys():
                list_photos(params['list_id'], passphrase=params['passphrase'])
            else:
                list_photos(params['list_id'])
        elif params['action'] == 'shared_with_others':
            list_albums('shared_with_others')
        elif params['action'] == 'shared_with_me':
            list_albums('shared_with_me')
        else:
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        list_categories()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    addon = xbmcaddon.Addon()

    response = moments.login(addon.getSetting('username'),
                            addon.getSetting('password'),
                            addon.getSetting('host'),
                            addon.getSetting('port'))
    if response == 'success':
        router(sys.argv[2][1:])
    else:
        xbmcgui.Dialog().ok('Synology Moments', 'Failed to log in')