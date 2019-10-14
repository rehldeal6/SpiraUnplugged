#!/usr/bin/env python
from __future__ import unicode_literals
#TODO: - Check to see if ffmpeg can start a video on a specific timestamp
#      - Add in limited number of yt-dl requests
#      - Add ability to auto-update

import os
import sys
import time
import ffmpeg
import youtube_dl
from argparse import ArgumentParser
from multiprocessing import Process
from ConfigParser import ConfigParser, SafeConfigParser, NoSectionError, NoOptionError, ParsingError

class Game:
    def __init__(self, config, name):
        self.name = name
        self.playlist_id = config.get(name, "PlaylistID")
        self.loops = config.getint(name, "NumberOfLoops")
        ydl = youtube_dl.YoutubeDL({'extract_flat': True, 'quiet': True})
        playlist_information = ydl.extract_info("https://www.youtube.com/playlist?list={}".format(self.playlist_id), download=False)
        self.total_episodes = len(playlist_information['entries'])

class Stream:
    def __init__(self, config):
        self.game = None
        self.next_game = None
        self.episode = None
        self.loop = None
        self.position = None
        self.playlist_file = config

        try:
            self.playlist = dict(config._sections['Order'])
            del self.playlist['__name__']
        except KeyError:
            print("There's no 'Order' section in the playlist file.")
            sys.exit(4)
        
        self.number_of_games = len(self.playlist.keys())

    def update_status(self, status_conf):
        self.game = Game(self.playlist_file, status_conf.get("current", "Game", "FF7"))
        self.episode = status_conf.getint("current", "Episode") if status_conf.has_option("current", "Episode") else 1
        self.loop = status_conf.getint("current", "Loop") if status_conf.has_option("current", "Loop") else 1
        self.position = status_conf.getint("current", "Position") if status_conf.has_option("current", "Position") else 1
        return

    def next(self):
        if self.episode < self.game.total_episodes:
            self.episode += 1
        else:
            self.episode = 1
            if self.loop == self.game.loops:
                self.game = self.next_game
                self.loop = 1
                if self.position == self.number_of_games:
                    self.position = 1
                else:
                    self.position += 1
            else:
                self.loop += 1
        return

    def get_next_game_name(self):
        if self.position == self.number_of_games:
            return self.playlist['1']
        return self.playlist[str(self.position + 1)]

    def get_next_n_episodes(self, n):
        list_of_episodes = []
        for i in xrange(1, n+1):
            download_episode = self.episode + i
            if download_episode > self.game.total_episodes:
                download_episode = download_episode % self.game.total_episodes
                if not self.next_game or (self.next_game.name != self.get_next_game_name()):
                    self.next_game = Game(self.playlist_file, self.get_next_game_name())
                if self.loop == self.game.loops:
                    list_of_episodes.append((self.next_game.name, self.next_game.playlist_id, download_episode))
                else:
                    list_of_episodes.append((self.game.name, self.game.playlist_id, download_episode))
            else:
                list_of_episodes.append((self.game.name, self.game.playlist_id, download_episode))
        return list_of_episodes

    def current_video_exists(self, media_folder):
        if not os.path.exists("{}{}-E{}.v".format(media_folder, self.game.name, self.episode)) or not os.path.exists("{}{}-E{}.v".format(media_folder, self.game.name, self.episode)):
            return False
        return True


def yt_download_episode(playlist, game, episode, media_folder):
    if youtube_dl.utils.ytdl_is_updateable():
        print("Please update youtube-dl!")
        return
    print("Downloading {}-E{}.".format(game, episode))
    ytdl_options_video = {"format": "bestvideo",
                          "quiet": True,
                          "outtmpl": media_folder + "{}-E{}.v".format(game, episode),
                          "playlist_items": str(episode)}
    ytdl_v = youtube_dl.YoutubeDL(ytdl_options_video)
    ytdl_v.download(["https://www.youtube.com/playlist?list=" + playlist])
    ytdl_options_audio = {"format": "bestaudio",
                          "quiet": True,
                          "outtmpl": media_folder + "{}-E{}.a".format(game, episode),
                          "playlist_items": str(episode)}
    ytdl_a = youtube_dl.YoutubeDL(ytdl_options_audio)
    ytdl_a.download(["https://www.youtube.com/playlist?list=" + playlist])
    print("Download of {}-E{} complete.".format(game, episode))
    return

def stream_video(game_name, episode_number):
    '''
    '''
    print("Starting stream of episode {}-E{}.".format(game_name, episode_number))
    time.sleep(360)
    print("Ending stream of episode {}-E{}.".format(game_name, episode_number))
    return

