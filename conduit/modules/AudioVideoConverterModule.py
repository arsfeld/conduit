import re
import logging
import threading
import tempfile
import os
log = logging.getLogger("modules.AVConverter")

import conduit
import conduit.utils as Utils
import conduit.TypeConverter as TypeConverter
import conduit.datatypes.File as File
import conduit.datatypes.Audio as Audio
import conduit.datatypes.Video as Video

import gobject

try:
    import gst
    from gst import Pipeline
    MODULES = {
        "AudioVideoConverter" :  { "type": "converter" }
    }
    log.info("Module Information: %s" % Utils.get_module_information(gst, "pygst_version"))
except ImportError:
    class Pipeline: 
        pass    
    MODULES = {}
    log.info("GStreamer transcoding disabled")

'''
GStreamer Conversion properties

The parameteres to a GStreamer conversion usually require the name of an 
GStreamer element.
All of the availiable elements in a GStreamer installation can be found with
the "gst-inspect" command, usually found in the gstreamer-tools package.
If an element is missing, it probably requires the bad or ugly packages from
GStreamer.
These elements will be used with gst.parse_launch, which can take properties 
with them, such as "faac bitrate=320000". Only single elements are supported
now. You can find the syntax in the gst-launch manual ("man gst-launch").
All the properties of each element can be found with the command
"gst-inspect <element-name>".

These are the properties the GStreamer converter can take:
 - mux (string, optional): Name of the file muxer used to group the audio 
    and video data, if required. Example: avimux or any of the ffmux elements
 - vcodec (string, optional): Name of the video data encoder. If not 
    specified, no video will be encoded.
    Examples: x264enc, theoraenc
 - acodec (string, optional): Name of the audio data encoder. If not 
    specified, audio won't be availiable.
    Examples: faac, vorbisenc
 - width and height (int, optional): Required video dimensions. If only one is
    specified, the other is calculated to keep the video proportional.    
'''

PROGRESS_WAIT = 2.5

