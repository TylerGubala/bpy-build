import pprint

import bpybuild.sources

matched_version_dict = bpybuild.sources.get_matched_versions()

for version in [_version for _version in matched_version_dict if 
                matched_version_dict[_version][0] and 
                matched_version_dict[_version][1]]:

    for _platform in [__platform for __platform in 
                      matched_version_dict[version][1][0].platforms() if
                      __platform.os_name == "Linux"]:

        pprint.pprint({version: _platform.python_versions()})