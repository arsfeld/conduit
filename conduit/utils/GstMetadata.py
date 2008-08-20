# -*- coding: utf-8 -*-
# Elisa - Home multimedia server
# Copyright (C) 2006-2008 Fluendo Embedded S.L. (www.fluendo.com).
# All rights reserved.
#
# This file is available under one of two license agreements.
#
# This file is licensed under the GPL version 2.
# See "LICENSE.GPL" in the root of this distribution including a special
# exception to use Elisa with Fluendo's plugins.
#
# The GPL part of Elisa is also available under a commercial licensing
# agreement from Fluendo.
# See "LICENSE.Elisa" in the root directory of this distribution package
# for details on that license.

import gobject
gobject.threads_init()
import pygst
pygst.require('0.10')
import gst
import logging
import os
import sys
import time
from threading import Lock
from Queue import Queue
import platform

import md5

if platform.system() == 'windows':
    import win32process

SEEK_SCHEDULED = 'scheduled'
SEEK_DONE = 'done'

THUMBNAIL_DIR = os.path.join(os.path.expanduser("~"), ".thumbnails", 'large')
THUMBNAIL_SIZE = 256

__maintainer__ = 'Alessandro Decina <alessandro@fluendo.com>'

supported_metadata_keys = set(['artist', 'album', 'song', 'track', 'thumbnail'])
media_type_keys = set(['uri', 'file_type', 'mime_type'])
thumbnail_keys = set(['uri', 'thumbnail'])
supported_keys = supported_metadata_keys.union(media_type_keys)
supported_schemes = ['file', 'http']

class MetadataError(Exception):
    pass

class InitializeFailure(MetadataError):
    pass

class TimeoutError(MetadataError):
    pass

class GstMetadataError(MetadataError):
    pass

class UriError(MetadataError):
    pass

def able_to_handle(supported_schemes, supported_keys, metadata):
    uri = metadata.get('uri')
    if not uri or uri.scheme not in supported_schemes:
        return False

    keys = set(metadata.keys())
    if uri.scheme == 'file' and os.path.isdir(uri.path) and \
            keys != media_type_keys:
        return False

    request_keys = supported_keys.intersection(metadata.keys())
    request_empty_keys = \
            [key for key in request_keys if metadata[key] is None]

    if request_empty_keys:
        return True

    return False

class MetadataProvider(object):
    pass

class Loggable(object):
    def debug(self, msg):
        logging.warning(msg)
        #logging.debug(msg)

    def log(self, msg):
        logging.warning(msg)
        #logging.info(msg)

