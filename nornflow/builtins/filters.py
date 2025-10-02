"""
NornFlow provided filters for Nornir inventory.
"""

from nornir.core.inventory import Host


def hosts(host: Host, hosts: list[str]) -> bool:
    """
    Filter hosts by hostname.

    Args:
        host (Host): The Nornir host object to check
        hosts (list[str]): List of hostnames to match against

    Returns:
        bool: True if host's name is in the hosts list
    """
    if not hosts:
        return True
    return host.name in hosts


def groups(host: Host, groups: list[str]) -> bool:
    """
    Filter hosts by group membership.

    Args:
        host (Host): The Nornir host object to check
        groups (list[str]): List of group names to match against

    Returns:
        bool: True if host belongs to any of the specified groups
    """
    if not groups:
        return True
    return any(group in host.groups for group in groups)
