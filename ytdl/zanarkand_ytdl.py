#! /usr/bin/python3

# Standard Imports
import os
import sys
import logging

# Third Party Imports
import youtube_dl
from discord_webhook import DiscordWebhook

def download_episode():
    ytdl_options = {'quiet': True,
                    'cachedir': False,
                    'ratelimit': 6291456}
    if os.environ['YTDL_TYPE'] == 'PLAYLIST':
        ytdl_options['playlist_items'] = os.environ['YTDL_EPISODE']
        download_url = 'https://www.youtube.com/playlist?list={}'.format(os.environ['YTDL_URL'])
    elif os.environ['YTDL_TYPE'] == 'VIDEO':
        download_url = 'https://www.youtube.com/watch?v={}'.format(os.environ['YTDL_URL'])
    for extension in ['v', 'a']:
        filename = '/media/{}-E{}.{}'.format(os.environ['YTDL_PLAYLIST'],
                                             os.environ['YTDL_EPISODE'],
                                             extension)
        ytdl_options['outtmpl'] = filename
        if os.path.exists('{}.part'.format(filename)):
            logging.warning('%s is partially downloaded. Removing', filename)
            try:
                os.remove('{}.part'.format(filename))
            except OSError as err:
                logging.error('Could not remove %s.part: %s', filename, err)
        logging.info('Downloading %s', filename)
        if not os.path.exists(filename):
            if extension == 'v':
                ytdl_options['format'] = os.environ.get('YTDL_VIDEOID', 'bestvideo')
            elif extension == 'a':
                ytdl_options['format'] = os.environ.get('YTDL_AUDIOID', 'bestaudio')
            ytdl = youtube_dl.YoutubeDL(ytdl_options)
            ytdl.download([download_url])
        if not os.path.exists(filename):
            DiscordWebhook(url=os.environ['DISCORD_WEBHOOK'], content="Could not download {}!".format(filename)).execute()

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S')
    logging.info("Starting ytdl...")
    download_episode()

if __name__ == "__main__":
    main()

