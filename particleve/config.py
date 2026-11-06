"""Validate installation inputs before generating commands or touching disks."""

import base64
import binascii
import ipaddress
import re
from urllib.parse import urlsplit

from .common import require

NAME = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{0,14}\Z")
VERSION = re.compile(r"[0-9]{1,6}(?:\.[0-9]{1,6})?\Z")
STABLE_DISK = re.compile(r"/dev/disk/by-id/[a-zA-Z0-9_.:+-]+\Z")
VERITY_SIGNATURE_SIZE = 1024 * 1024
MAINTENANCE_RAM_RESERVE_MIB = 1024


def ssh_key(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"ssh-ed25519 [A-Za-z0-9+/]+={0,2}(?: [^\n\r]+)?", value
    ):
        return False
    try:
        blob = base64.b64decode(value.split()[1], validate=True)
    except ValueError, binascii.Error:
        return False
    return blob.startswith(b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20") and len(blob) == 51


def version_key(value):
    require(VERSION.fullmatch(value), "version must use numeric OBS counters")
    return tuple(int(part) for part in value.split("."))


def integer(value, minimum, label):
    require(type(value) is int and value >= minimum, f"{label} must be an integer >= {minimum}")
    return value


def https_url(value):
    parsed = urlsplit(value)
    require(
        parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password,
        "feed must be an HTTPS URL without credentials",
    )
    require(not parsed.query and not parsed.fragment and not re.search(r"[\s%\\]", value), "invalid feed URL")
    require(not parsed.hostname.endswith((".invalid", ".example")), "configure the real ParticleVE feed")
    return value.rstrip("/")


def validate(config, *, publication=False):
    require(config.get("schema") == 1, "installation schema must be 1; no implicit migrations")
    require(config.get("architecture") == "x86-64", "only the x86-64/v2 build target is implemented")
    require(config.get("cpu_baseline") == "x86-64-v2", "CPU baseline must be x86-64-v2")
    require(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", config["hostname"]), "invalid hostname")
    disks = config["disks"]
    require(len(disks) == 2, "select exactly two boot disks")
    require({d["role"] for d in disks} == {"a", "b"}, "disk roles must be a and b")
    for disk in disks:
        require(STABLE_DISK.fullmatch(disk["path"]), "disks must use explicit /dev/disk/by-id identities")
        require(not re.search(r"-part[0-9]+$", disk["path"]), "select whole disks, not partitions")
        require(isinstance(disk["serial"], str) and disk["serial"].strip(), "record each disk serial")
    require(len({d["path"] for d in disks}) == 2, "disk paths must differ")
    require(len({d["serial"] for d in disks}) == 2, "disk serials must differ")
    storage = config["storage"]
    for field, minimum in {
        "esp_mib": 1024,
        "usr_growth_percent": 20,
        "swap_mib": 1024,
        "minimum_state_mib": 8192,
        "reserve_mib": 2048,
        "reserve_percent": 10,
        "metadata_max_percent": 50,
        "degraded_wait_seconds": 5,
        "firmware_staging_mib": 64,
    }.items():
        integer(storage[field], minimum, field)
    require(storage["reserve_percent"] <= 50, "state reserve must be <= 50%")
    require(storage["metadata_max_percent"] <= 95, "metadata threshold must be <= 95%")
    require(storage["degraded_wait_seconds"] <= 120, "missing-device wait must be bounded to 120 seconds")
    require(storage.get("discard") is False, "discard requires a separately commissioned policy")
    integer(config["minimum_ram_mib"], 2048, "minimum_ram_mib")
    require(config.get("recovery_console_confirmed") is True, "confirm independent recovery console access")
    require(config.get("tpm_policy") == "pcr7+signed-pcr11", "this implementation uses PCR7 + signed PCR11")
    console = config.get("console", "console=tty0")
    require(re.fullmatch(r"console=(?:tty0|ttyS[0-9]+(?:,[0-9]+n8)?)", console), "unsupported console")
    network = config["network"]
    devices = network["links"] + network.get("bridges", []) + network.get("vlans", [])
    names = [d["name"] for d in devices]
    require(len(names) == len(set(names)) and all(NAME.fullmatch(n) for n in names), "invalid network names")
    require(network["management"] in names, "management interface must be declared")
    require(network["links"], "declare at least one physical management NIC")
    for link in network["links"]:
        require(re.fullmatch(r"[0-9a-f]{2}(?::[0-9a-f]{2}){5}", link["mac"]), "invalid permanent NIC MAC")
    require(len({d["mac"] for d in network["links"]}) == len(network["links"]), "duplicate NIC MAC")
    graph = {}
    bridges = {d["name"] for d in network.get("bridges", [])}
    for dev in devices:
        if "bridge" in dev:
            require(dev["bridge"] in bridges and dev["bridge"] != dev["name"], "invalid bridge owner")
            graph.setdefault(dev["name"], []).append(dev["bridge"])
    for vlan in network.get("vlans", []):
        require(vlan["parent"] in names and vlan["parent"] != vlan["name"], "invalid VLAN parent")
        integer(vlan["id"], 1, "VLAN id")
        require(vlan["id"] <= 4094, "VLAN id must be <= 4094")
        graph.setdefault(vlan["parent"], []).append(vlan["name"])

    def visit(name, ancestors):
        require(name not in ancestors, "network ownership contains a cycle")
        for child in graph.get(name, []):
            visit(child, ancestors | {name})

    for name in names:
        visit(name, set())
    require(network["addresses"], "configure static management addresses")
    for address in network["addresses"]:
        ipaddress.ip_interface(address)
    sources = [ipaddress.ip_network(s, strict=True) for s in network["allowed_sources"]]
    require(
        sources and all(s.prefixlen > 0 for s in sources), "management sources cannot include the Internet"
    )
    for gateway in network["gateways"]:
        ipaddress.ip_address(gateway)
    for dns in network["dns"]:
        ipaddress.ip_address(dns)
    require(network["dns"], "configure DNS servers")
    for ntp in network["ntp"]:
        require(re.fullmatch(r"[a-zA-Z0-9.:-]+", ntp), "invalid time server")
    require(network["ntp"], "configure a time server")
    for key, minimum in (("start_tolerance_seconds", 1), ("graceful_seconds", 10), ("restore_seconds", 10)):
        integer(config["maintenance"][key], minimum, key)
    require(
        config["maintenance"]["start_tolerance_seconds"] <= 60,
        "maintenance start tolerance must be <= 60 seconds",
    )
    require(
        config["maintenance"]["graceful_seconds"] <= 1800, "graceful shutdown must be bounded to 30 minutes"
    )
    require(config["maintenance"]["restore_seconds"] <= 600, "restoration must be bounded to 10 minutes")
    reserve = config["maintenance"].get("minimum_available_ram_mib", MAINTENANCE_RAM_RESERVE_MIB)
    integer(reserve, 256, "minimum_available_ram_mib")
    require(
        reserve < config["minimum_ram_mib"],
        "maintenance RAM reserve must be below the minimum physical RAM",
    )
    require(
        config.get("admin_ssh_keys") and all(ssh_key(k) for k in config["admin_ssh_keys"]),
        "configure owner Ed25519 SSH public keys",
    )
    if publication:
        https_url(config["feed"])
    return config
