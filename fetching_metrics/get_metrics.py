import time
import json
import os
import requests
import pytz
import traceback
from mixpanel_utils import MixpanelUtils

init_time = int(time.time()) #start time of the script
enable_logging = False
zd_url=""
#how many hours to look up
#running twice a day, so looking up the last 13 hours for 1 hour of overlap
hours_back = 13
profile_set_updates = []
profile_set_once_updates = []
es_offset = 2

# Utility functions
def log(message, always=False):
    if(enable_logging or always):
        print(f'logging: {message}')

def build_profile_update(id, props):
    return {
        "$distinct_id": id,
        "$properties": props
    }

# function to lookup metrics in ZD API
# https://developer.zendesk.com/api-reference/ticketing/tickets/ticket_metric_events/
def fetch_zendesk_metrics():
    global zd_url
    global init_time
    res = {"success": False, "value": [], "end": False}

    if zd_url == "":
        zd_url = "https://mixpanelsupport.zendesk.com/api/v2/incremental/ticket_metric_events.json?start_time="+str(int(init_time - (hours_back*3600)))

    try:
        resp = requests.get(zd_url, auth=(os.environ.get("zd_userame"), os.environ.get("zd_password")))
        print("Querying page "+ zd_url)
        if resp.status_code == 200:
            metrics = resp.json()
            zd_url = metrics['next_page']
            return {"success": True, "value": metrics["ticket_metric_events"], "end": metrics["end_of_stream"]} 
        else:
            print("bad response")
            print(resp)
    except Exception as e:
        print("error reading metrics")
        if(os.environ.get('env_setting') == "local"):
                traceback.print_exc()
    return res
# end of function fetch_zendesk_request

def metrics_to_updates(rows):
    global profile_set_updates
    global profile_set_once_updates

    if(len(rows) == 0):
        return False
    
    for metric in rows:
        try:
            if metric["type"] == "update_status" and "status" in metric and "calendar" in metric["status"]:
                #handle first reply
                if metric["metric"] == "reply_time" and metric["instance_id"] == 1:
                    profile_set_once_updates.append(
                        build_profile_update(metric["ticket_id"],{
                            "first_response_min_cal": metric["status"]["calendar"],
                            "first_response_min_bh": metric["status"]["business"],
                        })
                    )
                else:
                    #handle resolution time
                    if metric["metric"] == "requester_wait_time":
                        profile_set_updates.append(
                            build_profile_update(metric["ticket_id"],{
                                "full_resolution_min_cal": metric["status"]["calendar"],
                                "full_resolution_min_bh": metric["status"]["business"],
                            })
                        )
                        profile_set_once_updates.append(
                            build_profile_update(metric["ticket_id"],{
                                "first_resolution_min_cal": metric["status"]["calendar"],
                                "first_resolution_min_bh": metric["status"]["business"],
                            })
                        )

        except Exception as e:
            print("error evaluating metric; skipping")
            if(os.environ.get('env_setting') == "local"):
                traceback.print_exc()
                log(json.dumps(metric))


# end of function metrics_to_updates

# Initialization check
if(not os.environ.get("zd_userame")):
    log('Problems loading environment variables. Exiting', True)
    exit()
if(os.environ.get('env_setting') == "local"):
    enable_logging = True
    log('Running in dev mode')
    hours_back = int(os.environ.get('lookup_hours'))

log('Script starting', True)
done = False
zd_url = ""
#read ZD metrics
while done == False:
    metrics = fetch_zendesk_metrics()
    if(metrics["success"]):
        metrics_to_updates(metrics["value"])
    done = metrics["end"]

#sending data to Mixpanel
mputils = MixpanelUtils(os.environ.get('mp_project_api_secret'), token=os.environ.get('mp_project_token'))
updates_sent = 0
if len(profile_set_updates):
    mputils.import_people(profile_set_updates)
    updates_sent = updates_sent + len(profile_set_updates)
if len(profile_set_once_updates):
    mputils.people_set_once(lambda x: x["$properties"], profiles=profile_set_once_updates)
    updates_sent = updates_sent + len(profile_set_once_updates)
log(f'Finished sending {updates_sent} updates to tickets', False)