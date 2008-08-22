import re
import logging
import threading
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
    from gst.extend import discoverer
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

class GStreamerConversionPipeline(Pipeline):
    """
    Converts between different multimedia formats.
    This class is event-based and needs a mainloop to work properly.
    Emits the 'converted' signal when conversion is finished.
    Heavily based from gst.extend.discoverer

    The 'converted' callback has one boolean argument, which is True if the
    file was successfully converted.
    """
    
    #TODO: Although this is based more on Discoverer, it might be better to base
    # on some ideas from utils.GstMetadata, especially the pipeline reutilization
    # (might be a temporary fix to the need to run the discover to get media 
    # information then the conversion pipeline)

    __gsignals__ = {
        'converted' : (gobject.SIGNAL_RUN_FIRST,
                       None,
                       (gobject.TYPE_BOOLEAN, ))
        }
        
    
    def __init__(self, **kwargs):        
        Pipeline.__init__(self)
        #if 'file_mux' not in kwargs:
        #    raise Exception('Output file format not specified')        
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
            #TODO: Add dynamic video scaling, thus removing the need to run
            # the discoverer before conversion
            if ('width' in kwargs) or ('height' in kwargs):
                log.debug("Video dimensions specified")
                resolution = []                
                if 'width' in kwargs:
                    width = kwargs['width']
                    resolution.append('width=%s' % (width - width % 2))
                if 'height' in kwargs:
                    height = kwargs['height']
                    resolution.append('height=%s' % (height - height % 2))
                caps = gst.caps_from_string('video/x-raw-yuv,%s;video/x-raw-yuv,%s' % (','.join(resolution), ','.join(resolution)))
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
            #TODO: Add audio rate and sampler            
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
        log.debug("Conversion finished")
        self._success = success
        self.bus.remove_signal_watch()
        gobject.idle_add(self._stop)
        gobject.source_remove(self.watch)
        return False

    def _stop(self):
        log.debug('Conversion stop')
        self.set_state(gst.STATE_READY)
        self.emit('converted', self._success)

    def _bus_message_cb(self, bus, message):
        if message.type == gst.MESSAGE_EOS:
            #TODO: Any other possibility for end-of-stream other then successfull
            # conversion?
            log.debug("Conversion sucessfull")
            self._finished(True)
        #elif message.type == gst.MESSAGE_TAG:
        #    for key in message.parse_tag().keys():
        #        self.tags[key] = message.structure[key]
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
            log.debug("Conversion progress %.2f%%" % (float(pos)*100.0/dur))
            return (pos/float(gst.SECOND), dur/float(gst.SECOND))
        except gst.QueryError:
            log.debug("QUERY ERROR")
            return (0.0, 0.0)
                
    def convert(self):
        gst.debug_set_default_threshold(2)
        self.bus = self.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self._bus_message_cb)
        log.debug("Starting conversion")
        self.watch  = gobject.timeout_add(2000, self.progress)
        if not self.set_state(gst.STATE_PLAYING):
            self._finished()
            
class GStreamerConverter():
    def __init__(self, filename):
        self.filename = filename

    def get_stream_info(self, needs_audio = False, needs_video = False):                
        def discovered(discoverer, valid):
            self.valid = valid
            event.set()        
        event = threading.Event()    
        log.debug("Getting stream information file: %s" % self.filename)
        self.info = discoverer.Discoverer(self.filename)
        self.info.connect('discovered', discovered)
        self.info.discover()
        event.wait()        
        if not self.valid:
            raise Exception('Not a valid media file')
        if needs_video and not self.info.is_video:
            raise Exception("Not a valid video file")
        if needs_audio and not self.info.is_audio:
            raise Exception("Not a valid audio file")            
        if self.info.is_video:
            return (self.info.videowidth, self.info.videoheight, \
                self.info.videolength / gst.SECOND)
        elif self.info.is_audio:            
            return (self.info.audiolength / gst.SECOND)
        else:
            raise Exception
            
    def _run_pipeline(self, **kwargs):
        def converted(converter, success):
            if not success:
                raise Exception
            self.success = success
            event.set()            
        event = threading.Event()
        pipeline = GStreamerConversionPipeline(**kwargs)
        pipeline.connect("converted", converted)
        pipeline.convert()
        event.wait()        
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

    def transcode_video(self, video, **kwargs):
        #mimetype = video.get_mimetype()
        #if not Video.mimetype_is_video(mimetype):
        #    log.debug("File %s is not video type: %s" % (video,mimetype))
        #    return None
        input_file = video.get_local_uri()
        
        log.debug("Creating GStreamer converter")

        gst_converter = GStreamerConverter(input_file) 
        #try:
        log.debug("Getting video information")
        (w, h, duration) = gst_converter.get_stream_info(needs_video = True)
        #except:
        #    log.debug("Error getting video information")
        #    return None

        log.debug("Input Video %s: size=%swx%sh, duration=%ss" % (input_file,w,h,duration))

        if 'width' in kwargs and 'height' in kwargs:
            kwargs['width'],kwargs['height'] = Utils.get_proportional_resize(
                            desiredW=int(kwargs['width']),
                            desiredH=int(kwargs['height']),
                            currentW=int(w),
                            currentH=int(h)
                            )

        #TODO: Test folder_location code
        #if kwargs.has_key("folder_location"):
        #    output_file = kwargs.has_key("folder_location")
        #    if not os.path.isdir(output_file):
        #        log.debug("Output location not a folder")
        #        return None
        #    output_file = os.path.join(output_file, os.path.basename(input_file))
        #    log.debug("Using output_file = %s", output_file)
        #else:
        
        #create output file
        output_file = video.to_tempfile()
        if kwargs.has_key("file_extension"):
            video.force_new_file_extension(".%s" % kwargs["file_extension"])
        kwargs['in_file'] = input_file
        kwargs['out_file'] = output_file
        sucess = gst_converter.convert(**kwargs)
        
        if not sucess:
            log.debug("Error transcoding video\n%s" % output)
            return None

        return video

    def transcode_audio(self, audio, **kwargs):
        mimetype = audio.get_mimetype()
        if not Audio.mimetype_is_audio(mimetype):
            log.debug("File %s is not audio type: %s" % (audio,mimetype))
            return None
        input_file = audio.get_local_uri()


        gst_converter = GStreamerConverter(input_file)
        try:
            duration = gst_converter.get_stream_info(needs_audio = True)
        except:
            log.debug("Error getting audio information")
            return None

        log.debug("Input Audio %s: duration=%ss" % (input_file,duration))

        #create output file
        output_file = audio.to_tempfile()
        if kwargs.has_key("file_extension"):
            audio.force_new_file_extension(".%s" % kwargs["file_extension"])

        #convert audio
        kwargs['in_file'] = input_file
        kwargs['out_file'] = output_file
        sucess = gst_converter.convert(**kwargs)
        
        if not sucess:
            log.debug("Error transcoding audio\n%s" % output)
            return None

        return audio

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
