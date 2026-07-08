import requests
import shutil
import socket
import time
import json
import os
from test_helper import ApiTestCase

class TestGeoIP(ApiTestCase):
    def setUp(self):
        super(TestGeoIP, self).setUp()
        
    def test_geoIP(self):
        # don't allow IPs from Japan (arbitrary)
        r = self.allowFunc('baddie', '112.78.112.20', "1234")
        j = r.json()
        self.assertEqual(j['status'], -1)
        self.assertRegex(json.dumps(j), "Japan")
        r.close()

    def test_geoIP2City(self):
        attrs = dict()
        attrs['ip'] = '128.243.1.1'
        r = self.customFuncWithName("geoip2", attrs)
        j = r.json()
        self.assertRegex(json.dumps(j), "Nottingham")
        r.close()

    def test_geoIP2LookupVals(self):
        attrs = dict()
        attrs['ip'] = '128.243.21.1'
        r = self.customFuncWithName("geoip2_lookupValue", attrs)
        j = r.json()
        print(json.dumps(j))
        self.assertRegex(json.dumps(j['r_attrs']['city']), "Nottingham")
        self.assertRegex(json.dumps(j['r_attrs']['latitude']), "52.9044")
        r.close()

    # RegressionGeoIP-v2.mmdb contains the same networks as
    # RegressionGeoIP.mmdb (generated with the python mmdb_writer package,
    # ip_version=6/ipv4_compatible) but maps 128.243.0.0/16 to Derby
    # instead of Nottingham, so we can verify a reload picks up new data
    def test_geoIP2Reload(self):
        attrs = dict()
        attrs['ip'] = '128.243.1.1'
        # the original DB maps 128.243.0.0/16 to Nottingham
        r = self.customFuncWithName("geoip2", attrs)
        j = r.json()
        self.assertRegex(json.dumps(j), "Nottingham")
        r.close()
        # replace the DB file with a version mapping 128.243.0.0/16
        # to Derby, and check the reload picks up the new data
        os.rename('RegressionGeoIP.mmdb', 'RegressionGeoIP.mmdb.orig')
        shutil.copyfile('RegressionGeoIP-v2.mmdb', 'RegressionGeoIP.mmdb')
        try:
            out = self.writeCmdToConsole("reloadGeoIP2DBs()").decode()
            self.assertRegex(out, "Reloaded GeoIP2 DB City")
            self.assertRegex(out, "Reloaded GeoIP2 DB Country")
            r = self.customFuncWithName("geoip2", attrs)
            j = r.json()
            self.assertRegex(json.dumps(j), "Derby")
            r.close()
        finally:
            os.rename('RegressionGeoIP.mmdb.orig', 'RegressionGeoIP.mmdb')
        # reload again and check we are back to the original data
        out = self.writeCmdToConsole("reloadGeoIP2DBs()").decode()
        self.assertRegex(out, "Reloaded GeoIP2 DB City")
        r = self.customFuncWithName("geoip2", attrs)
        j = r.json()
        self.assertRegex(json.dumps(j), "Nottingham")
        r.close()

    def test_geoIP2ReloadFailure(self):
        # If a DB file cannot be opened, reload should report an error
        # for that DB and keep serving the existing DB
        os.rename('RegressionGeoIP.mmdb', 'RegressionGeoIP.mmdb.orig')
        try:
            out = self.writeCmdToConsole("reloadGeoIP2DBs()").decode()
            self.assertRegex(out, "Error reloading GeoIP2 DB City")
            self.assertRegex(out, "Error reloading GeoIP2 DB Country")
            attrs = dict()
            attrs['ip'] = '128.243.1.1'
            r = self.customFuncWithName("geoip2", attrs)
            j = r.json()
            self.assertRegex(json.dumps(j), "Nottingham")
            r.close()
        finally:
            os.rename('RegressionGeoIP.mmdb.orig', 'RegressionGeoIP.mmdb')
        # reload should succeed again now the file is back
        out = self.writeCmdToConsole("reloadGeoIP2DBs()").decode()
        self.assertRegex(out, "Reloaded GeoIP2 DB City")
        self.assertRegex(out, "Reloaded GeoIP2 DB Country")
