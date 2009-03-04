import random
import logging
log = logging.getLogger("modules.Feed")

import conduit
import conduit.utils as Utils
import conduit.dataproviders.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.File as File
import conduit.datatypes.Audio as Audio
import conduit.datatypes.Video as Video
import conduit.datatypes.Photo as Photo

from gettext import gettext as _

try:
    import feedparser
    MODULES = {
        "RSSSource" : { "type": "dataprovider" }    
    }
    log.info("Module Information: %s" % Utils.get_module_information(feedparser, "__version__"))

    #work around a bug in feedparser where it incorrectly detects
    #media enclosures
    #http://code.google.com/p/feedparser/issues/detail?id=100
    if feedparser.__version__ <= '4.1':
        log.info("Patching feedparser issue #100")
        def _start_media_content(self, attrsD):
            context = self._getContext()
            context.setdefault('media_content', [])
            context['media_content'].append(attrsD)


        def _start_media_thumbnail(self, attrsD):
            context = self._getContext()
            context.setdefault('media_thumbnail', [])
            self.push('url', 1) # new
            context['media_thumbnail'].append(attrsD)


        def _end_media_thumbnail(self):
            url = self.pop('url')
            context = self._getContext()
            if url != None and len(url.strip()) != 0:
                if not context['media_thumbnail'][-1].has_key('url'):
                    context['media_thumbnail'][-1]['url'] = url

        feedparser._FeedParserMixin._start_media_content = _start_media_content
        feedparser._FeedParserMixin._start_media_thumbnail = _start_media_thumbnail
        feedparser._FeedParserMixin._end_media_thumbnail = _end_media_thumbnail

except ImportError:
    MODULES = {}
    log.info("RSS Feed support disabled")

class RSSSource(DataProvider.DataSource):

    _name_ = _("RSS Feed")
    _description_ = _("Synchronize data from RSS enclosures")
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "source"
    _in_type_ = ""
    _out_type_ = "file"
    _icon_ = "feed"
    _configurable_ = True

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        self.update_configuration(
            feedUrl = "",
            limit = 0,
            randomize = False,
            downloadPhotos = True,
            downloadAudio = True,
            downloadVideo = True,
        )
        self.files = {}
        
    def _is_allowed_type(self, mimetype):
        ok = False
        if not ok and self.downloadPhotos:
            ok = Photo.mimetype_is_photo(mimetype)
        if not ok and self.downloadAudio:
            ok = Audio.mimetype_is_audio(mimetype)
        if not ok and self.downloadVideo:
            ok = Video.mimetype_is_video(mimetype)
        return ok

    def _add_file(self, url, title, t):
        log.debug("Got enclosure %s %s (%s)" % (title,url,t))
        if self._is_allowed_type(t):
            if len(self.files) < self.limit or self.limit == 0 or self.randomize:
                self.files[url] = (title,t)
        else:
            log.debug("Enclosure %s is an illegal type (%s)" % (title,t))

    def initialize(self):
        return True

    def config_setup(self, config):
        #FIXME: Add Randomize
        config.add_section("Feed details")
        config.add_item("Feed address", "text",
            config_name = 'feedUrl',
        )
        config.add_section("Enclosure settings")
        limit_config = config.add_item("Limit downloaded enclosures", "check",
            initial_value = (self.limit > 0)
        )
        limit_config.connect("value-changed", 
            lambda item, changed, value: limit_spin_config.set_enabled(value)
        )
        limit_spin_config = config.add_item("Limit to", "spin",
            config_name = 'limit',
            enabled = (self.limit > 0),
        )
        random_config = config.add_item("Randomize enclosures", "check",
            config_name = 'randomize'
        )
        
        config.add_section("Download types")
        config.add_item("Download audio files", "check", config_name = "downloadAudio")
        config.add_item("Download video files", "check", config_name = "downloadVideo")
        config.add_item("Download photo files", "check", config_name = "downloadPhotos")
    
    def refresh(self):
        DataProvider.DataSource.refresh(self)
        #url : (title, mimetype)
        self.files = {}
        d = feedparser.parse(self.feedUrl)
        for entry in d.entries:
            #check for enclosures first (i.e. podcasts)
            for enclosure in entry.get('enclosures', ()):
                self._add_file(enclosure['href'], entry.title, enclosure['type'])
            #also check for media_content (like flickr)
            for media in entry.get('media_content', ()):
                self._add_file(media['url'], entry.title, media['type'])

    def get_all(self):
        DataProvider.DataSource.get_all(self)
        all_files = self.files.keys()

        if self.randomize:
            if self.limit == 0:
                #no need to randomly choose between *all* files,
                #as order is irellevant, really
                return all_files
            else:
                #randomly choose limit files from all_files
                lim = self.limit
                files = []
                while lim > 0:
                    files.append(all_files.pop(random.randint(0,len(all_files)-1)))
                    lim -= 1
                return files
        else:
            return all_files
            
    def get(self, url):
        DataProvider.DataSource.get(self, url)
        #Make a file
        f = File.File(URI=url)
        f.set_UID(url)
        f.set_open_URI(url)
        name, ext = f.get_filename_and_extension()
        
        #create the correct filename and retain the original extension
        try:
            title,t = self.files[url]
            f.force_new_filename(title)
            f.force_new_file_extension(ext)
        except:
            log.warn("Error setting filename\n%s" % traceback.format_exc())

        return f

    def finish(self, aborted, error, conflict):
        DataProvider.DataSource.finish(self)
        self.files = {}

    def get_UID(self):
        return self.feedUrl
