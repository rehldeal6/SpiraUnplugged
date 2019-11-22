import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="zanarkand",
    version="0.1.0",
    author="Jim Rehl",
    author_email="James.D.Rehl@gmail.com",
    description="Software to continuously stream a set of youtube videos and playlists",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rehldeal6/SpiraUnplugged",
    packages=setuptools.find_packages(),
    data_files=[
        ('/opt/zanarkand/fonts', ['agency-fb-bold.ttf']),
        ('/opt/zanarkand/logs', []),
        ('/opt/zanarkand/media', []),
        ('/opt/zanarkand/standby', []),
        ('/opt/zanarkand/resources', []),
        ('/opt/zanarkand', ['zanarkand.py',
                            'config.yml',
                            'current_status.yml']),
        ('/etc/logrotate.d', ['zanarkand.logrotate']),
        ('/lib/systemd/system', ['zanarkand.service'])]
    install_requires=[
        'ffmpeg-python',
        'youtube-dl',
        'PyYAML',
        'psutil',
        'discord-webhook']
    classifiers=[
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=2.7',
)
