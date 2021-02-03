import os
import re
import json
import traceback
import sys
import requests
import pycountry

GEO_CACHE_FILE_NAME='db/geo-cache.json'
OUTPUT_JSON_FILE_NAME='output.json'
OUTPUT_TXT_FILE_NAME='output.txt'

def find_geo(entry):
    print('find_geo called')
    #url = f"https://freegeoip.app/json/{entry['src_ip']}"

    ## access token from free account ipinfo.io (gmail account)
    url = f"https://ipinfo.io/{entry['src_ip']}?token=286904e1a908ce"
    headers = {
        'accept': "application/json",
        'content-type': "application/json"
    }
    try:
        response = requests.request("GET", url, headers=headers)
        respond = json.loads(response.text)
        entry['geo'] = respond
    except:
        entry['geo'] = None


def update_one_dict(key, r, ip, d):
    v = d.get(key)
    if v is None:
        v = {'src_ip': ip, 'rule': r, 'geo': None, 'count':1}
        d[key] = v
    else:
        v['count'] = v['count'] + 1
    
def update_dict(rule, src_ip, output, db): 
    key = src_ip + "+" + rule
    update_one_dict(key, rule, src_ip, output)
    update_one_dict(key, rule, src_ip, db)

    # update geo code in db cache
    v = db.get(key)
    if v['geo'] is None:
        find_geo(v)

    # copy geo code to the current output
    output[key]['geo'] = v['geo']


def process_file(fname, pat, output, db):
    file1 = open(fname, 'r')
    Lines = file1.readlines()
    for line in Lines:
        try:
            s1 = pat.search(line.strip()) 
            if s1 is not None:
                update_dict(s1.group(1), s1.group(4), output, db)
        except Exception:
            traceback.print_exc()


def main():
    #pat = re.compile('SRC=(.*?) DST=(.*?) LEN=')
    #pat = re.compile('\[(.*?)\]IN=(.*?) SRC=(.*?) DST=(.*?) LEN=')
    #pat = re.compile('\[(.*?)\]IN=')
    #pat = re.compile('SRC=(.*?) DST=(.*?)[\s]')
    pat = re.compile('\[(.*?)\]IN=(.*?) OUT= (.*?) SRC=(.*?) DST=(.*?) LEN=')
   
    # for current run output
    output = {}

    # read the cache first
    db = None
    try:
        with open(GEO_CACHE_FILE_NAME) as f:
            db = json.load(f)
    except: 
        print("geo cache file not found")
        db = {}
    
    for file in os.listdir("."):
        #if file.startswith("test-messages"):
        if file.startswith("messages"):
            process_file(file, pat, output, db)
   
    ## output results
    json.dump(output, open(OUTPUT_JSON_FILE_NAME, 'w'))

    fmt="{:<2},{:<20},country={:<30},region={:<25},city={:<25},count={:<8}\n"
    with open(OUTPUT_TXT_FILE_NAME, 'w') as f:
        for key in output: 
            v = output[key]
            g = output[key]['geo']
            if g is not None:
                country_name = g.get('country')
                try:
                   country_name = pycountry.countries.get(alpha_2=country_name).name
                except:
                    print(f"cn={country_name}")
                    country_name = g.get('country')

                try:
                    f.write(fmt.format(v.get('rule')[-1], 
                        v.get('src_ip'), 
                        country_name,
                        g.get('region'), 
                        g.get('city'), 
                        v.get('count')))
                except:
                    print(v.get('rule'), v.get('src_ip'), country_name, g.get('region'), g.get('city'), v.get('count'))
                # print(f"{v.get('src_ip')}, country={g.get('country')}, region={g.get('region')}, city={g.get('city')}, count={v.get('count')}")
    
    print('total entries: ', len(output))
   
    ## update geo cache file
    json.dump(db, open(GEO_CACHE_FILE_NAME, 'w'))

if __name__ == "__main__":
    # execute only if run as a script
    main()
