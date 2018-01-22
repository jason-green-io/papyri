# papyri version 0.1

Papyri is a Minecraft map item web presenter. It will show all maps created on a server positioned and scaled properly, creating a mosaic of your world as explored with maps. Since Many maps can be created of the same area, Papyri will prioritize rendering in this order, *1.* being the top layer:

1. maps at zoom level 0, rendered oldest to newest
2. maps	at zoom level 1, rendered oldest to newest
3. maps	at zoom level 2, rendered oldest to newest
4. maps	at zoom level 3, rendered oldest to newest
5. maps	at zoom level 4, rendered oldest to newest

So maps with higher detail are rendered on top of maps of lower detail and maps at the same detail are rendered in order from oldest updated to newest updated.

[Example 1 - Barlynaland](http://minecraft.greener.ca/#!/barlynaland/papyri/)

[Example 2 - various YouTuber server maps](http://jason.green.io/static)

![screen shot 2018-01-12 at 9 35 04 pm](https://user-images.githubusercontent.com/2853489/34902012-feb1c496-f7e0-11e7-871e-e1a79f971295.png)

## prerequisites

python3 and pip (pip3) (Not tested in python2)

You'll need to install http://jcupitt.github.io/libvips/

to do this on Mac OS X:

    brew install vips

Ubuntu should be:

    apt-get install libvips glib2.0-dev

some python stuff you'll need:

    pip3 install nbt Pillow requests pyvips

and you'll need *minecraftmap*; I've put in a pull request for the official one to fix maps in 1.12, I'm hoping to just pull this from pypi eventaully, but for now use this fork:

    git clone https://github.com/jason-green-io/minecraftmap

then, inside the new *minecraftmap* folder

    python setup.py build
    python setup.py install

## usage

type `./papyri.py -h` for help

Once it's done, the contents of the output folder can be served as a website. It's completely static so it can but put in an S3 bucket a github project or hosted locally on your machine by running something like `python3 -m SimpleHTTPServer` inside the output folder.


## Credits

POI web front end by: http://dynalon.github.io/mdwiki/#!index.md
(this can actually be used as full fledged wiki with markdown files, pretty cool)

Font provided by: http://www.04.jp.org

DZI viewer provided by: https://github.com/davidmcclure/osd-dzi-viewer and https://openseadragon.github.io

minecraftmap map item framework by: https://github.com/spookymushroom/minecraftmap
