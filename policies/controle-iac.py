"""Contrôles ciblés des CIDR et des ouvertures de ports d'administration."""

import ipaddress
import json
import sys
from pathlib import Path

import yaml

RESTRICTED_PORTS = (22, 23, 3389, 5432, 3306)


class TemplateLoader(yaml.SafeLoader):
    pass


def intrinsic(loader, suffix, node):
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return loader.construct_scalar(node)


TemplateLoader.add_multi_constructor("!", intrinsic)


def ingress_objects(node):
    if isinstance(node, list):
        for item in node:
            yield from ingress_objects(item)
    elif isinstance(node, dict):
        yield node


def failures(template):
    for name, resource in template.get("Resources", {}).items():
        properties = resource.get("Properties", {})
        if resource["Type"] == "AWS::EC2::SecurityGroup":
            items = ingress_objects(properties.get("SecurityGroupIngress", []))
        elif resource["Type"] == "AWS::EC2::SecurityGroupIngress":
            items = [properties]
        else:
            continue
        for rule in items:
            if not any(rule.get(key) in ("0.0.0.0/0", "::/0") for key in ("CidrIp", "CidrIpv6")):
                continue
            start, end = rule.get("FromPort"), rule.get("ToPort")
            all_protocols = str(rule.get("IpProtocol")) == "-1"
            tcp = str(rule.get("IpProtocol")).lower() in ("tcp", "6")
            if all_protocols or (tcp and (
                not isinstance(start, int) or not isinstance(end, int)
                or any(start <= port <= end for port in RESTRICTED_PORTS)
            )):
                yield f"{name} ouvre un port d’administration à Internet"


def validate_cidrs(directory):
    config = [
        json.loads((directory / f"{stage}.json").read_text(encoding="utf-8"))
        for stage in ("dev", "prod")
    ]
    networks = [ipaddress.ip_network(values["CidrVpc"]) for values in config]
    if networks[0].overlaps(networks[1]):
        yield "Les VPC dev et prod se chevauchent"
    for values, vpc in zip(config, networks):
        subnets = [ipaddress.ip_network(values[key]) for key in ("PublicACidr", "PublicBCidr", "PrivateACidr")]
        if any(not subnet.subnet_of(vpc) for subnet in subnets):
            yield f"Un sous-réseau sort du VPC {values['Environnement']}"
        if any(a.overlaps(b) for i, a in enumerate(subnets) for b in subnets[i + 1:]):
            yield f"Les sous-réseaux se chevauchent dans {values['Environnement']}"
        for key, subnet in zip(("WebIp", "WebBackupIp", "AppIp"), subnets):
            if ipaddress.ip_address(values[key]) not in subnet:
                yield f"{key} est hors de son sous-réseau {values['Environnement']}"


def main():
    issues = list(validate_cidrs(Path("parameters")))
    for path in map(Path, sys.argv[1:]):
        template = yaml.load(path.read_text(encoding="utf-8"), Loader=TemplateLoader)
        issues.extend(f"{path}: {message}" for message in failures(template))
    if issues:
        raise SystemExit("\n".join(issues))
    print("CIDR distincts et aucun port d’administration public dans les templates contrôlés.")


if __name__ == "__main__":
    main()
