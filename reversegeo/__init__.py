import logging
import Flickr.API
import Geohash
import sqlite3

try:
    import json
except Exception, e:
    import simplejson as json

class woeid:

    def __init__(self, **kwargs):

        self.flickr_api = Flickr.API.API(kwargs['flickr_apikey'], None)
        self.cache = None

        if kwargs.get('flickr_cache_db', False):
            self.cache = sqlite3.connect(kwargs['flickr_cache_db'])

    def reverse_geocode(self, lat, lon, force=False):

        logging.debug("reverse geocode %s,%s" % (lat, lon))

        cache_key = self.generate_cache_key(lat, lon)

        if not force:
            cache = self.cache_fetch(cache_key)

            if cache:
                if not self.is_valid_woeid(cache):
                    return None

                logging.debug("return from cache for key %s" % cache_key)
                return cache

        # Okay, talk to Flickr...

        args = { 'lat':lat, 'lon':lon, 'format':'json', 'nojsoncallback':1}

        try:
            rsp = self.flickr_api.execute_method(method='flickr.places.findByLatLon', args=args)
            data = json.loads(rsp.read())
        except Exception, e:
            logging.error("failed to reverse geocode: %s" % e)
            return None

        stat = data.get('stat', False)

        if stat != 'ok':
            logging.warning("reverse geocoding failed")
            return None

        try:

            if data['places']['total'] == 0:
                logging.debug("no results for reverse geocoding, caching as empty")
                self.cache_set(cache_key, -1)

            woeid = data['places']['place'][0]['woeid']
        except Exception, e:
            logging.error("failed to parse Flickr response: %s" % e)
            return None

        self.cache_set(cache_key, woeid)

        logging.debug("return WOEID %s" % woeid)
        return woeid

    def is_valid_woeid(self, woeid):

        if not woeid:
            return False

        if woeid < 1:
            return False

        return True

    def generate_cache_key(self, lat, lon):
        return Geohash.encode(lat, lon)

    def cache_set(self, geohash, woeid):

        if not self.cache:
            return False

        db = self.cache.cursor()

        try:
            db.execute("""INSERT INTO reversegeo (geohash, woeid) VALUES(?,?)""", (geohash, woeid))
            self.cache.commit()
        except Exception, e:
            logging.debug("failed to store cache data for %s: %s" % (key, e))
            return False

        return True

    def cache_fetch(self, geohash):

        if not self.cache:
            return None

        db = self.cache.cursor()
        db.execute("SELECT woeid FROM reversegeo WHERE geohash='%s'" % geohash)

        row = db.fetchone()

        if not row:
            return None

        return row[0]

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    import optparse

    parser = optparse.OptionParser()
    parser.add_option("-A", "--api-key", dest="apikey", help="A valid Flickr API key")
    parser.add_option("-l", "--lat-lon", dest="latlon", help="A comma-separated lat,lon pair")
    parser.add_option("-c", "--cache", dest="cache", help="The path to a (sqlite3) Where On Earth (WOE) reverse geocoding DB")
    parser.add_option("-f", "--force", dest="force", help="Force requests to Flickr", default=False, action='store_true')

    (opts, args) = parser.parse_args()

    # apikey = '50f8fe2a13c12d48ec4dfb1dc1f15cc8'
    # cache='../woeid.db'

    lat, lon = map(float, opts.latlon.split(','))

    geo = woeid(flickr_apikey=opts.apikey, flickr_cache_db=opts.cache)
    woeid = geo.reverse_geocode(lat, lon, opts.force)

    print woeid
