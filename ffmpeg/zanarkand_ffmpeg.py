#! /usr/bin/python3

# Standard Imports
import os
import sys
import logging
from random import choice

# Third Party Imports
import ffmpeg
from discord_webhook import DiscordWebhook

def stream_episode():
    overlay = ffmpeg.input('/resources/overlay.png')\
                    .filter('ass',
                            filename='/resources/final.ass')
    video = ffmpeg.input('/media/{}/{}-E{}.v'.format(os.environ['FFMPEG_PLAYLIST'],
                                                     os.environ['FFMPEG_PLAYLIST'],
                                                     os.environ['FFMPEG_EPISODE']),
                         re=None)\
                  .video\
                  .filter('scale',
                          os.environ['FFMPEG_VIEWPORT_WIDTH'],
                          os.environ['FFMPEG_VIEWPORT_HEIGHT'])\
                  .filter('pad',
                          os.environ['FFMPEG_RESOLUTION_WIDTH'],
                          os.environ['FFMPEG_RESOLUTION_HEIGHT'],
                          os.environ['FFMPEG_VIEWPORT_X'],
                          os.environ['FFMPEG_VIEWPORT_Y'])\
                  .overlay(overlay)
    audio = ffmpeg.input('/media/{}/{}-E{}.a'.format(os.environ['FFMPEG_PLAYLIST'],
                                                     os.environ['FFMPEG_PLAYLIST'],
                                                     os.environ['FFMPEG_EPISODE']),
                         re=None)
    logging.info('Streaming episode %s-E%s', os.environ['FFMPEG_PLAYLIST'], os.environ['FFMPEG_EPISODE'])
    try:
        ffmpeg.output(video,
                      audio,
                      'rtmp://a.rtmp.youtube.com/live2/{}'.format(os.environ['YOUTUBE_KEY']),
                      format=os.environ['FFMPEG_FORMAT'],
                      vcodec=os.environ['FFMPEG_VCODEC'],
                      acodec=os.environ['FFMPEG_ACODEC'],
                      minrate=os.environ['FFMPEG_MINRATE'],
                      maxrate=os.environ['FFMPEG_MAXRATE'],
                      bufsize=os.environ['FFMPEG_BUFSIZE'],
                      crf=os.environ['FFMPEG_CRF'],
                      preset=os.environ['FFMPEG_PRESET'],
                      audio_bitrate=os.environ['FFMPEG_AUDIO_BITRATE'],
                      ar=os.environ['FFMPEG_AR'],
                      g=os.environ['FFMPEG_G'])\
               .run(capture_stdout=False,
                    capture_stderr=True,
                    quiet=True)
    except ffmpeg.Error as err:
        logging.error('Error while streaming %s-E%s', os.environ['FFMPEG_PLAYLIST'], os.environ['FFMPEG_EPISODE'])
        DiscordWebhook(url=os.environ['DISCORD_WEBHOOK'], content=err.stderr.decode('utf-8')[-2000:]).execute()

def stream_standby():
    logging.info("Starting initial standby video")
    try:
        ffmpeg.input('/resources/standby.flv',
                     re=None)\
              .output('rtmp://a.rtmp.youtube.com/live2/{}'.format(os.environ['YOUTUBE_KEY']),
                      format='flv')\
              .run(capture_stdout=False,
                   capture_stderr=True,
                   quiet=True)
    except ffmpeg.Error as err:
        logging.error('Error while streaming the initial standby video')
        DiscordWebhook(url=os.environ['DISCORD_WEBHOOK'], content=err.stderr.decode('utf-8')[-2000:]).execute()

def stream_longer_standby():
    logging.info('Starting longer standby videos')
    while True:
        try:
            media = choice(os.listdir('/standby'))
            logging.info('Starting longer standby video %s', media)
            video_name = os.path.splitext(media)[0]
            video = ffmpeg.input('/standby/' + media, re=None).video\
                          .drawtext(text="The stream is currently on standby, please bear with us while the Al-Bhed Tech Support fixes the issue.",
                                    x="(w-text_w)/2",
                                    y="h-100",
                                    fontcolor="yellow",
                                    fontsize=25,
                                    font="agency-fb-bold",
                                    box=1,
                                    boxcolor="black",
                                    boxborderw=5)\
                          .drawtext(text="Now Playing: {}".format(video_name),
                                    x="(w-text_w)/2",
                                    y="h-50",
                                    fontcolor="yellow",
                                    fontsize=25,
                                    font="agency-fb-bold",
                                    box=1,
                                    boxcolor="black",
                                    boxborderw=5)
            audio = ffmpeg.input('/standby/' + media, re=None).audio
            ffmpeg.output(video,
                       audio,
                       'rtmp://a.rtmp.youtube.com/live2/{}'.format(os.environ['YOUTUBE_KEY']),
                       format=os.environ['FFMPEG_FORMAT'],
                       vcodec=os.environ['FFMPEG_VCODEC'],
                       acodec=os.environ['FFMPEG_ACODEC'],
                       minrate=os.environ['FFMPEG_MINRATE'],
                       maxrate=os.environ['FFMPEG_MAXRATE'],
                       bufsize=os.environ['FFMPEG_BUFSIZE'],
                       crf=os.environ['FFMPEG_CRF'],
                       preset=os.environ['FFMPEG_PRESET'],
                       audio_bitrate=os.environ['FFMPEG_AUDIO_BITRATE'],
                       ar=os.environ['FFMPEG_AR'],
                       g=os.environ['FFMPEG_G'])\
                .run(capture_stdout=False,
                     capture_stderr=True,
                     quiet=True)
        except ffmpeg.Error as err:
            logging.error('Error while streaming longer video %s: %s', video_name, err)
            DiscordWebhook(url=os.environ['DISCORD_WEBHOOK'], content=err.stderr.decode('utf-8')[-2000:]).execute()

def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S')
    required_files = ['/resources/overlay.png',
                      '/resources/standby.flv',
                      '/resources/final.ass',
                      '/resources/standby.flv']
    for f in required_files:
        if not os.path.isfile(f):
            logging.error('File {} does not exist. Exiting'.format(f))
            sys.exit(1)
    if os.environ['STREAM_STANDBY'] == '0':
        stream_episode()
    elif os.environ['STREAM_STANDBY'] == '1':
        stream_standby()
    elif os.environ['STREAM_STANDBY'] == '2':
        stream_longer_standby()

if __name__ == "__main__":
    main()

