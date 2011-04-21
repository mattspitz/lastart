import logging
import optparse
import os
import re
import simplejson
import urllib
import urllib2
import xml.dom.minidom

config = simplejson.load(open("config.json", "r"))

parser = optparse.OptionParser()
parser.add_option("-f", "--cover_filename", default="cover.jpg", action="store", help="the filename for the downloaded cover art; defaults to cover.jpg")

(options, args) = parser.parse_args()
album_dir = args[0]

class Album(object):
    def __init__(self, dirpath, artist, title):
        self.dirpath = dirpath
        self.artist = artist if artist is not None else ""
        self.title = title if title is not None else ""

    def __str__(self):
        s = getattr(self, "artist", "")
        if getattr(self, "title", ""):
            s += " - %s" % self.title
        return s

    def formulate_lastfm_query(self):
        return "%s %s" % (self.artist, self.title)

def get_cover_fn(dirpath):
    return os.path.join(dirpath, options.cover_filename)

def collect_albums(album_dir):
    albums = []
    regex = re.compile(config["ALBUM_DIR_REGEX"])
    for dirpath, dirnames, filenames in os.walk(album_dir):
        if os.path.exists(get_cover_fn(dirpath)):
            logging.debug("%s already has a '%s'.  Skipping..." % (dirpath, options.cover_filename))
            continue

        match = regex.match(dirpath)
        if match:
            albums.append(Album(dirpath, match.group("artist"), match.group("title")))
        else:
            logging.debug("%s didn't match.  Skipping..." % dirpath)
    return albums

def get_cover_url(album_query):
    """ Given a query, ask Last.fm for the albums that match that query.
    Return the first album that has an extra large image for the album
    cover.  We assume the response format will look something like this:

    # we assume something like this:
    <results>
        <albums>
            <album>
                <image size="small">http://small/image</image>
                ...
                <image size="extralarge">http://the/image/we/want</image>
            </album>
            <album>
                <image size="small">http://small/image</image>
                ...
                <image size="extralarge">http://we/actually/take/the/first/album's/image</image>
            </album>
            ...
        </albums>
    </results>
    """

    args = {"method": "album.search",
            "api_key": config["API_KEY"],
            "album": album_query}
    url = "http://ws.audioscrobbler.com/2.0/?%s" % urllib.urlencode(args)
    try:
        domStr = urllib2.urlopen(url).read()
        dom = xml.dom.minidom.parseString(domStr)
        for album in dom.getElementsByTagName("album"):
            for image in album.getElementsByTagName("image"):
                if image.getAttribute("size") == "extralarge":
                    return image.childNodes[0].data
    except:
        logging.exception("Error parsing query: %s.  Skipping..." % album_query)
    return None

def pull_cover_url(cover_url, cover_fn):
    logging.debug("Pulling cover_url %s to file %s" % (cover_url, cover_fn))
    try:
        urllib.urlretrieve(cover_url, cover_fn)
    except:
        logging.exception("Couldn't pull cover_url %s to file %s" % (cover_url, cover_fn))

def grab_cover_art(albums):
    for album in albums:
        cover_url = get_cover_url(album.formulate_lastfm_query())
        if cover_url:
            pull_cover_url(cover_url, get_cover_fn(album.dirpath))
        else:
            logging.debug("Couldn't find cover url for %s" % album)

def main():
    albums = collect_albums(album_dir)
    grab_cover_art(albums)

if __name__ == "__main__":
    log_level = logging.DEBUG if os.environ.get("DEBUG") else logging.ERROR
    logging.basicConfig(level=log_level,
                        format="%(asctime)s: %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
    main()