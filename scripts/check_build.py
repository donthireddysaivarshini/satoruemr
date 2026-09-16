#!/usr/bin/env python3
import json
with open("/mnt/c/Projects/EMRCHT/cht-core/webapp/angular.json") as f:
    d = json.load(f)
p = d["projects"]["webapp"]["architect"]["build"]["options"]
print("outputPath:", p.get("outputPath"))
print("main:", p.get("main"))
