import re

import conduit
import conduit.Utils as Utils

if Utils.program_installed("mencoder"):
    MODULES = {
        "MencoderConverter" :  { "type": "converter" }
        }
else:
    MODULES = {}

VIDEO_TYPES = (
    "video/mpeg"
    )

class MencoderConverter:
    def __init__(self):
        self.conversions =  {
                            "file/video,file/video"     :   self.transcode,    
                            "file,file/video"           :   self.file_to_video
                            }
                            
    def transcode(self, video, **kwargs):
        input_file = "/home/john/Downloads/house.404.hdtv-lol.avi"
        #run mencoder over the video to work out its format, etc
        c = Utils.CommandLineConverter('mencoder "%s" -endpos 0 -oac copy -ovc copy -o "%s" 2>&1')
        ok,output = c.convert(input_file,"/dev/null",save_output=True)

        if not ok:
            conduit.logd("Error getting video information")
            return None

        #extract the video parameters    
        pat = r'\nVIDEO:\s*\[?(\w+)\]?.*?(\d+)x(\d+).*?([\d\.]+)\s*fps.*?([\d\.]+)\s*kbps'
        try:
            format,w,h,fps,vbr = re.search(pat,output).groups()
        except AttributeError:
            conduit.logd("Error parsing mencoder output")
            return None
        #extract aspect ratio
        try:
            aspect, = re.search(r'\nVIDEO:.*?\(aspect\s+(\d+)\)',output).groups()
        except AttributeError:
            aspect = 1

        conduit.logd("Input Video %s: format=%s, size=%swx%sh, fps=%s, bitrate=%s, aspect=%s" % (input_file,format,w,h,fps,vbr,aspect))

        #get conversion options
        abitrate = kwargs.get('abitrate',96)
        vbitrate = kwargs.get('vbitrate',200)
        width = kwargs.get('width',320)
        height = kwargs.get('height',240)
        fps = kwargs.get('fps',15)
        vcodec = kwargs.get('vcodec','mpeg4')
        acodec = kwargs.get('acodec','mp3')

        #build command line args
        command = "$(in_file)s -o $(out_file)s -srate 44100 "
        #downmix to mono if low audio rate
        if abitrate < 64:
            command += "-channels 1 "
        #audio options
        command += "-oac lavc -lavcopts acodec=%(acodec)s:abitrate=%(abitrate)s "
        if abitrate < 64:
            command += "-af volnorm,channels=1 "
        else:
            command += "-af volnorm "
        #video options
        command += "-ovc lavc -lavcopts vcodec=%(vcodec)s:vbitrate=%(vbitrate)s "

        conduit.log(command)
        return video

    def file_to_video(self, f, **kwargs):
        t = f.get_mime_type()
        #if t in MUSIC_TYPES:
        #    return Music.Music(URI=f._get_text_uri())
        #else:
        return None
