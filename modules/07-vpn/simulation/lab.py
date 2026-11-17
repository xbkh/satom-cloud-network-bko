"""Tests des modules 7 et 8, à exécuter avec unshare -Urn."""
import contextlib
import os
from pathlib import Path
import secrets
import shlex
import subprocess
import sys
import time

bird = Path(sys.argv[1]).resolve()
birdc = bird.with_name("birdc")
work = Path(sys.argv[2]).resolve()
work.mkdir(exist_ok=True)
gre = Path(__file__).with_name("gre.py")
app = "10.0.2.10"
sites = {"siege": "192.168.10.1", "agence": "192.168.20.1"}
namespaces = {}
processes = []


def command(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def prefix(node):
    return ["nsenter", "-t", str(namespaces[node].pid), "-n", "--"]


def run(node, *args, quiet=False):
    return command(prefix(node) + list(args), capture_output=quiet)


def launch(node, *args):
    child = subprocess.Popen(prefix(node) + list(args), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    processes.append(child)
    return child


def ns(node):
    child = subprocess.Popen(["unshare", "-n", "sleep", "3600"])
    processes.append(child)
    namespaces[node] = child
    for _ in range(40):
        if os.readlink(f"/proc/{child.pid}/ns/net") != os.readlink("/proc/self/ns/net"):
            break
        time.sleep(0.05)
    else:
        raise RuntimeError(f"Espace réseau non isolé pour {node}")
    run(node, "ip", "link", "set", "lo", "up")


def esp(sender, receiver, src, dst, index):
    key = "0x" + secrets.token_hex(20)
    spi = hex(0x700 + index)
    for node in (sender, receiver):
        run(node, "ip", "xfrm", "state", "add", "src", src, "dst", dst,
            "proto", "esp", "spi", spi, "mode", "transport",
            "aead", "rfc4106(gcm(aes))", key, "128", quiet=True)
    for node, direction in ((sender, "out"), (receiver, "in")):
        run(node, "ip", "xfrm", "policy", "add", "src", src, "dst", dst,
            "proto", "gre", "dir", direction, "tmpl", "src", src, "dst", dst,
            "proto", "esp", "mode", "transport", "level", "required", quiet=True)


def link(node, label, index, encrypted):
    outer = [f"192.0.2.{index * 4 + i}" for i in (1, 2)]
    inner = [f"169.254.{index}.1", f"169.254.{index}.2"]
    devices = [f"x{index}a", f"x{index}b"]
    command(["ip", "link", "add", devices[0], "type", "veth", "peer", "name", devices[1]])
    for i, who in enumerate((node, "aws")):
        command(["ip", "link", "set", devices[i], "netns", str(namespaces[who].pid)])
        run(who, "ip", "addr", "add", outer[i]+"/30", "dev", devices[i])
        run(who, "ip", "link", "set", devices[i], "up")
        run(who, "ip", "tuntap", "add", "dev", label, "mode", "tun")
        run(who, "ip", "addr", "add", inner[i]+"/30", "dev", label)
        run(who, "ip", "link", "set", label, "mtu", "1400", "up")
    if encrypted:
        esp(node, "aws", outer[0], outer[1], index * 2)
        esp("aws", node, outer[1], outer[0], index * 2 + 1)
    for i, who in enumerate((node, "aws")):
        launch(who, sys.executable, str(gre), label, outer[i], outer[1-i])
    return inner


def route(node, action, network, device, peer, metric):
    run(node, "ip", "route", action, network, "via", peer, "dev", device, "metric", str(metric))


def check(node, args, success=True):
    print(f"$ {node}# {shlex.join(args)}", flush=True)
    result = subprocess.run(prefix(node) + args, check=False)
    print(f"code={result.returncode}", flush=True)
    if (result.returncode == 0) != success:
        raise RuntimeError(f"Résultat inattendu depuis {node}")


def bird_config(node, peers):
    local_as, remote_as, advertised, remote = {
        "siege": (65010, 64513, "192.168.10.0/24", "10.0.0.0/16"),
        "aws": (64513, 65010, "10.0.0.0/16", "192.168.10.0/24")
    }[node]
    router_id = "192.168.10.1" if node == "siege" else app
    text = f"""router id {router_id};
protocol device {{}}
protocol kernel {{ ipv4 {{ import none; export filter {{ if source = RTS_BGP then accept; reject; }}; }}; }}
protocol static {{ ipv4; route {advertised} via "lo"; }}
"""
    for name, local, peer in peers:
        priority = "bgp_local_pref = 200;" if node == "siege" and name == "dx" else ""
        prepend = "bgp_path.prepend(65010); " * 3 if node == "siege" and name == "vpn" else ""
        text += f"""protocol bgp {name} {{
 local {local} as {local_as};
 neighbor {peer} as {remote_as};
 connect retry time 3;
 connect delay time 1;
 check link on;
 hold time 9;
 keepalive time 3;
 ipv4 {{
  import filter {{ if net != {remote} then reject; {priority} accept; }};
  export filter {{ if net != {advertised} then reject; {prepend} accept; }};
 }};
}}
"""
    file = work / f"{node}.conf"
    file.write_text(text)
    return file


def bird_show(node, *query, show=True):
    cmd = [str(birdc), "-s", str(work / f"{node}.sock"), *query]
    result = run(node, *cmd, quiet=True).stdout
    if show:
        print(f"$ {node}# birdc {' '.join(query)}\n{result.rstrip()}", flush=True)
    return result


def await_route(device, start=None):
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        result = subprocess.run(prefix("siege") + ["ip", "route", "get", app],
                                capture_output=True, text=True, check=False)
        path = result.stdout
        if f"dev {device}" in path:
            elapsed = time.monotonic() - start if start else None
            print(f"$ siege# ip route get {app}\n{path.rstrip()}", flush=True)
            return elapsed
        time.sleep(0.1)
    raise RuntimeError(f"Route non convergée vers {device}")


def main():
    for node in ("siege", "agence", "aws"):
        ns(node)
        addr = sites.get(node, app)
        run(node, "ip", "addr", "add", addr+"/24", "dev", "lo")
    link("siege", "dx0", 1, False)
    topo = {
        "siege": [(label, link("siege", label, index, True)) for label, index in (("ipsec1", 2), ("ipsec2", 3))],
        "agence": [(label, link("agence", label, index, True)) for label, index in (("agence1", 4), ("agence2", 5))]
    }
    command_path = work / "www"
    command_path.mkdir(exist_ok=True)
    (command_path / "index.html").write_text("app-01 simulation : HTTP 8080\n")
    for port in ("8080", "8081"):
        launch("aws", sys.executable, "-m", "http.server", port, "--bind", app, "--directory", str(command_path))
    firewall = """table inet leman {
 chain input {
  type filter hook input priority 0; policy accept;
  ip saddr { 192.168.10.0/24, 192.168.20.0/24 } tcp dport != 8080 drop
  ip saddr 192.168.20.0/24 icmp type echo-request drop
 }
}
"""
    command(prefix("aws") + ["nft", "-f", "-"], input=firewall)
    for node, links in topo.items():
        for i, (label, (local, remote)) in enumerate(links):
            metric = 10 + i * 10
            route(node, "add", "10.0.0.0/16", label, remote, metric)
            route("aws", "add", sites[node].rsplit(".", 1)[0]+".0/24", label, local, metric)
    time.sleep(0.5)
    print("=== MODULE 7 : ESP AES-GCM, routes statiques et segmentation (local) ===", flush=True)
    # curl/ping emploient l'adresse LAN pour exercer la politique du site.
    ping = ["ping", "-I", sites["siege"], "-c", "2", "-W", "1", app]
    check("siege", ping)
    check("agence", ["curl","--interface",sites["agence"],"-fsS","--max-time","2",f"http://{app}:8080/"])
    check("agence", ["curl","--interface",sites["agence"],"-fsS","--max-time","2",f"http://{app}:8081/"], False)
    for node in sites:
        check(node, ["ping", "-I", sites[node], "-c", "1", "-W", "1", "10.1.1.10"], False)
    for node in ("siege","aws"):
        print(f"$ {node}# ip link set ipsec1 down", flush=True)
        run(node, "ip", "link", "set", "ipsec1", "down")
    await_route("ipsec2")
    check("siege", ping)
    print("$ siege# ip -s xfrm state list nokeys", flush=True)
    esp_status = run("siege", "ip", "-s", "xfrm", "state", "list", "nokeys", quiet=True).stdout
    for line in esp_status.splitlines():
        if line.startswith("src ") or any(key in line for key in ("proto esp", "gcm(aes)", "(packets)")):
            print(line, flush=True)
    print("=== FIN MODULE 7 ===", flush=True)

    route("siege", "del", "10.0.0.0/16", "ipsec2", "169.254.3.2", 20)
    route("aws", "del", "192.168.10.0/24", "ipsec2", "169.254.3.1", 20)
    print("=== MODULE 8 : GRE/BGP et secours IPsec (local) ===", flush=True)
    for node, i in (("siege",1),("aws",2)):
        opposite = 3-i
        conf = bird_config(node, [
            ("dx", f"169.254.1.{i}", f"169.254.1.{opposite}"),
            ("vpn", f"169.254.3.{i}", f"169.254.3.{opposite}")
        ])
        command([str(bird), "-p", "-c", str(conf)])
        launch(node,str(bird),"-f","-c",str(conf),"-s",str(work/f"{node}.sock"),"-P",str(work/f"{node}.pid"))
    await_route("dx0")
    for _ in range(50):
        backup = bird_show("aws", "show", "route", "for", "192.168.10.0/24", "all", show=False)
        if "65010 65010 65010 65010" in backup:
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Route de secours avec AS-path allongé non observée")
    bird_show("siege","show","protocols")
    bird_show("siege","show","route","for","10.0.0.0/16","all")
    bird_show("aws","show","route","for","192.168.10.0/24","all")
    check("siege", ping)
    print("$ siege/aws# ip link set dx0 down", flush=True)
    start = time.monotonic()
    for node in ("siege","aws"):
        run(node,"ip","link","set","dx0","down")
    elapsed = await_route("ipsec2", start)
    check("siege", ping)
    print(f"Convergence aller sur le secours : {elapsed:.2f} s", flush=True)
    print("$ siege/aws# ip link set dx0 up", flush=True)
    for node in ("siege","aws"):
        run(node,"ip","link","set","dx0","up")
    await_route("dx0")
    check("siege", ping)
    print("=== FIN MODULE 8 ===", flush=True)


if __name__ == "__main__":
    try:
        main()
    finally:
        for child in reversed(processes):
            with contextlib.suppress(ProcessLookupError):
                child.terminate()
        for child in reversed(processes):
            with contextlib.suppress(subprocess.TimeoutExpired):
                child.wait(timeout=2)
