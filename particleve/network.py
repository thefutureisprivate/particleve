"""Render networkd and nftables from validated host topology."""

from pathlib import Path

from .common import atomic_write


def render(config):
    network = config["network"]
    files = {}
    devices = network["links"] + network.get("bridges", []) + network.get("vlans", [])
    for link in network["links"]:
        files[f"etc/systemd/network/10-particleve-{link['name']}.link"] = (
            f"[Match]\nPermanentMACAddress={link['mac']}\n\n[Link]\nName={link['name']}\n"
        )
    for bridge in network.get("bridges", []):
        files[f"etc/systemd/network/20-particleve-{bridge['name']}.netdev"] = (
            f"[NetDev]\nName={bridge['name']}\nKind=bridge\n"
        )
    for vlan in network.get("vlans", []):
        files[f"etc/systemd/network/20-particleve-{vlan['name']}.netdev"] = (
            f"[NetDev]\nName={vlan['name']}\nKind=vlan\n\n[VLAN]\nId={vlan['id']}\n"
        )
    for device in devices:
        lines = [
            "[Match]",
            f"Name={device['name']}",
            "",
            "[Network]",
            "DHCP=no",
            "IPv6AcceptRA=no",
            "LinkLocalAddressing=no",
        ]
        if device.get("bridge"):
            lines.append(f"Bridge={device['bridge']}")
        for vlan in network.get("vlans", []):
            if vlan["parent"] == device["name"]:
                lines.append(f"VLAN={vlan['name']}")
        if device["name"] == network["management"]:
            lines += [f"Address={value}" for value in network["addresses"]]
            lines += [f"Gateway={value}" for value in network["gateways"]]
            lines += [f"DNS={value}" for value in network["dns"]]
            lines += [f"NTP={value}" for value in network["ntp"]]
            lines += ["", "[Link]", "RequiredForOnline=routable"]
        else:
            lines += ["", "[Link]", "RequiredForOnline=no"]
        files[f"etc/systemd/network/30-particleve-{device['name']}.network"] = "\n".join(lines) + "\n"
    # Only our host-input table is replaced; external guest forwarding policy remains independent.
    rules = [
        "destroy table inet particleve_host",
        "table inet particleve_host {",
        "  chain input {",
        "    type filter hook input priority 0; policy drop;",
        '    iifname "lo" accept',
        "    ct state invalid drop",
        "    ct state established,related accept",
        "    meta l4proto { icmp, ipv6-icmp } accept",
    ]
    for source in network["allowed_sources"]:
        family = "ip6" if ":" in source else "ip"
        rules.append(f'    iifname "{network["management"]}" {family} saddr {source} tcp dport 22 accept')
    rules += ["  }", "}"]
    files["etc/particleve/host.nft"] = "\n".join(rules) + "\n"
    files["etc/systemd/timesyncd.conf.d/50-particleve.conf"] = (
        "[Time]\nNTP=" + " ".join(network["ntp"]) + "\n"
    )
    files["etc/hostname"] = config["hostname"] + "\n"
    console = config.get("console", "console=tty0").removeprefix("console=")
    if console != "tty0":
        port, _, setting = console.partition(",")
        baud = setting.removesuffix("n8") if setting else "115200"
        files["etc/systemd/system/getty.target.d/50-particleve-console.conf"] = (
            f"[Unit]\nWants=serial-getty@{port}.service\n"
        )
        files[f"etc/systemd/system/serial-getty@{port}.service.d/50-particleve.conf"] = (
            "[Service]\nExecStart=\n"
            f"ExecStart=-/sbin/agetty --noclear --noreset -o '-p -- \\u' - {baud} vt220\n"
        )
    files["etc/ssh/sshd_config.d/05-particleve.conf"] = (
        "UsePAM yes\nPubkeyAuthentication yes\n"
        "AuthorizedKeysCommand /usr/bin/userdbctl ssh-authorized-keys %u\n"
        "AuthorizedKeysCommandUser root\n"
        "PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin prohibit-password\n"
        "PermitEmptyPasswords no\nX11Forwarding no\nAllowAgentForwarding no\n"
    )
    return files


def write(config, root):
    for name, content in render(config).items():
        atomic_write(Path(root) / name, content.encode(), mode=0o644)
