import conduit
import conduit.datatypes.File as File
import conduit.utils.MediaFile as MediaFile
import logging
log = logging.getLogger("datatypes.Audio")

PRESET_ENCODINGS = {
    "ogg":{"description": "Ogg", "acodec": "vorbisenc", "format":"oggmux","file_extension":"ogg", 'mimetype': 'application/ogg'},
    "wav":{"description": "Wav", "acodec": "wavenc", "file_extension":"wav", 'mimetype': 'audio/x-wav'},
    "mp3":{"description": "Mp3", "acodec": "lame", "file_extension": "mp3", 'mimetype':'audio/mpeg'},
    #AAC conversion doesn't work
    #"aac":{"description": "AAC", "acodec": "faac", "file_extension": "m4a"},    
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
        Song title (str)
        '''
        return self._get_metadata('title')

    def get_audio_artist(self):
        '''
        Song artist (str)
        '''
        return self._get_metadata('artist')

    def get_audio_album(self):
        '''
        Song album (str)
        '''
        return self._get_metadata('album')

    def get_audio_genre(self):
        '''
        Song genre (str)
        '''
        return self._get_metadata('genre')

    def get_audio_track(self):
        '''
        Get number of the track inside the album (int)
        '''
        return self._get_metadata('track-number')

    def get_audio_tracks(self):
        '''
        Get number of tracks in album (int)
        '''
        return self._get_metadata('track-count')

    def get_audio_bitrate(self):
        '''
        Bitrate of the audio stream, in bits/sec (int)
        '''
        return self._get_metadata('bitrate')

    def get_audio_composer(self):
        '''
        Song composer (str)
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

    def get_audio_playcount(self):
        '''
        Audio play count (int)
        '''
        return self._get_metadata('play_count')

    def get_audio_rating(self):
        '''
        Audio rating from 0.0 to 5.0 (float)
        '''
        return self._get_metadata('rating')

    def get_audio_cover_location(self):
        '''
        Get path to the track album cover (str)
        '''
        return self._get_metadata('cover_location')
