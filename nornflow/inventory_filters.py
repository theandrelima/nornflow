from nornir.core.inventory import Host


def filter_by_hostname(host: Host, hostnames: list[str]) -> bool:
    """
    Filter hosts by hostname.

    Args:
        host (Host): The Nornir host object to check
        hostnames (List[str]): List of hostnames to match against

    Returns:
        bool: True if host's name is in the hostnames list
    """
    return host.name in hostnames


def filter_by_groups(host: Host, groups: list[str]) -> bool:
    """
    Filter hosts by group membership.

    Args:
        host (Host): The Nornir host object to check
        groups (List[str]): List of group names to match against

    Returns:
        bool: True if host belongs to any of the specified groups
    """
    return any(group in host.groups for group in groups)
