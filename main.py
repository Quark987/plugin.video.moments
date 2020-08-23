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
            'general_tag':'Tags', 'album':'Personal albums', 'video':'Videos'}

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
    xbmcplugin.setContent(_handle, 'videos')
    categories = moments.get_categories()

    for category in categories:
        list_item = xbmcgui.ListItem(label=category_titles[category])

        addon_dir = xbmc.translatePath( addon.getAddonInfo('path') )
        art_url = os.path.join(addon_dir, 'resources', 'icon_'+category+'.png')
        xbmc.log(art_url)
        list_item.setArt({'thumb': art_url,
                          'icon': art_url,
                          'fanart': art_url})

        url = get_url(action='show_category', category=category)
        is_folder = True
        xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)
    xbmcplugin.endOfDirectory(_handle)


def list_albums(category):
    """
    Create the list of video categories in the Kodi interface.
    """
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_handle, category)
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_handle, 'videos')
    # Get video categories
    albums = moments.get_albums(category)
    # Iterate through categories
    for k in range(len(albums)):
        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=albums[k]['name'])

        list_item.setArt({'thumb': albums[k]['url'],
                          'icon': albums[k]['url'],
                          'fanart': albums[k]['url']})
                          
        list_item.setInfo('video', {'title': albums[k]['name'],
                                    'mediatype': 'video'})

        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=listing&category=Animals
        url = get_url(action='show_album', list_id=urlencode({category+'_id':albums[k]['id']}))
        # is_folder = True means that this item opens a sub-list of lower level items.
        is_folder = True
        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    # xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def list_photos(list_id):
    """
    Create the list of playable videos in the Kodi interface.

    :param category: Category name
    :type category: str
    """
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_handle, list_id)
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_handle, 'videos')
    # Get the list of videos in the category.
    photos = moments.get_photos(list_id)

    # Iterate through videos.
    for k in range(len(photos)):
        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=photos[k]['filename'])

        list_item.setArt({'thumb': photos[k]['url'],
                          'icon': photos[k]['url'],
                          'fanart': photos[k]['url']})

        # Setup url for both videos and photos
        if 'video_convert' in photos[k]['additional'].keys():       # If it's a video
            list_item.setProperty('IsPlayable', 'true')             # Set 'IsPlayable' property to 'true'.
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
            
            # url = moments.get_photo_url(photo_id, photo_cache_key)
            url = get_url(action='play', content_id=photo_id+'/'+photo_cache_key)
            
        # Add the list item to a virtual Kodi folder.
        # is_folder = False means that this item won't open any sub-list.
        is_folder = False
        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    # xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def play_content(photo_ids):
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    ids = photo_ids.split('/')
    photo_id = ids[0]
    photo_cache_key = ids[1]

    url = moments.get_photo_url(photo_id, photo_cache_key)

    xbmc.executebuiltin('ShowPicture("{0}")'.format(url))


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
            else:
                list_albums(params['category'])     # List albums within each category
        elif params['action'] == 'show_album':
            list_photos(params['list_id'])          # Display the list of videos in a provided category.
        elif params['action'] == 'play':
            play_content(params['content_id'])      # Display photo or play video from a provided URL.
        else:
            # If the provided paramstring does not contain a supported action
            # we raise an exception. This helps to catch coding errors,
            # e.g. typos in action names.
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