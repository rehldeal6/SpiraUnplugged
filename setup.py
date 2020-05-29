#!/usr/bin/python3

from setuptools import setup

setup(name='zanarkand',
      version='1.0',
      description='Dansg08 Zanarkand Stream that never sleeps!',
      author='Jim Rehl',
      author_email='rehldeal6@gmail.com',
      url='https://github.com/rehldeal6/SpiraUnplugged',
      scripts=['zanarkand.py'],
      install_requires=[
          "discord-webhook",
          "ffmpeg-python",
          "psutil",
          "youtube-dl",
          "PyYAML"
      ],
      classifiers=[
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Games/Entertainment',
    ]
     )
