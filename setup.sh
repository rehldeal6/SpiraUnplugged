#!/bin/bash

 if [ ! -d $(pwd)/standby ]; then
     mkdir $(pwd)/standby
 fi
 if [ ! -d $(pwd)/media ]; then
     mkdir $(pwd)/media
 fi
 if [ ! -d $(pwd)/resources ]; then
     mkdir $(pwd)/resources
 fi

docker run -v $(pwd)/resources:/media --entrypoint youtube-dlc ytdl https://www.youtube.com/watch?v=QtYienBNUAs -o "/media/standby.%(ext)s"
docker run -v $(pwd)/standby:/media --entrypoint youtube-dlc ytdl --playlist-items 135-137,139-145,151-154,156 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "/media/%(title)s"
