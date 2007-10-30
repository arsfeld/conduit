import re

import conduit
import conduit.Utils as Utils
import conduit.datatypes.File as File

if Utils.program_installed("ffmpeg"):
    MODULES = {
        "AudioVideoConverter" :  { "type": "converter" }
        }
else:
    MODULES = {}

class FFmpegCommandLineConverter(Utils.CommandLineConverter):
    def __init__(self, duration=None):
        Utils.CommandLineConverter.__init__(self)
        self.duration = duration
        self.percentage_match = re.compile('time=?(\d+\.\d+)')

    def build_command(self, **kwargs):
        kwargs['in_file'] = '"%s"'
        kwargs['out_file'] = '"%s"'

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
        if kwargs.get('achannels', None):   command += "-ac %(achannels) "
        #output file, overwrite and container format
        if kwargs.get('format', None):      command += "-f %(format)s "
        command += "-y %(out_file)s"

        self.command = command % kwargs

    def calculate_percentage(self, val):
        return float(val)/self.duration*100.0

    def check_cancelled(self):
        return conduit.GLOBALS.cancelled

class MencoderCommandLineConverter(Utils.CommandLineConverter):
    def __init__(self):
        Utils.CommandLineConverter.__init__(self)
        self.percentage_match = re.compile('(\d+)%')

    def build_command(self, **kwargs):
        kwargs['in_file'] = '"%s"'
        kwargs['out_file'] = '"%s"'

        command = "mencoder %(in_file)s -o %(out_file)s "
        #audio options
        if kwargs.get('arate', None):       command += "-srate %(arate)s "
        if kwargs.get('achannels', None):   command += "-channels %(achannels) "
        #only support lavc atm
        command += "-oac lavc "
        if kwargs.has_key('acodec') and kwargs.has_key('abitrate'):
            command += "-lavcopts acodec=%(acodec)s:abitrate=%(abitrate)s "
        if kwargs.get('achannels', None):
            command += "-af volnorm,channels=%(achannels) "
        else:
            command += "-af volnorm "
        #video options (only support lavc atm)
        command += "-ovc lavc "
        if kwargs.has_key('vcodec') and kwargs.has_key('vbitrate'):
            command += "-ovc lavc -lavcopts vcodec=%(vcodec)s:vbitrate=%(vbitrate)s "
        if kwargs.get('width', None) and kwargs.get('height', None):
            command += "-vf-add scale=%(width)s:%(height)s "
        if kwargs.get('fps', None):         command += "-ofps %(fps)s "
        if kwargs.get('vtag', None):        command += "-ffourcc %(vtag)s "

        self.command = command % kwargs

    def calculate_percentage(self, val):
        return float(val)

    def check_cancelled(self):
        return conduit.GLOBALS.cancelled
            
