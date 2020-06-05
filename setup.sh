#!/bin/bash

mkdir $(pwd)/standby
mkdir $(pwd)/media
mkdir $(pwd)/resources

youtube-dl -f flv https://www.youtube.com/watch?v=r3SpJYsAr0A -o "$(pwd)/standby/standby.flv"
youtube-dl --playlist-items 135 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "$(pwd)/standby/%(title)s"
youtube-dl --playlist-items 136 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "$(pwd)/standby/%(title)s"
youtube-dl --playlist-items 137 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "$(pwd)/standby/%(title)s"
youtube-dl --playlist-items 139 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "$(pwd)/standby/%(title)s"
youtube-dl --playlist-items 140 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "$(pwd)/standby/%(title)s"
youtube-dl --playlist-items 141 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "$(pwd)/standby/%(title)s"
youtube-dl --playlist-items 142 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "$(pwd)/standby/%(title)s"
youtube-dl --playlist-items 143 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "$(pwd)/standby/%(title)s"
youtube-dl --playlist-items 144 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "$(pwd)/standby/%(title)s"
youtube-dl --playlist-items 145 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "$(pwd)/standby/%(title)s"
youtube-dl --playlist-items 151 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "$(pwd)/standby/%(title)s"
youtube-dl --playlist-items 152 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "$(pwd)/standby/%(title)s"
youtube-dl --playlist-items 153 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "$(pwd)/standby/%(title)s"
youtube-dl --playlist-items 154 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "$(pwd)/standby/%(title)s"
youtube-dl --playlist-items 156 https://www.youtube.com/playlist?list=PL9wpzJw8GKy74rLqQv7OH9v94Hj8qQWps -o "$(pwd)/standby/%(title)s"
