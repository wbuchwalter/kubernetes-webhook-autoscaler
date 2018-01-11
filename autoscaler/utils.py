import json
import re
import urllib.request

SI_suffix = {
    'y': 1e-24,  # yocto
    'z': 1e-21,  # zepto
    'a': 1e-18,  # atto
    'f': 1e-15,  # femto
    'p': 1e-12,  # pico
    'n': 1e-9,  # nano
    'u': 1e-6,  # micro
    'm': 1e-3,  # mili
    'c': 1e-2,  # centi
    'd': 1e-1,  # deci
    'k': 1e3,  # kilo
    'M': 1e6,  # mega
    'G': 1e9,  # giga
    'T': 1e12,  # tera
    'P': 1e15,  # peta
    'E': 1e18,  # exa
    'Z': 1e21,  # zetta
    'Y': 1e24,  # yotta
    # Kube also uses the power of 2 equivalent
    'Ki': 2**10,
    'Mi': 2**20,
    'Gi': 2**30,
    'Ti': 2**40,
    'Pi': 2**50,
    'Ei': 2**60,
}
SI_regex = re.compile(r"(\d+)(%s)?$" % "|".join(SI_suffix.keys()))


def parse_SI(s):
    m = SI_regex.match(s)
    if m is None:
        raise ValueError("Unknown SI quantity: %s" % s)
    num_s, unit = m.groups()
    multiplier = SI_suffix[unit] if unit else 1.  # unitless
    return float(num_s) * multiplier


def parse_resource(resource):
    try:
        return float(resource)
    except ValueError:
        return parse_SI(resource)


def parse_bool_label(value):
    return str(value).lower() in ('1', 'true')

def is_agent(node, pool_name_regex):
    # if a node name matches the pool regex, then it is an agent
    result = re.search(pool_name_regex, node.name)
    if result:
        return True
    return False

def get_pool_name(node, pool_name_regex):
    result = re.search(pool_name_regex, node.name)
    if result:
        return result.group(0)

    raise ValueError("Couldn't infer pool name for node {}".format(node.name))
        