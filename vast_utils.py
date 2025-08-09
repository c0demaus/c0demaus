import os
import requests
import json
from argparse import Namespace
import time
import re
from urllib.parse import quote_plus
import shutil

# Default server URL
server_url_default = os.getenv("VAST_URL") or "https://console.vast.ai"

# API Key file path
APP_NAME = "vastai"
try:
    import xdg
    DIRS = {
        'config': xdg.xdg_config_home(),
    }
except ImportError:
    DIRS = {
        'config': os.path.join(os.getenv('HOME'), '.config'),
    }
for key in DIRS.keys():
    DIRS[key] = path = os.path.join(DIRS[key], APP_NAME)
    if not os.path.exists(path):
        os.makedirs(path)

APIKEY_FILE = os.path.join(DIRS['config'], "vast_api_key")
APIKEY_FILE_HOME = os.path.expanduser("~/.vast_api_key") # Legacy

if not os.path.exists(APIKEY_FILE) and os.path.exists(APIKEY_FILE_HOME):
  shutil.copyfile(APIKEY_FILE_HOME, APIKEY_FILE)

# Global headers dictionary
headers = {}

# These fields are displayed when you do 'show instances'
instance_fields = (
    ("id", "ID", "{}", None, True),
    ("machine_id", "Machine", "{}", None, True),
    ("actual_status", "Status", "{}", None, True),
    ("num_gpus", "Num", "{}x", None, False),
    ("gpu_name", "Model", "{}", None, True),
    ("gpu_util", "Util. %", "{:0.1f}", None, True),
    ("cpu_cores_effective", "vCPUs", "{:0.1f}", None, True),
    ("cpu_ram", "RAM", "{:0.1f}", lambda x: x / 1000, False),
    ("disk_space", "Storage", "{:.0f}", None, True),
    ("ssh_host", "SSH Addr", "{}", None, True),
    ("ssh_port", "SSH Port", "{}", None, True),
    ("dph_total", "$/hr", "{:0.4f}", None, True),
    ("image_uuid", "Image", "{}", None, True),
    ("inet_up", "Net up", "{:0.1f}", None, True),
    ("inet_down", "Net down", "{:0.1f}", None, True),
    ("reliability2", "R", "{:0.1f}", lambda x: x * 100, True),
    ("label", "Label", "{}", None, True),
    ("duration", "age(hours)", "{:0.2f}",  lambda x: x/(3600.0), True),
    ("uptime_mins", "uptime(mins)", "{:0.2f}",  None, True),
)

def get_api_key():
    if os.path.exists(APIKEY_FILE):
        with open(APIKEY_FILE, "r") as reader:
            return reader.read().strip()
    return None