class AudioVideoConverter:
    def __init__(self):
        self.conversions =  {
                            "file/video,file/video"     :   self.transcode_video,    
                            "file,file/video"           :   self.file_to_video,
                            "file/audio,file/audio"     :   self.transcode_audio,    
                            "file,file/audio"           :   self.file_to_audio
                            }

    def transcode_video(self, video, **kwargs):
        if not video.get_mimetype().startswith("video/"):
            conduit.logd("File is not video type")
            return None
        input_file = video.get_local_uri()
        
        #run ffmpeg over the video to work out its format, and duration
        c = Utils.CommandLineConverter()
        c.build_command('ffmpeg -fs 1 -y -i "%s" -f avi "%s" 2>&1')
        ok,output = c.convert(input_file,"/dev/null",save_output=True)

        if not ok:
            conduit.logd("Error getting video information\n%s" % output)
            return None

        #extract the video parameters    
        pat = re.compile(r'Input.*?Duration: ([\d:]*\.*\d*).*?Stream #\d\.\d: Video:.*?(\d+)x(\d+)',re.DOTALL)
        try:
            duration_string,w,h = re.search(pat,output).groups()
            #make duration into seconds
            ho,m,s = duration_string.split(':')
            duration = (60.0*60.0*float(ho)) + (60*float(m)) + float(s)
        except AttributeError:
            conduit.logd("Error parsing ffmpeg output")
            return None
        conduit.logd("Input Video %s: size=%swx%sh, duration=%ss" % (input_file,w,h,duration))

        if kwargs.get('width',None) != None and kwargs.get('height',None) != None:
            kwargs['width'],kwargs['height'] = Utils.get_proportional_resize(
                            desiredW=int(kwargs['width']),
                            desiredH=int(kwargs['height']),
                            currentW=int(w),
                            currentH=int(h)
                            )

        #create output file
        out = File.TempFile()
        out.pretend_to_be(video)
        output_file = out.get_local_uri()

        #convert the video
        if kwargs.get("mencoder", False) and Utils.program_installed("mencoder"):
            c = MencoderCommandLineConverter()
        else:    
            c = FFmpegCommandLineConverter(duration=duration)
        c.build_command(**kwargs)
        ok,output = c.convert(
                        input_file,
                        output_file,
                        callback=lambda x: conduit.logd("Trancoding video %s%% complete" % x),
                        save_output=True
                        )

        if not ok:
            conduit.logd("Error transcoding video\b%s" % output)
            return None

        return out
        
    def transcode_audio(self, audio, **kwargs):
        if not audio.get_mimetype().startswith("audio/"):
            conduit.logd("File is not audio type")
            return None
        input_file = audio.get_local_uri()

        #run ffmpeg over the video to work out its format, and duration
        c = Utils.CommandLineConverter()
        c.build_command('ffmpeg -fs 1 -y -i "%s" -f wav "%s" 2>&1')
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
        
        #create output file
        out = File.TempFile()
        out.pretend_to_be(audio)
        output_file = out.get_local_uri()

        #convert audio
        c = FFmpegCommandLineConverter(duration=duration)
        c.build_command(**kwargs)
        ok,output = c.convert(
                        input_file,
                        output_file,
                        callback=lambda x: conduit.logd("Trancoding audio %s%% complete" % x),
                        save_output=True
                        )

        if not ok:
            conduit.logd("Error transcoding audio\n%s" % output)
            return None

        return out
        
    def file_to_audio(self, f, **kwargs):
        t = f.get_mimetype()
        if t.startswith("audio/"):
            #FIXME: Only transcode if necessary
            return self.transcode_audio(f,**kwargs)
        else:
            return None

    def file_to_video(self, f, **kwargs):
        t = f.get_mimetype()
        if t.startswith("video/"):
            #FIXME: Only transcode if necessary
            return self.transcode_video(f,**kwargs)
        else:
            return None
        
if __name__ == "__main__":
    import conduit.datatypes.File as File
    c = AudioVideoConverter()

    try:
        f = File.File("/home/john/Downloads/1002 - Smug Alert!.avi")
        args = {'abitrate':128,'vbitrate':200,'fps':15,'vcodec':'theora','acodec':'vorbis','format':'ogg',"width":640,"height":480}
        c.transcode_video(f,**args)
    except KeyboardInterrupt: pass

    try:
        f = File.File("/home/john/Downloads/1002 - Smug Alert!.avi")
        args = {'arate':44100,'acodec':'mp3','abitrate':128,'vcodec':'mpeg4','vbitrate':420,"fps":15,"vtag":"DIVX","width":320,"height":240}
        #use mencoder not ffmpef
        args["mencoder"] = True
        c.transcode_video(f,**args)
    except KeyboardInterrupt: pass


    try:
        f = File.File("/home/john/Music/Salmonella Dub/Inside The Dub Plates/01 - Problems.mp3")
        args = {'arate':44100,'abitrate':96,'acodec':'vorbis','format':'ogg'}
        c.transcode_audio(f,**args)
    except KeyboardInterrupt: pass

    
        
