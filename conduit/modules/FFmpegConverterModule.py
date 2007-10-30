import re

import conduit
import conduit.Utils as Utils

if Utils.program_installed("ffmpeg"):
    MODULES = {
        "FFmpegConverter" :  { "type": "converter" }
        }
else:
    MODULES = {}

class FFmpegCommandLineConverter(Utils.CommandLineConverter):
    def __init__(self, command, duration=None):
        Utils.CommandLineConverter.__init__(self,command)
        self.duration = duration
        self.percentage_match = re.compile('time=?(\d+\.\d+)')

    def calculate_percentage(self, val):
        return float(val)/self.duration*100.0
            
class FFmpegConverter:
    def __init__(self):
        self.conversions =  {
                            "file/video,file/video"     :   self.transcode_video,    
                            "file,file/video"           :   self.file_to_video,
                            "file/audio,file/audio"     :   self.transcode_audio,    
                            "file,file/audio"           :   self.file_to_audio
                            }

    def _build_command(self, **kwargs):
        command = "ffmpeg -i %(in_file)s "
        #video options
        if kwargs.get('vcodec', None):      command += "-vcodec %(vcodec)s "
        if kwargs.get('vbitrate', None):    command += "-b %(vbitrate)s "
        if kwargs.get('fps', None):         command += "-r %(fps)s " 
        if kwargs.get('vtag', None):        command += "-vtag %(vtag)s "
        if kwargs.get('width', None) and kwargs.get('height', None):
            command += "-s %(width)sx%(height)s "
        #audio options
        if kwargs.get('acodec', None):      command += "-acodec %(acodec)s "
        if kwargs.get('arate', None):       command += "-ar %(arate)s "
        if kwargs.get('abitrate', None):
            if kwargs.get('acodec', None) != 'ac3':
                command += "-ab %(abitrate)s "  
                if kwargs['abitrate'] < 64:
                    command += "-ac 1 "
                else:
                    command += "-ac 2 "
        #output file, overwrite and container format
        if kwargs.get('format', None):      command += "-f %(format)s "
        command += "-y %(out_file)s"

        return command % kwargs
                            
    def transcode_video(self, video, **kwargs):
        if not video.get_mimetype().startswith("video/"):
            conduit.logd("File is not video type")
            return None
            
        input_file = video.get_local_uri()
        #run ffmpeg over the video to work out its format, and duration
        c = FFmpegCommandLineConverter('ffmpeg -fs 1 -y -i "%s" -f avi "%s" 2>&1')
        ok,output = c.convert(input_file,"/dev/null",save_output=True)

        if not ok:
            conduit.logd("Error getting video information\n%s" % output)
            return None

        #extract the video parameters    
        pat = re.compile(r'Input.*?Duration: ([\d:]*\.*\d*).*?Stream #\d\.\d: Video:.*?(\d+)x(\d+)',re.DOTALL)
        try:
            duration_string,w,h = re.search(pat,output).groups()
            #make duration into seconds
            h,m,s = duration_string.split(':')
            duration = (60.0*60.0*float(h)) + (60*float(m)) + float(s)
        except AttributeError:
            conduit.logd("Error parsing ffmpeg output")
            return None
        conduit.logd("Input Video %s: size=%swx%sh, duration=%ss" % (input_file,w,h,duration))

        #build converstion options with defaults
        convargs = {
            'abitrate':kwargs.get('abitrate',128),
            'vbitrate':kwargs.get('vbitrate',200),
            'fps':kwargs.get('fps',29),
            'vcodec':kwargs.get('vcodec','theora'),
            'acodec':kwargs.get('acodec','vorbis'),
            'format':kwargs.get('format','ogg'),
            'in_file':'"%s"',
            'out_file':'"%s"',
            }
        if kwargs.get('width',None) != None and kwargs.get('height',None) != None:
            convargs['width'],convargs['height'] = Utils.get_proportional_resize(
                            desiredW=int(kwargs['width']),
                            desiredH=int(kwargs['height']),
                            currentW=int(w),
                            currentH=int(h)
                            )

        #convert the video
        command = self._build_command(**convargs)
        c = FFmpegCommandLineConverter(command, duration=duration)
        ok = c.convert(input_file,"/tmp/foo",callback=lambda x: conduit.logd(x))

        if not ok:
            conduit.logd("Error transcoding video")
            return None

        return video
        
    def transcode_audio(self, audio, **kwargs):
        if not audio.get_mimetype().startswith("audio/"):
            conduit.logd("File is not audio type")
            return None
            
        input_file = audio.get_local_uri()
        #run ffmpeg over the video to work out its duration
        c = FFmpegCommandLineConverter('ffmpeg -fs 1 -y -i "%s" -target vcd "%s" 2>&1')
        ok,output = c.convert(input_file,"/dev/null",save_output=True)

        if not ok:
            conduit.logd("Error getting audio information\n%s" % output)
            return None

        #extract the video parameters    
        pat = re.compile(r'Input.*?Duration: ([\d:]*\.*\d*)',re.DOTALL)
        try:
            duration_string = re.search(pat,output).group(1)
            #make duration into seconds
            h,m,s = duration_string.split(':')
            duration = (60.0*60.0*float(h)) + (60*float(m)) + float(s)
        except AttributeError:
            conduit.logd("Error parsing ffmpeg output")
            return None
        conduit.logd("Input Audio %s: duration=%ss" % (input_file,duration))
        
        #build converstion options with defaults
        convargs = {
            'arate':kwargs.get('arate',44100),
            'abitrate':kwargs.get('abitrate',96),
            'acodec':kwargs.get('acodec','vorbis'),
            'format':kwargs.get('format','ogg'),
            'in_file':'"%s"',
            'out_file':'"%s"',
            }

        #convert audio
        command = self._build_command(**convargs)
        c = FFmpegCommandLineConverter(command, duration=duration)
        ok = c.convert(input_file,"/tmp/foo",callback=lambda x: conduit.logd(x))

        if not ok:
            conduit.logd("Error transcoding audio")
            return None

        return audio
        
    def file_to_audio(self, f, **kwargs):
        t = f.get_mimetype()
        if t.startswith("audio/"):
            return self.transcode_audio(f,**kwargs)
        else:
            return None

    def file_to_video(self, f, **kwargs):
        t = f.get_mimetype()
        if t.startswith("video/"):
            return self.transcode_video(f,**kwargs)
        else:
            return None
        
if __name__ == "__main__":
    import conduit.datatypes.File as File
    c = FFmpegConverter()

    try:
        f = File.File("/home/john/Downloads/1002 - Smug Alert!.avi")
        c.transcode_video(f)
    except KeyboardInterrupt: pass

    try:
        f = File.File("/home/john/Music/Salmonella Dub/Inside The Dub Plates/01 - Problems.mp3")
        c.transcode_audio(f)
    except KeyboardInterrupt: pass

    
        