def strip_strings(value):
    if isinstance(value, str):
        return value.strip()
    elif isinstance(value, dict):
        return {k: strip_strings(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [strip_strings(item) for item in value]
    return value

def apiurl(args, subpath, query_args=None):
    if query_args is None:
        query_args = {}
    if args.api_key is not None:
        query_args["api_key"] = args.api_key

    if query_args:
        query_json = "&".join(
            "{x}={y}".format(x=x, y=quote_plus(y if isinstance(y, str) else json.dumps(y))) for x, y in
            query_args.items())
        result = args.url + "/api/v0" + subpath + "?" + query_json
    else:
        result = args.url + "/api/v0" + subpath
    return result

def http_request(verb, args, req_url, headers=None, json_data=None):
    t = 0.15
    for i in range(0, args.retry):
        try:
            r = requests.request(verb, req_url, headers=headers, json=json_data, timeout=30)
            if r.status_code != 429:
                r.raise_for_status()
                return r
            time.sleep(t)
            t *= 1.5
        except requests.exceptions.RequestException as e:
            if i == args.retry - 1:
                raise e
            time.sleep(t)
            t *= 1.5

def http_get(args, req_url, headers=None, json_data=None):
    return http_request('GET', args, req_url, headers, json_data)

def http_put(args, req_url, headers=None, json_data={}):
    return http_request('PUT', args, req_url, headers, json_data)

def http_del(args, req_url, headers=None, json_data={}):
    return http_request('DELETE', args, req_url, headers, json_data)

def show_instances(args):
    req_url = apiurl(args, "/instances", {"owner": "me"})
    r = http_get(args, req_url, headers=headers)
    rows = r.json()["instances"]
    for row in rows:
        row = {k: strip_strings(v) for k, v in row.items()}
        if 'start_date' in row and row['start_date'] is not None:
            row['duration'] = time.time() - row['start_date']
        else:
            row['duration'] = 0
        if 'extra_env' in row and isinstance(row['extra_env'], list):
            row['extra_env'] = {env_var[0]: env_var[1] for env_var in row['extra_env']}
    return rows

def destroy_instance(args, instance_id):
    url = apiurl(args, f"/instances/{instance_id}/")
    r = http_del(args, url, headers=headers)
    return r.json()

# --- Functions for searching offers ---

displayable_fields = (
    ("id", "ID", "{}", None, True),
    ("cuda_max_good", "CUDA", "{:0.1f}", None, True),
    ("num_gpus", "N", "{}x", None, False),
    ("gpu_name", "Model", "{}", None, True),
    ("pcie_bw", "PCIE", "{:0.1f}", None, True),
    ("cpu_ghz", "cpu_ghz", "{:0.1f}", None, True),
    ("cpu_cores_effective", "vCPUs", "{:0.1f}", None, True),
    ("cpu_ram", "RAM", "{:0.1f}", lambda x: x / 1000, False),
    ("disk_space", "Disk", "{:.0f}", None, True),
    ("dph_total", "$/hr", "{:0.4f}", None, True),
    ("dlperf", "DLP", "{:0.1f}", None, True),
    ("dlperf_per_dphtotal", "DLP/$", "{:0.2f}", None, True),
    ("score", "score", "{:0.1f}", None, True),
    ("driver_version", "NV Driver", "{}", None, True),
    ("inet_up", "Net_up", "{:0.1f}", None, True),
    ("inet_down", "Net_down", "{:0.1f}", None, True),
    ("reliability", "R", "{:0.1f}", lambda x: x * 100, True),
    ("duration", "Max_Days", "{:0.1f}", lambda x: x / (24.0 * 60.0 * 60.0), True),
    ("machine_id", "mach_id", "{}", None, True),
    ("verification", "status", "{}", None, True),
    ("host_id", "host_id", "{}", None, True),
    ("direct_port_count", "ports", "{}", None, True),
    ("geolocation", "country", "{}", None, True),
)

offers_fields = {
    "bw_nvlink", "compute_cap", "cpu_arch", "cpu_cores", "cpu_cores_effective",
    "cpu_ghz", "cpu_ram", "cuda_max_good", "datacenter", "direct_port_count",
    "driver_version", "disk_bw", "disk_space", "dlperf", "dlperf_per_dphtotal",
    "dph_total", "duration", "external", "flops_per_dphtotal", "gpu_arch",
    "gpu_display_active", "gpu_frac", "gpu_mem_bw", "gpu_name", "gpu_ram",
    "gpu_total_ram", "has_avx", "host_id", "id", "inet_down", "inet_down_cost",
    "inet_up", "inet_up_cost", "machine_id", "min_bid", "mobo_name", "num_gpus",
    "pci_gen", "pcie_bw", "reliability", "rentable", "rented", "storage_cost",
    "static_ip", "total_flops", "ubuntu_version", "verification", "verified",
    "vms_enabled", "geolocation", "cluster_id"
}

offers_alias = {
    "cuda_vers": "cuda_max_good", "display_active": "gpu_display_active",
    "dlperf_usd": "dlperf_per_dphtotal", "dph": "dph_total",
    "flops_usd": "flops_per_dphtotal",
}

offers_mult = {
    "cpu_ram": 1000, "gpu_ram": 1000, "gpu_total_ram": 1000,
    "duration": 24.0 * 60.0 * 60.0,
}

def parse_query(query_str, res=None, fields={}, field_alias={}, field_multiplier={}):
    if query_str is None:
        return res
    if res is None:
        res = {}
    if type(query_str) == list:
        query_str = " ".join(query_str)
    query_str = query_str.strip()
    pattern = r"([a-zA-Z0-9_]+)( *[=><!]+| +(?:[lg]te?|nin|neq|eq|not ?eq|not ?in|in) )?( *)(\[[^\]]+\]|\"[^\"]+\"|[^ ]+)?( *)"
    opts = re.findall(pattern, query_str)
    op_names = {
        ">=": "gte", ">": "gt", "gt": "gt", "gte": "gte",
        "<=": "lte", "<": "lt", "lt": "lt", "lte": "lte",
        "!=": "neq", "==": "eq", "=": "eq", "eq": "eq",
        "neq": "neq", "noteq": "neq", "not eq": "neq",
        "notin": "notin", "not in": "notin", "nin": "notin", "in": "in",
    }
    joined = "".join("".join(x) for x in opts)
    if joined != query_str:
        raise ValueError(f"Unconsumed text. Did you forget to quote your query? {repr(joined)} != {repr(query_str)}")
    for field, op, _, value, _ in opts:
        value = value.strip(",[]")
        v = res.setdefault(field, {})
        op = op.strip()
        op_name = op_names.get(op)
        if field in field_alias:
            res.pop(field)
            field = field_alias[field]
        if not op_name:
            raise ValueError(f"Unknown operator. Did you forget to quote your query? {repr(op)}")
        if op_name in ["in", "notin"]:
            value = [x.strip() for x in value.split(",") if x.strip()]
        if not value:
            raise ValueError(f"Value cannot be blank. Did you forget to quote your query? {repr((field, op, value))}")
        if value in ["?", "*", "any"]:
            if op_name != "eq":
                raise ValueError("Wildcard only makes sense with equals.")
            if field in v: del v[field]
            if field in res: del res[field]
            continue
        if isinstance(value, str):
            value = value.replace('_', ' ').strip('\"')
        elif isinstance(value, list):
            value = [x.replace('_', ' ').strip('\"') for x in value]
        if field in field_multiplier:
            value = float(value) * field_multiplier[field]
            v[op_name] = value
        else:
            if value == 'true' or value == 'True': v[op_name] = True
            elif value == 'false' or value == 'False': v[op_name] = False
            elif value == 'None' or value == 'null': v[op_name] = None
            else: v[op_name] = value
        if field not in res:
            res[field] = v
        else:
            res[field].update(v)
    return res

def search_offers(args, query_str):
    query = {"verified": {"eq": True}, "external": {"eq": False}, "rentable": {"eq": True}, "rented": {"eq": False}}
    query = parse_query(query_str, query, offers_fields, offers_alias, offers_mult)

    order = []
    for name in args.order.split(","):
        name = name.strip()
        if not name: continue
        direction = "asc"
        field = name
        if name.strip("-") != name:
            direction = "desc"
            field = name.strip("-")
        if name.strip("+") != name:
            direction = "asc"
            field = name.strip("+")
        if field in offers_alias:
            field = offers_alias[field]
        order.append([field, direction])

    query["order"] = order
    query["type"] = args.type
    if args.limit:
        query["limit"] = int(args.limit)

    url = apiurl(args, "/bundles/")
    r = http_request('POST', args, url, headers=headers, json_data=query)
    rows = r.json()["offers"]
    return rows

# --- Functions for creating instances ---

def get_runtype(args):
    runtype = 'ssh'
    if args.args:
        runtype = 'args'
    if (args.args == '') or (args.args == ['']) or (args.args == []):
        runtype = 'args'
        args.args = None
    if not args.jupyter and (args.jupyter_dir or args.jupyter_lab):
        args.jupyter = True
    if args.jupyter and runtype == 'args':
        raise ValueError("Can't use --jupyter and --args together.")
    if args.jupyter:
        runtype = 'jupyter_direc ssh_direc ssh_proxy' if args.direct else 'jupyter_proxy ssh_proxy'
    elif args.ssh:
        runtype = 'ssh_direc ssh_proxy' if args.direct else 'ssh_proxy'
    return runtype

def smart_split(s, char):
    in_double_quotes = False
    in_single_quotes = False
    parts = []
    current = []
    for c in s:
        if c == char and not (in_double_quotes or in_single_quotes):
            parts.append(''.join(current))
            current = []
        elif c == '\'':
            in_single_quotes = not in_single_quotes
            current.append(c)
        elif c == '\"':
            in_double_quotes = not in_double_quotes
            current.append(c)
        else:
            current.append(c)
    parts.append(''.join(current))
    return parts

def parse_env(envs):
    result = {}
    if envs is None: return result
    env = smart_split(envs, ' ')
    prev = None
    for e in env:
        if prev is None:
            if e in {"-e", "-p", "-h", "-v", "-n"}:
                prev = e
        else:
            if prev == "-p":
                result["-p " + e] = "1"
            elif prev == "-e":
                kv = e.split('=', 1)
                if len(kv) == 2:
                    result[kv[0]] = kv[1].strip("'\"")
            else:
                result[prev] = e
            prev = None
    return result

def create_instance(args, instance_id):
    if args.onstart:
        with open(args.onstart, "r") as reader:
            onstart_cmd = reader.read()
    else:
        onstart_cmd = args.onstart_cmd

    runtype = get_runtype(args)

    json_blob = {
        "client_id": "me",
        "image": args.image,
        "env": parse_env(args.env),
        "price": args.bid_price,
        "disk": args.disk,
        "label": args.label,
        "onstart": onstart_cmd,
        "runtype": runtype,
        "image_login": args.login,
        "python_utf8": args.python_utf8,
        "lang_utf8": args.lang_utf8,
        "use_jupyter_lab": args.jupyter_lab,
        "jupyter_dir": args.jupyter_dir,
        "force": args.force,
        "cancel_unavail": args.cancel_unavail,
    }

    if args.args:
        json_blob["args"] = args.args

    url = apiurl(args, f"/asks/{instance_id}/")
    r = http_put(args, url, headers=headers, json_data=json_blob)
    return r.json()