class GStreamerConversionPipeline(Pipeline):
    """
    Converts between different multimedia formats.
    This class is event-based and needs a mainloop to work properly.
    Emits the 'converted' signal when conversion is finished.
    Heavily based on gst.extend.discoverer

    The 'converted' callback has one boolean argument, which is True if the
    file was successfully converted.
    """

    __gsignals__ = {
        'converted' : (gobject.SIGNAL_RUN_FIRST,
                       None,
                       (gobject.TYPE_BOOLEAN, ))
        }
        
    
    def __init__(self, **kwargs):        
        Pipeline.__init__(self)
        self._has_video_enc = ('vcodec' in kwargs) or ('vcodec_pass1' in kwargs) or ('vcodec_pass2' in kwargs)
        self._has_audio_enc = 'acodec' in kwargs
        if not self._has_video_enc and not self._has_audio_enc:
            raise Exception('At least one output must be specified')
            
        self._pass = kwargs.get('pass', 0)
        self._filesrc = gst.element_factory_make('filesrc')        
        self._filesrc.set_property('location', kwargs['in_file'])
        self._decodebin = gst.element_factory_make('decodebin')
        self._decodebin.connect('new-decoded-pad', self._dbin_decoded_pad)
        self._filesink = gst.element_factory_make('filesink')
        self._filesink.set_property('location', kwargs['out_file'])
        
        self.add(self._filesrc, self._decodebin, self._filesink)
        self._filesrc.link(self._decodebin)
        
        if self._pass == 1:
            self._fileout = gst.element_factory_make('fakesink')
            self.add(self._fileout)
        elif 'format' in kwargs:
            #TODO: File muxer could probably be found by inspection (from a mime
            # string, for instance)
            self._filemuxer = gst.parse_launch(kwargs['format'])
            self.add(self._filemuxer)
            self._filemuxer.link(self._filesink)
            self._fileout = self._filemuxer        
        else:
            self._fileout = self._filesink
        #TODO: Create video and audio encoders on demand
        if self._has_video_enc:
            self._video_queue = gst.element_factory_make('queue')
            self._video_scale = gst.element_factory_make('videoscale')
            self._video_ffmpegcolorspace = gst.element_factory_make('ffmpegcolorspace')
            if self._pass == 1 and 'vcodec_pass1' in kwargs:
                self._video_enc = gst.parse_launch(kwargs['vcodec_pass1'])
            elif self._pass == 2 and 'vcodec_pass2' in kwargs:
                self._video_enc = gst.parse_launch(kwargs['vcodec_pass2'])
            else:
                if self._pass != 0:
                    log.debug("Creating generic video encoder for pass != 0")
                self._video_enc = gst.parse_launch(kwargs['vcodec'])            
            self.add(self._video_queue, self._video_scale, self._video_ffmpegcolorspace, self._video_enc)
            # Dont link videoscale to ffmpegcolorspace yet
            self._video_queue.link(self._video_scale)
            self._video_ffmpegcolorspace.link(self._video_enc)
            if ('width' in kwargs) or ('height' in kwargs):
                log.debug("Video dimensions specified")
                resolution = []                
                if 'width' in kwargs:
                    width = kwargs['width']
                    # Make sure it works with all encoders
                    resolution.append('width=%s' % (width - width % 2))
                if 'height' in kwargs:
                    height = kwargs['height']
                    resolution.append('height=%s' % (height - height % 2))
                resolution = ','.join(resolution)
                caps = gst.caps_from_string('video/x-raw-yuv,%s;video/x-raw-rgb,%s' % (resolution, resolution))
                self._video_scale.link_filtered(self._video_ffmpegcolorspace, caps)
            else:
                self._video_scale.link(self._video_ffmpegcolorspace)
            # Pad linked to decodebin in decoded_pad
            self._video_pad = self._video_queue.get_pad('sink')
            # Final element linked to file muxer in decoded_pad
            self._video_src = self._video_enc
        else:
            self._video_pad = None
        if self._has_audio_enc and self._pass != 1:
            self._audio_queue = gst.element_factory_make('queue')
            self._audio_convert = gst.element_factory_make('audioconvert')
            self._audio_resample = gst.element_factory_make('audioresample')
            self._audio_rate = gst.element_factory_make('audiorate')            
            self._audio_enc = gst.parse_launch(kwargs['acodec'])
            self.add(self._audio_queue, self._audio_convert, self._audio_resample, self._audio_rate, self._audio_enc)
            gst.element_link_many(self._audio_queue, self._audio_convert, self._audio_resample, self._audio_rate, self._audio_enc)
            # Pad linked to decodebin
            self._audio_pad = self._audio_queue.get_pad('sink')
            # Final element linked to file muxer in decoded_pad
            self._audio_src = self._audio_enc
        else:
            self._audio_pad = None
            
    def _finished(self, success=False):
        self._success = success
        self.bus.remove_signal_watch()
        gobject.idle_add(self._stop)
        return False

    def _stop(self):
        self.set_state(gst.STATE_READY)
        self.emit('converted', self._success)

    def _bus_message_cb(self, bus, message):
        if message.type == gst.MESSAGE_EOS:
            #TODO: Any other possibility for end-of-stream other then successfull
            # conversion?
            log.debug("Conversion sucessfull")
            self._finished(True)
        elif message.type == gst.MESSAGE_ERROR:
            log.debug("Conversion error")
            self._finished()     
            
    def _dbin_decoded_pad(self, dbin, pad, is_last):
        caps = pad.get_caps()
        log.debug("Caps found: %s" % caps.to_string())        
        if caps.to_string().startswith('video'):
            if self._video_pad and not self._video_pad.is_linked():
                log.debug("Linking video encoder: %s" % (self._video_pad))
                pad.link(self._video_pad)
                self._video_src.link(self._fileout)
            elif self._video_pad:
                log.debug("Video encoder already linked, probably multiple video streams")
            else:
                log.debug("Video caps found, but no video encoder")
        elif caps.to_string().startswith('audio'):
            if self._audio_pad and not self._audio_pad.is_linked():
                log.debug("Linking audio encoder")
                pad.link(self._audio_pad)
                self._audio_src.link(self._fileout)
            elif self._audio_pad:
                log.debug("Audio encoder already linked, probably multiple audio streams")
            else:
                log.debug("Audio caps found, but no audio encoder")
                
    def progress(self):        
        try:
            (pos, format) = self.query_position(gst.FORMAT_TIME)
            (dur, format) = self.query_duration(gst.FORMAT_TIME)
            return (pos/float(gst.SECOND), dur/float(gst.SECOND))
        except gst.QueryError:
            log.debug("Conversion query ERROR")
            return (0.0, 0.0)
                
    def convert(self):
        gst.debug_set_default_threshold(2)
        self.bus = self.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self._bus_message_cb)
        log.debug("Starting conversion")
        if not self.set_state(gst.STATE_PLAYING):
            self._finished()
            
class GStreamerConverter():
    def _run_pipeline(self, **kwargs):
        def converted(converter, success):
            self.success = success
            event.set()
        event = threading.Event()
        pipeline = GStreamerConversionPipeline(**kwargs)
        pipeline.connect("converted", converted)
        pipeline.convert()
        current_thread = threading.currentThread()
        check_progress = False
        while not event.isSet():
            # Dont print an error message if we havent yet started the conversion
            if check_progress:
                (time, total) = pipeline.progress()
                if total:
                    log.debug("Conversion progress: %.2f%%" % (100.0 * time/total))
            event.wait(PROGRESS_WAIT)
			# FIXME: A little hackish, but works.
            if hasattr(current_thread, 'cancelled'):
                if current_thread.cancelled:
                    log.debug("Stopping conversion")
                    pipeline.set_state(gst.STATE_NULL)      
                    pipeline = None
                    return False
            check_progress = True
        pipeline.set_state(gst.STATE_NULL)
        pipeline = None
        return self.success

    def convert(self, **kwargs):
        if kwargs.get('twopass', False):
            kwargs['pass'] = 1
            self._run_pipeline(**kwargs)
            kwargs['pass'] = 2
            return self._run_pipeline(**kwargs)
        else:
            return self._run_pipeline(**kwargs)


