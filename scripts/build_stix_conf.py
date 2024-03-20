"""Build a default stix bundle Storm import config and save it to ``data/stix_import_conf.json``."""

import stormlibpp.stix


bc = stormlibpp.stix.BundleConf()
bc.load()
bc.save(out="data/stix_import_conf.json")