def video_files_exist(media_folder, game_name, episode_number):
    return os.path.exists("{}{}-E{}.v".format(media_folder, game_name, episode_number)) and os.path.exists("{}{}-E{}.a".format(media_folder, game_name, episode_number))

def main():
    parser = ArgumentParser()
    parser.add_argument("-c", "--config", help="Main configuration file location", default="/etc/zanarkand/zanarkand.conf")
    args = parser.parse_args()

    zanarkand_defaults = {"PlaylistsFile": "/etc/zanarkand/playlist.conf",
                          "CurrentStatusFile": "/etc/Zanarkand/current_status.txt",
                          "DefaultVideoID": "default",
                          "LogFile": "/home/rehlj/ZanarkandPt2/test_log.log",
                          "MediaFolder": "/home/rehlj/ZanarkandPt2/media",
                          "NumberOfDownloads": 3}

    zanarkand_config = SafeConfigParser(zanarkand_defaults)
    try:
        zanarkand_config.read(args.config)
    except ParsingError as e:
        print("Could not open configuration file {}: {}".format(args.config, e))
        #log(LOG_ERR, "Could not open configuration file {}".format(args.config))
        sys.exit(1)
    # Youtube Key
    try:
        zanarkand_config.get("youtube", "StreamKey")
    except NoSectionError, NoOptionError:
        print("No streamkey found. Needs to be in the {} file under a section named \"youtube\" with an option named \"StreamKey\"".format(args.config))
        #log(LOG_ERR, "No streamkey found. Needs to be in the {} file under a section named \"youtube\" with an option named \"StreamKey\"".format(args.config))
        sys.exit(2)

    # Stream Config
    playlists = zanarkand_config.get("Zanarkand", "PlaylistsFile")
    current_status = zanarkand_config.get("Zanarkand", "CurrentStatusFile")
    log_destination = zanarkand_config.get("Zanarkand", "LogFile")
    media_folder = zanarkand_config.get("Zanarkand", "MediaFolder")
    number_of_downloads = zanarkand_config.getint("Zanarkand", "NumberOfDownloads")

    ### TODO: Set up logging

    #Check media folder
    media_folder = media_folder + "/" if not media_folder.endswith('/') else media_folder
    if not os.path.exists(media_folder):
        print("Media folder ({}) not found.".format(media_folder))
        sys.exit(3)

    # Check of status file
    if not os.path.exists(current_status):
        print("Current status not found not found")
        #log(LOG_ERR, "File {} not found".format(f))

    # Get games list
    games_configs = SafeConfigParser()
    try:
        games_configs.read(playlists)
    except ParsingError as e:
        print("Could not parse configuration file {}: {}".format(playlists, e))
        #log(LOG_ERR, "Could not open configuration file {}".format(args.config))
        sys.exit(1)
    

    current_video = SafeConfigParser()
    try:
        current_video.read(current_status)
    except ParsingError as e:
        print("Could not parse configuration file {}: {}".format(playlists, e))
        #log(LOG_ERR, "Could not open configuration file {}".format(args.config))
        sys.exit(1)

    stream = Stream(games_configs)
    stream.update_status(current_video)

    while True:
        #Update current config
        current_video.set("current", "Game", stream.game.name)
        current_video.set("current", "Episode", str(stream.episode))
        current_video.set("current", "Loop", str(stream.loop))
        current_video.set("current", "Position", str(stream.position))
        with open(current_status, 'w') as f:
            current_video.write(f)
        
        if not video_files_exist(media_folder, stream.game.name, stream.episode):
            default_stream = Process(target=stream_video, args=("default", 0))
            default_stream.start()
            download_episode = Process(target=yt_download_episode, args=(stream.game.playlist_id, stream.game.name, stream.episode, media_folder,))
            download_episode.start()
            download_episode.join()
            default_stream.terminate()
        streaming = Process(target=stream_video, args=(stream.game.name, stream.episode,))
        streaming.start()

        # Download next N episodes
        for download_game, download_playlist, download_episode in stream.get_next_n_episodes(number_of_downloads):
            if not video_files_exist(media_folder, download_game, download_episode):
                download = Process(target=yt_download_episode, args=(download_playlist, download_game, download_episode, media_folder,))
                download.start()

        # Wait until Stream ends
        streaming.join()

        # Remove file
        try:
            os.remove(media_folder + "{}-E{}.v".format(stream.game.name, stream.episode))
            os.remove(media_folder + "{}-E{}.a".format(stream.game.name, stream.episode))
        except OSError as e:
            print("Could not remove the media files for {}-E{}: {}".format(stream.game.name, stream.episode, e))

        # Set up for next episode
        stream.next()

if __name__ == "__main__":
    main()