class AudioVideoConverter(TypeConverter.Converter):

    def __init__(self):
        self.conversions =  {
                            "file/video,file/video"     :   self.transcode_video,
                            "file,file/video"           :   self.file_to_video,
                            "file/audio,file/audio"     :   self.transcode_audio,
                            "file,file/audio"           :   self.file_to_audio
                            }

    def _get_output_file(self, input_file, **kwargs):
        # We are not checking the contents of keep_converted, because it is a 
        # string, not a bool, even if it was a bool in the args
        use_temp = not kwargs.has_key("keep_converted")
        if not use_temp:
            try:
                (input_folder, input_filename) = os.path.split(input_file)
                output_folder = os.path.join(input_folder, "Converted Files")
                if not os.path.exists(output_folder):
                    os.mkdir(output_folder)
                output_file = os.path.join(output_folder, input_filename)
                if 'file_extension' in kwargs:
                    output_file = os.path.splitext(output_file)[0] + '.' + kwargs['file_extension']
                #TODO: If the file already exists, we could probably not convert it,
                # because it could've been converted before
                #if os.path.is_file(output_file):
                #    return video
            except Exception, e:
                log.debug("Using temp folder as a fallback: %s" % e)
                use_temp = True
        if use_temp:
            output_file = tempfile.mkstemp(suffix='conduit')[1]
            if kwargs.has_key("file_extension"):
                output_file += '.' + kwargs["file_extension"]
        log.debug("Using output_file = %s", output_file)
        return output_file
        
    def transcode_video(self, video, **kwargs):
        #FIXME: This code fails with flv. Should we add an exception?
        mimetype = video.get_mimetype()
        if not Video.mimetype_is_video(mimetype):
            log.debug("File %s is not video type: %s" % (video,mimetype))
            return None
        
        #Check if we need to convert the video
        if kwargs.get('mimetype', None) == mimetype:
            #Check if the video is smaller or equal then the required dimensions
            #If it does, we dont need to convert it
            width = kwargs.get('width', None)
            height = kwargs.get('height', None)
            if width or height:
                (video_width, video_height) = video.get_video_size()                
                if (not width or video_width <= width) and \
                   (not height or video_height <= height):
                    log.debug("Video matches the required dimensions, not converting")
                    return video
            else:
                #There is no required dimensions, and we match the mimetype,
                #so we dont convert it
                log.debug("Video matches the mimetype, not converting")
                return video

        kwargs['in_file'] = video.get_local_uri()
        kwargs['out_file'] = self._get_output_file(kwargs['in_file'], **kwargs)
        if os.path.exists(kwargs['out_file']):
            log.debug('Converted video already exists, using it')
            return Video.Video(kwargs['out_file'])
                       
        if 'width' in kwargs and 'height' in kwargs:
            (width, height) = video.get_video_size()
            if not width and not height:
                log.debug("Can't get video dimensions")
                return None
            kwargs['width'],kwargs['height'] = Utils.get_proportional_resize(
                            desiredW=int(kwargs['width']),
                            desiredH=int(kwargs['height']),
                            currentW=int(width),
                            currentH=int(height)
                            )
            log.debug("Scaling video to %swx%sh" % (kwargs['width'],kwargs['height']))
 
        try:
            gst_converter = GStreamerConverter()
            sucess = gst_converter.convert(**kwargs)       
        except Exception, e:
            log.debug("Error transcoding video: %s" % e)
            return None
        
        if not sucess:
            log.debug("Error transcoding video\n")
            return None
        
        return Video.Video(kwargs['out_file'])

    def transcode_audio(self, audio, **kwargs):
        mimetype = audio.get_mimetype()
        if not Audio.mimetype_is_audio(mimetype):
            log.debug("File %s is not audio type: %s" % (audio,mimetype))
            return None
        
        kwargs['in_file'] = audio.get_local_uri()
        kwargs['out_file'] = self._get_output_file(kwargs['in_file'], **kwargs)
        
        if kwargs.get('mimetype', None) == mimetype:    
            log.debug('No need to convert file')
            return audio
        
        #convert audio
        gst_converter = GStreamerConverter()
        sucess = gst_converter.convert(**kwargs)
        
        if not sucess:
            log.debug("Error transcoding audio\n")
            return None

        return Audio.Audio(kwargs['out_file'])

    def file_to_audio(self, f, **kwargs):
        mimetype = f.get_mimetype()
        if Audio.mimetype_is_audio(mimetype):
            a = Audio.Audio(
                        URI=f._get_text_uri()
                        )
            a.set_from_instance(f)
            if len(kwargs) > 0:
                return self.transcode_audio(a,**kwargs)
            else:
                return a
        else:
            return None

    def file_to_video(self, f, **kwargs):
        mimetype = f.get_mimetype()
        if Video.mimetype_is_video(mimetype):
            v = Video.Video(
                        URI=f._get_text_uri()
                        )
            v.set_from_instance(f)
            if len(kwargs) > 0:
                return self.transcode_video(v,**kwargs)
            else:
                return v
        else:
            return None