class GstMetadataPipeline(Loggable):
    reuse_elements = True
    timeout = 2
    thumb_timeout = 1

    def __init__(self):
        super(GstMetadataPipeline, self).__init__()
        self._pipeline = None
        self._src = None
        self._decodebin = None
        self._ffmpegcolorspace = None
        self._imgthumbbin = None
        self._videothumbbin = None
        self._plugged_elements = []
        self._frame_locations = [1.0 / 3.0, 2.0 / 3.0, 0.1, 0.9, 0.5]

        # other instance variables that need to be reset for each new metadata
        # request are set directly in _reset()

    def clean(self):
        self._clean_pipeline(finalize=True)

        if self._timeout_call is not None:
            self._timeout_call.cancel()
            self._timeout_call = None

        if self._seek_call is not None:
            self._seek_call.cancel()
            self._seek_call = None

    def initialize(self):
        self._reset()

    def _clean_pipeline(self, finalize=False):
        # reset the pipeline to READY
        if self._pipeline is not None:
            self._bus.set_flushing(True)
            self._pipeline.set_state(gst.STATE_READY)

        if self._src is not None:
            self._pipeline.remove(self._src)
            self._src.set_state(gst.STATE_NULL)
            self._src = None

        if not self.reuse_elements or finalize:
            # destroy the pipeline
            if self._pipeline is not None:
                self._bus.set_flushing(True)
                self._pipeline.set_state(gst.STATE_NULL)
                self._pipeline = None
                self._decodebin = None
                self._ffmpegcolorspace = None
                self._imgthumbbin = None
                self._videothumbbin = None
                self._plugged_elements = []
        else:
            # reusing decodebin leads to problems
            if self._decodebin is not None:
                self._typefind.unlink(self._decodebin)
                self._decodebin.set_state(gst.STATE_NULL)
                self._pipeline.remove(self._decodebin)
                self._decodebin = None

            # remove dynamically plugged elements
            for element in self._plugged_elements:
                self._pipeline.remove(element)
                element.set_state(gst.STATE_NULL)
            self._plugged_elements = []

    def _build_pipeline(self):
        self._pipeline = gst.Pipeline()
        self._bus = self._pipeline.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect('message::application',
                self._bus_message_application_cb)
        self._bus.connect('message::error', self._bus_message_error_cb)
        self._bus.connect('message::eos', self._bus_message_eos_cb)
        self._bus.connect('message::tag', self._bus_message_tag_cb)
        self._bus.connect('message::state-changed',
                self._bus_message_state_changed_cb)
        self._src = None
        self._typefind = gst.element_factory_make('typefind')
        self._typefind.connect('have-type', self._typefind_have_type_cb)
        pad = self._typefind.get_pad('src')
        self._pipeline.add(self._typefind)

        self._pipeline.set_state(gst.STATE_READY)

    def _reset(self):
        # NOTE: we call gst_element_set_state so we MUST NOT be called from the
        # streaming thread

        # destroy the current pipeline if reuse_elements == False, otherwise
        # clean it so that it can be reused
        self._clean_pipeline()
        if self._pipeline is None:
            # we're either being called from initialize() or
            # self.reuse_elements == False
            self._build_pipeline()

        # the metadata dictionary of the current request
        self._req_metadata = None
        # the uri value in the metadata dictionary
        self._req_uri = None
        # the deferred that we callback when we finish loading stuff in
        # self._req_metadata
        self._req_callback = None

        # the caps as given by the typefind::have-type signal
        self._typefind_caps = None
        self._typefind_file_type = None
        self._typefind_mime_type = None

        # the video/audio/image caps that we get from decodebin pads when
        # we plug decodebin
        self._video_caps = None
        self._audio_caps = None
        self._image_caps = None

        # the taglist containing all the tags for the stream
        self._tags = gst.TagList()

        # the duration of the current stream, used to seek when doing a
        # thumbnail
        self._duration = None
        self._seek_status = None
        self._seek_location_index = 0
        self._seek_call = None

        self._timeout_call = None

        # timestamps used for logging purposes
        self._start_timestamp = 0
        self._end_timestamp = 0

    def _bus_message_error_cb(self, bus, message):
        gerror, debug = message.parse_error()
        if self._typefind_file_type is not None or \
                self._video_caps is not None or \
                self._audio_caps is not None or \
                self._image_caps is not None:
            # we got an error going to PAUSED but we still can report the info
            # that we got from have_type_cb
            self.debug('error going to paused %s: %s', gerror.message, debug)
            self._clean_thumbnail()
            self._done()
        else:
            self._failed(GstMetadataError('error'
                    ' domain: %r code: %r message: %s debug: %s' %
                    (gerror.domain, gerror.code, gerror.message, debug)))

    def _bus_message_application_cb(self, bus, message):
        if message.structure.get_name() == 'metadata-done':
            self._done()
            return

    def _bus_message_eos_cb(self, bus, message):
        self.log('got EOS')

        self._done()

    def _bus_message_tag_cb(self, bus, message):
        taglist = message.parse_tag()
        self._tags = self._tags.merge(taglist, gst.TAG_MERGE_APPEND)

    def _bus_message_state_changed_cb(self, bus, message):
        if message.src is not self._pipeline:
            return

        prev, current, pending = message.parse_state_changed()
        if prev == gst.STATE_READY and current == gst.STATE_PAUSED and \
                self._decodebin is not None and \
                self._decodebin.get_pad('sink').is_linked():
            self.debug('reached PAUSED')

            if self._video_caps is None and self._image_caps is None and \
                self._typefind_file_type not in ('video', 'image'):
                # we have the tags at this point
                self._done()

    def _typefind_have_type_cb(self, typefind, probability, caps):
        self.debug('have type %s' % caps)

        # self._typefind_caps = caps is broken, bug in the bindings
        # FIXME: fix the bug and change this asap
        self._typefind_caps = caps.copy()
        gst_mime_type = self._typefind_mime_type = self._typefind_caps[0].get_name()
        file_type = self._typefind_file_type = gst_mime_type.split('/')[0]

        # NB: id3 tags most of the time are used with mp3 (even if it isn't
        # uncommon to find them with AIFF or WAV). Given that mp3 is by far the
        # most used audio format at the moment we make the common case fast here
        # by assuming that the file_type is audio. By doing this we also set the
        # mime_type to application/x-id3, but this doesn't matter at the moment
        # since we don't use the mime_type anywhere.
        if gst_mime_type == 'application/x-id3':
            file_type = self._typefind_file_type = 'audio'
        elif gst_mime_type == 'audio/x-m4a':
            # FIXME: see http://bugzilla.gnome.org/show_bug.cgi?id=340375 and use this
            # hack until we write our typefinder for this
            file_type = None

        req_keys = set(self._req_metadata.keys())
        if (req_keys == media_type_keys and \
                file_type in ('video', 'audio', 'image'))or \
                (file_type in ('video', 'image') and \
                (not 'thumbnail' in req_keys or self._have_thumbnail())):
            self.debug('got media_type for %s, NOT going to paused',
                    self._req_uri)
            # we are in the streaming thread so we post a message on the bus
            # here and when we read it from the main thread we call _done()
            structure = gst.Structure('metadata-done')
            self._bus.post(gst.message_new_application(self._pipeline, structure))
            return

        # we need tags and/or a thumbnail
        self.debug('we need to go to PAUSED, plugging decodebin '
                '(file_type: %s)' % file_type)
        self._plug_decodebin()

    def _plug_decodebin(self):
        if self._decodebin is None:
            self._decodebin = gst.element_factory_make('decodebin')
            self._decodebin.connect('new-decoded-pad',
                    self._decodebin_new_decoded_pad_cb)
            self._decodebin.connect('unknown-type',
                    self._decodebin_unknown_type_cb)
            self._pipeline.add(self._decodebin)

        self._typefind.link(self._decodebin)
        pad = self._typefind.get_pad('src')
        self._decodebin.set_state(gst.STATE_PAUSED)

    def _check_thumbnail_directory(self):
        if not os.path.exists(THUMBNAIL_DIR):
            try:
                os.makedirs(THUMBNAIL_DIR, 0700)
            except OSError, e:
                msg = "Could not make directory %r: %s. Thumbnail not saved." % (directory, e)
                self.warning(msg)
                raise ThumbnailError(self._req_uri, msg)

    def _boring_cb(self, obj, buffer):
        self.debug('boring buffer')
        self._seek_next_thumbnail_location()

    def _plug_video_thumbnailbin(self, video_pad):
        self.debug('pluging video thumbbin')

        self._check_thumbnail_directory()

        if self._videothumbbin is None:
            self._videothumbbin = PngVideoSnapshotBin()
            self._videothumbbin.connect('boring', self._boring_cb)
            self._pipeline.add(self._videothumbbin)

        thumbbin = self._videothumbbin

        filesink = gst.element_factory_make('filesink')
        self._pipeline.add(filesink)
        filesink.props.location = get_thumbnail_location(self._req_uri)

        video_pad.link(thumbbin.get_pad('sink'))
        thumbbin.get_pad('src').link(filesink.get_pad('sink'))

        thumbbin.set_state(gst.STATE_PAUSED)
        filesink.set_state(gst.STATE_PAUSED)

        self._plugged_elements.append(filesink)
        self.debug('video thumbbin plugged')

    def _plug_image_thumbnailbin(self, image_pad):
        self.debug('plugging image thumbbin')

        self._check_thumbnail_directory()

        if self._imgthumbbin is None:
        # we can't register the element on old gst-python versions so we can't
        # use gst_element_factory_make
        #    self._imgthumbbin = gst.element_factory_make('pngimagesnapshot')
            self._imgthumbbin = PngImageSnapshotBin()
            self._pipeline.add(self._imgthumbbin)
        thumbbin = self._imgthumbbin

        filesink = gst.element_factory_make('filesink')
        self._pipeline.add(filesink)
        filesink.props.location = get_thumbnail_location(self._req_uri)

        image_pad.link(thumbbin.get_pad('sink'))
        thumbbin.get_pad('src').link(filesink.get_pad('sink'))

        thumbbin.set_state(gst.STATE_PAUSED)
        filesink.set_state(gst.STATE_PAUSED)

        self._plugged_elements.append(filesink)
        self.debug('image thumbbin plugged')

    #def _have_thumbnail(self):
    #    location = get_thumbnail_location(self._req_uri)
    #    if os.path.exists(location):
    #        stat = os.stat(location)
    #        if stat.st_size != 0:
    #            return True

    #    return False

    def _find_decoder(self, pad):
        target = pad.get_target()
        element = target.get_parent()
        klass = element.get_factory().get_klass()
        if 'Decoder' in klass:
            return element
        return None

    def _get_type_from_decoder(self, decoder):
        klass = decoder.get_factory().get_klass()
        parts = klass.split('/', 2)
        if len(parts) != 3:
            return None

        return parts[2].lower()

    def _seek_next_thumbnail_location(self):
        self._seek_status = SEEK_SCHEDULED

        #self._seek_call = \
        #    reactor.callLater(0, self._seek_next_thumbnail_location_real)

    def _seek_next_thumbnail_location_real(self):
        self._seek_call = None
        self._seek_status = SEEK_DONE

        if self._duration is None:
            # first seek, get the duration
            try:
                self._duration, format = self._pipeline.query_duration(gst.FORMAT_TIME)
            except gst.QueryError, e:
                self.debug('duration query failed: %s', e)

                return

            if self._duration == -1:
                self.debug('invalid duration, not seeking')
                return

            self.debug('stream duration %s' % self._duration)

        if self._seek_location_index == len(self._frame_locations):
            self.debug('no more seek locations')
            return self._failed(ThumbnailError('no more seek locations'))

        location = self._frame_locations[self._seek_location_index]
        self.debug('seek to location %d, time %s duration %s' %
                (self._seek_location_index,
                gst.TIME_ARGS(int(location * self._duration)),
                gst.TIME_ARGS(self._duration)))
        self._seek_location_index += 1

        res = self._pipeline.seek(1.0, gst.FORMAT_TIME,
                gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_KEY_UNIT,
                gst.SEEK_TYPE_SET, int(location * self._duration),
                gst.SEEK_TYPE_NONE, 0)

        self.debug('seek done res %s' % res)

    def _close_pad(self, pad):
        queue = gst.element_factory_make('queue')
        # set the queue leaky so that if we take some time to do the thumbnail
        # the demuxer doesnt' block on full queues
        queue.props.leaky = 1
        sink = gst.element_factory_make('fakesink')
        self._pipeline.add(queue, sink)
        # add sink before queue so when we iterate over the elements to clean
        # them we clean the sink first and unblock the queue if it's blocked
        # prerolling
        self._plugged_elements.append(sink)
        self._plugged_elements.append(queue)
        pad.link(queue.get_pad('sink'))
        queue.link(sink)
        queue.set_state(gst.STATE_PAUSED)
        sink.set_state(gst.STATE_PAUSED)

    def _get_pad_type(self, pad):
        decoder = self._find_decoder(pad)
        if decoder:
            return self._get_type_from_decoder(decoder)

        return pad.get_caps()[0].get_name().split('/', 1)[0]

    def _get_pad_caps(self, pad):
        decoder = self._find_decoder(pad)
        if decoder:
            return decoder.get_pad('sink').get_caps()

        return pad.get_caps()

    def _decodebin_new_decoded_pad_cb(self, decodebin, pad, is_last):
        self.debug('new decoded pad %s, caps %s, is_last %s' % (pad,
                pad.get_caps(), is_last))

        typ = self._get_pad_type(pad)
        caps = self._get_pad_caps(pad)

        if typ == 'audio':
            if self._audio_caps is None:
                self._audio_caps = caps
        elif typ == 'video':
            if self._video_caps is None:
                self._video_caps = caps
                # do a thumbnail of the first video track
        #        self._plug_video_thumbnailbin(pad)
        elif typ == 'image':
            if self._image_caps is None:
                self._image_caps = caps
        #        self._plug_image_thumbnailbin(pad)

        if not pad.is_linked():
            self._close_pad(pad)

    def _decodebin_unknown_type_cb(self, decodebin, pad, caps):
        self.debug('unknown pad %s, caps %s' % (pad, caps))

    def _plug_src(self, uri):
        src = gst.element_make_from_uri(gst.URI_SRC, str(uri))
        # FIXME: workaround for jpegdec that does a gst_buffer_join for each
        # gst_pad_chain.
        #src.props.blocksize = 3 * 1024 * 1024

        return src

    def get_metadata(self, requested_metadata, callback):
        #assert self._timeout_call is None

        self._req_metadata = requested_metadata
        self._req_uri = requested_metadata['uri']
        #self._req_defer = defer.Deferred()
        self._req_callback = callback

        self.debug('getting metadata %s' % self._req_metadata)

        self._start_timestamp = time.time()

        self._src = self._plug_src(self._req_uri)
        self._pipeline.add(self._src)
        self._src.link(self._typefind)

        #self._timeout_call = reactor.callLater(self.timeout, self._timeout)

        # reset the bus in case this is not the first request
        self._bus.set_flushing(False)
        self._pipeline.set_state(gst.STATE_PLAYING)

        #return self._req_defer

    def _get_media_type_from_caps(self, caps):
        res = {}
        mime_type = caps[0].get_name()
        file_type = mime_type.split('/', 1)[0]

        return {'file_type': file_type, 'mime_type': mime_type}

    def _done(self):
        #if not self._timeout_call.called:
        #    self._timeout_call.cancel()

        # we can't check self._seek_call.called here because we don't know if we
        # scheduled a seek call at all
        #if self._seek_call is not None:
        #    self._seek_call.cancel()
        #    self._seek_call = None

        self._end_timestamp = time.time()

        metadata = self._req_metadata
        metadata_callback = self._req_callback

        available_metadata = {}
        for caps in (self._video_caps, self._audio_caps,
                self._image_caps):
            if caps is not None:
                available_metadata.update(self._get_media_type_from_caps(caps))
                break

        # fallback to typefind caps
        if available_metadata.get('file_type') is None:
            available_metadata['file_type'] = self._typefind_file_type
            available_metadata['mime_type'] = self._typefind_mime_type

        #if available_metadata['file_type'] in ('video', 'image') and \
        #    self._have_thumbnail():
        #    available_metadata['thumbnail'] = \
        #            get_thumbnail_location(self._req_uri)

        tags = self._tags

        try:
            del tags['extended-comment']
        except KeyError:
            pass

        #tag_keys = tags.keys()
        #for gst_key, elisa_key in (('track-number', 'track'),
        #            ('title', 'song')):
        #    try:
        #        available_metadata[elisa_key] = tags[gst_key]
        #    except KeyError:
        #        pass

        #for key in tag_keys:
        #    value = tags[key]
            # FIXME: this was an old assumption, let's keep it until we update
            # all the old code
        #    if isinstance(value, list):
        #        try:
        #            value = value[0]
        #        except IndexError:
        #            continue

        #    available_metadata[key] = value

        for tag_key in tags.keys():
            available_metadata[tag_key] = tags[tag_key]

        #for key, value in available_metadata.iteritems():
        #    try:
        #        if metadata[key] is None:
        #            metadata[key] = value
        #    except KeyError:
        #        pass
        metadata = available_metadata

        self.debug('finished getting metadata %s, elapsed time %s' %
                (metadata, self._end_timestamp - self._start_timestamp))

        self._reset()
        metadata_callback(metadata)

    def _timeout(self, thumb_timeout=False):
        self.debug('timeout thumb %s video caps %s',
                thumb_timeout, self._video_caps)

        if not thumb_timeout and (self._typefind_file_type == 'video' or
                self._video_caps is not None):
            # give some more time to the pipline if we are trying to make a
            # thumbnail
            #self._timeout_call = \
            #    reactor.callLater(self.thumb_timeout, self._timeout, True)
        #else:
            self._clean_thumbnail()

            keys = set(self._req_metadata.keys())
            if keys != thumbnail_keys and \
                    (self._typefind_file_type is not None or \
                    self._video_caps is not None or \
                    self._audio_caps is not None or \
                    self._image_caps is not None):
                # timeout while going to paused. This can happen on really slow
                # machines while doing the thumbnail. Even if we didn't do the
                # thumbnail, we have some clue about the media type here.
                self._done()
            else:
                self._failed(TimeoutError('timeout'))

    def _clean_thumbnail(self):
        # if we fail doing a thumbnail we need to remove the file
        if self._imgthumbbin is not None or self._videothumbbin is not None:
            location = get_thumbnail_location(self._req_uri)
            try:
                os.unlink(location)
            except OSError:
                pass

    def _failed(self, error):
        # cancel delayed calls
        #if not self._timeout_call.called:
        #    self._timeout_call.cancel()

        #if self._seek_call is not None:
        #    self._seek_call.cancel()
        #    self._seek_call = None

        self._end_timestamp = time.time()

        metadata = self._req_metadata
        metadata_callback = self._req_callback
        #self.debug('error getting metadata %s, error: %s, '
        #        'elapsed time: %s, timeout %s' % (metadata, error,
        #        self._end_timestamp - self._start_timestamp,
        #        self._timeout_call.called))
        self.debug('error getting metadata %s, error: %s, '
                'elapsed time: %s' % (metadata, error,
                self._end_timestamp - self._start_timestamp))


        #self._clean_thumbnail()

        self._reset()

        metadata_callback(None)

class GstMetadata:
    def __init__(self):
        self.queue = Queue()
        self.pipeline = GstMetadataPipeline()
        self.pipeline.initialize()

    def get_metadata(self, uri):
        self.pipeline.get_metadata({'uri': 'file://'+os.path.abspath(uri)}, self.queue.put)
        metadata = self.queue.get()
        return metadata
