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
                            
    def transcode_video(self, video, **kwargs):
        if not video.get_mimetype().startswith("video/"):
            conduit.logd("File is not video type")
            return None
            
        input_file = video.get_local_uri()
        #run ffmpeg over the video to work out its format, and duration
        c = FFmpegCommandLineConverter('ffmpeg -fs 1 -y -i "%s" -target vcd "%s" 2>&1')
        ok,output = c.convert(input_file,"/dev/null",save_output=True)

        if not ok:
            conduit.logd("Error getting video information")
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

        #get conversion options
        abitrate = kwargs.get('abitrate',96)
        vbitrate = kwargs.get('vbitrate',200)
        width = kwargs.get('width',None)
        height = kwargs.get('height',None)
        fps = kwargs.get('fps',15)
        vcodec = kwargs.get('vcodec','mpeg4')
        acodec = kwargs.get('acodec','ac3')
        format = kwargs.get('format','avi')

        #build command line args
        command = "ffmpeg -i %(in_file)s "
        #video options
        command += "-f %(format)s -vcodec %(vcodec)s -b %(vbitrate)s -r %(fps)s " #-vtag DIVX
        if width != None and height != None:
            width,height = Utils.get_proportional_resize(
                            desiredW=int(width),
                            desiredH=int(height),
                            currentW=int(w),
                            currentH=int(h)
                            )
            command += "-s %(width)sx%(height)s "
        #audio options
        command += "-acodec %(acodec)s -ar 44100 "
        if acodec != "ac3":
            command += "-ab %(abitrate)s "
        #downmix to mono if low audio rate
        if abitrate < 64:
            command += "-ac 1 "

        command += "-y %(out_file)s"
        command = command % {
                    'abitrate':abitrate,
                    'vbitrate':vbitrate,
                    'width':width,
                    'height':height,
                    'fps':fps,
                    'vcodec':vcodec,
                    'acodec':acodec,
                    'format':format,
                    'in_file':'"%s"',
                    'out_file':'"%s"'
                    }

        c = FFmpegCommandLineConverter(command, duration=duration)
        ok = c.convert(input_file,"/tmp/foo",callback=lambda x: conduit.logd(x))

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
            conduit.logd("Error getting audio information")
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
        
        #get conversion options
        arate = kwargs.get('arate',44100)
        abitrate = kwargs.get('abitrate',96)
        acodec = kwargs.get('acodec','vorbis')
        format = kwargs.get('format','ogg')

        #build command line args
        command = "ffmpeg -i %(in_file)s "
        #audio options
        command += "-acodec %(acodec)s -ar %(arate)s -ab %(abitrate)s -f %(format)s "
        #downmix to mono if low audio rate
        if abitrate < 64:
            command += "-ac 1 "
        command += "-y %(out_file)s"
        command = command % {
                    'arate':arate,
                    'abitrate':abitrate,
                    'acodec':acodec,
                    'format':format,
                    'in_file':'"%s"',
                    'out_file':'"%s"'
                    }

        c = FFmpegCommandLineConverter(command, duration=duration)
        ok = c.convert(input_file,"/tmp/foo",callback=lambda x: conduit.logd(x))

        return audio
        
    def file_to_audio(self, f, **kwargs):
        t = f.get_mime_type()
        if t.startswith("audio/"):
            return f
        else:
            return None

    def file_to_video(self, f, **kwargs):
        t = f.get_mime_type()
        if t.startswith("video/"):
            return Music.Music(URI=f._get_text_uri())
        else:
            return None
        
if __name__ == "__main__":
    import conduit.datatypes.File as File
    c = FFmpegConverter()

    #f = File.File("/home/john/Videos/House/house.312.hdtv-lol.avi")
    #c.transcode_video(f)

    f = File.File("/media/media/MusicToSort/Baitercell & Schumacher - Whats Down Low (Original Mix).mp3")
    c.transcode_audio(f)

    
        
