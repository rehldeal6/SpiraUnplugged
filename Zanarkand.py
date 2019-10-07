#!/usr/bin/env python
from __future__ import unicode_literals
#TODO: - Check to see if ffmpeg can start a video on a specific timestamp
#      - Add in limited number of yt-dl requests
#      - Add ability to auto-update
#      - Set up proper logging
import os
import sys
import time
import ffmpeg
import pprint
import youtube_dl
from itertools import cycle
from argparse import ArgumentParser
from multiprocessing import Process
from ConfigParser import ConfigParser, SafeConfigParser, NoSectionError, NoOptionError

def get_episode_id(playlist, episode):
    ytdl_options = {"simulate": True,
                    "quiet": True,
                    "playlist_items": str(episode)}
    ytdl = youtube_dl.YoutubeDL(ytdl_options)
    episode_information = ytdl.extract_info("https://www.youtube.com/playlist?list=" + playlist)
    if episode_information['entries']:
        return episode_information['entries'][0]['id']
    else:
        return None

def yt_download_episode(playlist, episode, media_folder):
    print("Downloading episode {}.".format(episode))
    ytdl_options_video = {"format": "bestvideo",
                          "quiet": True,
                          "outtmpl": media_folder + "%(id)s.v",
                          "playlist_items": str(episode)}
    ytdl_v = youtube_dl.YoutubeDL(ytdl_options_video)
    ytdl_v.download(["https://www.youtube.com/playlist?list=" + playlist])
    ytdl_options_audio = {"format": "bestaudio",
                          "quiet": True,
                          "outtmpl": media_folder + "%(id)s.a",
                          "playlist_items": str(episode)}
    ytdl_a = youtube_dl.YoutubeDL(ytdl_options_audio)
    ytdl_a.download(["https://www.youtube.com/playlist?list=" + playlist])
    print("Download of episode {} complete.".format(episode))
    return

def stream_video(episode):
    '''
    '''
    print("Starting stream of episode {}.".format(episode))
    time.sleep(240)
    print("Ending stream of episode {}.".format(episode))
    return

def build_playlist(playlist_file):
    game_dict = {}
    game_list = []
    highest_loop_position = 0

    for s in playlist_file.sections():
        positions = playlist_file.get(s, "LoopPositions")
        for position in positions.split(","):
            position = int(position)
            if position > highest_loop_position:
                highest_loop_position = position
            if position in game_dict:
                #log(LOG_ERR, "Duplicate loop position! {} and {} conflict".format(s, game_dict[position]))
                sys.exit(4)
            else:
                game_dict[position] = s
    for loop_position in xrange(1, highest_loop_position+1):
        if loop_position not in game_dict:
            print("Missing loop position! Position {} not found".format(loop_position))
            #log(LOG_ERR, "Missing loop position! Position {} not found".format(loop_position))
            sys.exit(4)
        game_list.append(game_dict[loop_position])
    return game_list

