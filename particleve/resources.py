"""Physical memory headroom and read-only health of the selected boot disks."""

import json
from pathlib import Path

from .common import Deferred, Error, require, run
from .config import MAINTENANCE_RAM_RESERVE_MIB
from .inventory import observe_disk


def memory():
    fields = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        if key in ("MemTotal", "MemAvailable"):
            number, unit = value.split()
            require(unit == "kB", "unexpected kernel memory units")
            fields[key] = int(number) * 1024
    require(
        set(fields) == {"MemTotal", "MemAvailable"} and 0 <= fields["MemAvailable"] <= fields["MemTotal"],
        "physical memory availability cannot be established",
    )
    return {"total_bytes": fields["MemTotal"], "available_bytes": fields["MemAvailable"]}


def disk_health(selected):
    observe_disk(selected)  # Recheck the configured whole-disk identity before querying it.
    result = run(
        ["smartctl", "--json", "--health", "--attributes", selected["path"]],
        check=False,
        timeout=20,
    )
    report = json.loads(result.stdout)
    require(isinstance(report, dict), "invalid smartctl report")
    passed = report.get("smart_status", {}).get("passed")
    # smartctl's exit status is a bitmask: bits 3..7 report device health/history.
    # Missing/unsupported transport data must never be presented as a healthy disk.
    if passed is False or result.returncode & 0xF8:
        status = "attention"
    elif result.returncode == 0 and passed is True:
        status = "passed"
    else:
        status = "unavailable"
    return {
        "role": selected["role"],
        "path": selected["path"],
        "status": status,
        "exit_status": result.returncode,
        "report": report,
    }


def status(config, selected, *, healthy):
    ram = memory()
    reserve = config["maintenance"].get("minimum_available_ram_mib", MAINTENANCE_RAM_RESERVE_MIB) * 1024**2
    ram["reserve_bytes"] = reserve
    if healthy and ram["available_bytes"] < reserve:
        raise Deferred("physical memory headroom is below the maintenance reserve")
    disks = []
    for disk in selected:
        try:
            disks.append(disk_health(disk))
        except (Error, OSError, ValueError) as exc:
            disks.append(
                {"role": disk["role"], "path": disk["path"], "status": "unavailable", "reason": str(exc)}
            )
    if healthy and any(disk["status"] == "attention" for disk in disks):
        raise Deferred("a selected disk reports a SMART health fault; inspect physical disk health")
    return {"memory": ram, "physical_disks": disks}
