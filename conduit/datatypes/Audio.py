import conduit
import conduit.datatypes.File as File
import conduit.utils.MediaFile as MediaFile
import logging
log = logging.getLogger("datatypes.Audio")

from threading import Lock

PRESET_ENCODINGS = {
    "ogg":{"acodec":"vorbisenc","format":"oggmux","file_extension":"ogg"},
    "wav":{"acodec":"wavenc","file_extension":"wav"},
    "mp3":{"acodec":"lame", "file_extension": "mp3"},
    }

def mimetype_is_audio(mimetype):
    """
    @returns: True if the given mimetype string represents an audio file
    """
    if mimetype.startswith("audio/"):
        return True
    elif mimetype == "application/ogg":
        return True
    else:
        return False

class Audio(MediaFile.MediaFile):

    _name_ = "file/audio"

    def __init__(self, URI, **kwargs):
        MediaFile.MediaFile.__init__(self, URI, **kwargs)

    def get_audio_title(self):
        '''
        Song title (string)
        '''
        return self._get_metadata('title')

    def get_audio_artist(self):
        '''
        Song artist (string)
        '''
        return self._get_metadata('artist')

    def get_audio_album(self):
        '''
        Song album (string)
        '''
        return self._get_metadata('album')

    def get_audio_track(self):
        return self._get_metadata('track-number')

    def get_audio_tracks(self):

        return self._get_metadata('track-count')

    def get_audio_bitrate(self):
        '''
        Bitrate of the audio stream (int)
        '''
        return self._get_metadata('bitrate')

    def get_audio_composer(self):
        '''
        Song composer
        '''
        return self._get_metadata('composer')

    def get_audio_duration(self):
        '''
        Duration in miliseconds (int)
        '''
        return self._get_metadata('duration')

    def get_audio_samplerate(self):
        '''
        Sample rate of the audio stream (int)
        '''
        return self._get_metadata('samplerate')

    def get_audio_channels(self):
        '''
        Number of channels in the audio stream (int)
        '''
        return self._get_metadata('channels')

    def get_audio_rating(self):
        '''
        Audio rating from 0.0 to 5.0
        '''
        return self._get_metadata('rating')

    def get_audio_cover_location(self):
        return self._get_metadata('cover_location')