def main():
    parser = ArgumentParser()
    parser.add_argument("-c", "--config", help="Main configuration file location", default="/etc/zanarkand/zanarkand.conf")
    args = parser.parse_args()

    zanarkand_defaults = {"FfmpegPreset": "superfast",
                          "FfmpegCrf": 18,
                          "FfmpegMinrate": "5000K",
                          "FfmpegMaxrate": "6000K",
                          "FfmpegBufsize": "12000K",
                          "Resolution": 1080,
                          "ViewportWidth": 1760,
                          "ViewportHeight": 990,
                          "ViewportX": 0,
                          "ViewportY": 90,
                          "OverlayImage": "/home/Zanarkand/resources/1080overlay.png",
                          "PlaylistsFile": "/etc/zanarkand/playlist.conf",
                          "CurrentStatusFile": "/etc/Zanarkand/current_status.txt",
                          "DefaultVideoID": "default",
                          "LogFile": "/home/rehlj/ZanarkandPt2/test_log.log",
                          "MediaFolder": "/home/rehlj/ZanarkandPt2/media",
                          "NumberOfDownloads": 3}

    zanarkand_config = SafeConfigParser(zanarkand_defaults)
    try:
        zanarkand_config.read(args.config)
        #TODO - make this fail an check exception type
    except Exception as e:
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

    # ffmpeg Defaults
    ffmpeg_preset = zanarkand_config.get("ffmpeg", "FfmpegPreset")
    ffmpeg_crf = zanarkand_config.get("ffmpeg", "FfmpegCrf")
    ffmpeg_min_rate = zanarkand_config.get("ffmpeg", "FfmpegMinrate")
    ffmpeg_max_rate = zanarkand_config.get("ffmpeg", "FfmpegMaxrate")
    ffmpeg_buffer_size = zanarkand_config.get("ffmpeg", "FfmpegBufsize")
    ffmpeg_resolution = zanarkand_config.get("ffmpeg", "Resolution")
    ffmpeg_viewport_width = zanarkand_config.get("ffmpeg", "ViewportWidth")
    ffmpeg_viewport_height = zanarkand_config.get("ffmpeg", "ViewportHeight")
    ffmpeg_viewport_x = zanarkand_config.get("ffmpeg", "ViewportX")
    ffmpeg_viewport_y = zanarkand_config.get("ffmpeg", "ViewportY")
    ffmpeg_overlay = zanarkand_config.get("ffmpeg", "OverlayImage")

    # Stream Config
    playlists = zanarkand_config.get("Zanarkand", "PlaylistsFile")
    current_status = zanarkand_config.get("Zanarkand", "CurrentStatusFile")
    default_video_id = zanarkand_config.get("Zanarkand", "DefaultVideoID")
    log_destination = zanarkand_config.get("Zanarkand", "LogFile")
    media_folder = zanarkand_config.get("Zanarkand", "MediaFolder")
    number_of_downloads = zanarkand_config.getint("Zanarkand", "NumberOfDownloads")

    media_folder = media_folder + "/" if not media_folder.endswith('/') else media_folder
    if not os.path.exists(media_folder):
        print("Media folder ({}) not found.".format(media_folder))

    # Check existance of files
    config_files = [ffmpeg_overlay, playlists, default_video_id + ".v", default_video_id + ".a"]
    found_files = True
    for f in config_files: 
        if not os.path.exists(f):
            print("File {} not found".format(f))
            #log(LOG_ERR, "File {} not found".format(f))
            found_files = False
    if not found_files:
        sys.exit(3)

    # Get games list
    games_configs = SafeConfigParser()
    try:
        games_configs.read(playlists)
    except Exception as e:
        print("Could not open configuration file {}: {}".format(playlists, e))
        #log(LOG_ERR, "Could not open configuration file {}".format(args.config))
        sys.exit(1)

    playlist_games = build_playlist(games_configs)
    #pprint.pprint(playlist_games)

    # Get current video, or make the file if it doesn't exist
    if not os.path.exists(current_status):
        with open(current_status, "w") as f:
            f.write("[current]\n")
            f.write("Game: {}\n".format(playlist_games[0]))
            f.write("Episode: 1\n")
            f.write("Loop: 1\n")
            f.write("Position: 1\n")
        game = playlist_games[0]
        episode = 1
        loop = 1
        position = 1
    else:
        current_video = ConfigParser()
        try:
            current_video.read(current_status)
            game = current_video.get("current", "Game")
            episode = current_video.getint("current", "Episode")
            loop = current_video.getint("current", "Loop")
            position = current_video.getint("current", "Position")
        except Exception as e:
            print("Could not read from current status: {}".format(e))
    
    # Get current game and positon
    game_cycle = cycle(playlist_games)
    for _ in xrange(position):
        current_game = game_cycle.next()
    
    print "Current Game: {}".format(current_game)
    print "Current Episode: {}".format(episode)
    print "Current Loop: {}".format(loop)
    print "Current Position: {}".format(position)

    episode_id = ""
    playlist = games_configs.get(current_game, "Playlist")

    while current_game:
        #Update current config
        current_video.set("current", "Game", game)
        current_video.set("current", "Episode", str(episode))
        current_video.set("current", "Loop", str(loop))
        current_video.set("current", "Position", str(position))
        with open(current_status, 'w') as f:
            current_video.write(f)

        if not episode_id:
            episode_id = get_episode_id(playlist, episode)
        if not os.path.exists(media_folder + episode_id + ".v") or not os.path.exists(media_folder + episode_id + ".a"):
            default_stream = Process(target=stream_video, args=(default_video_id,))
            default_stream.start()
            download_episode = Process(target=yt_download_episode, args=(playlist, episode, media_folder,))
            download_episode.start()
            download_episode.join()
            default_stream.terminate()
        streaming = Process(target=stream_video, args=(episode_id,))
        streaming.start()

        # Download next N episodes
        i = 1
        download_playlist = playlist
        download_episode_number = episode
        next_episode_id = ""
        while i <= number_of_downloads:
            download_episode_number = download_episode_number + 1
            download_episode_id = get_episode_id(download_playlist, download_episode_number)
            if not download_episode_id:
                if i == 1:
                    print("Current loop: {} | Number of loops: {}.".format(loop, games_configs.get(current_game, "NumberOfLoops")))
                    if loop == int(games_configs.get(current_game, "NumberOfLoops")):
                        print("Switching to next game")
                        current_game = game_cycle.next()
                        download_playlist = games_configs.get(current_game, "Playlist")
                        loop = 1
                        position = playlist_games.index(current_game) + 1
                    else:
                        loop += 1
                    episode = 0
                    download_episode_number = 0
                else:
                    if loop == games_configs.get(current_game, "NumberOfLoops"):
                        download_playlist = games_configs.get(playlist_games[(playlist_games.index(current_game) + 1) % len(playlist_games)], "Playlist") 
                    download_episode_number = 0
            else:
                if i == 1:
                    next_episode_id = download_episode_id
                if not os.path.exists(media_folder + download_episode_id + ".v") or not os.path.exists(media_folder + download_episode_id + ".a"):
                    download_episode_process = Process(target=yt_download_episode, args=(playlist, download_episode_number, media_folder,))
                    download_episode_process.start()
                i += 1

        # Wait until Stream ends
        streaming.join()

        # Remove file
        try:
            os.remove(media_folder + episode_id + ".v")
            os.remove(media_folder + episode_id + ".a")
        except OSError as e:
            print("Could not remove the media files for {}: {}".format(episode_id, e))

        # Set up for next episode
        episode = episode + 1
        episode_id = next_episode_id


if __name__ == "__main__":
    main()
