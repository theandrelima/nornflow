"""
Guidance for developement of any other "NORNFLOW_SPECIAL_FILTER_KEYS" that may be added in the future.

This module contains filter functions that follow strict conventions to work with
NornFlow's dynamic filter resolution system. When adding new filters, you MUST
follow these conventions:

NAMING CONVENTION:
- Filter functions MUST be named 'filter_by_X' where X is the filter key used in 
  inventory_filters (e.g., 'filter_by_hosts' for filter key 'hosts')

PARAMETER STRUCTURE:
- MUST have exactly 2 parameters:
  1. First parameter MUST be named 'host' (Nornir Host object)
  2. Second parameter receives the filter values and SHOULD be named semantically 
     related to the filter purpose

RETURN VALUE:
- MUST return a boolean indicating whether the host meets the filter criteria
- True = host is included, False = host is excluded

DISCOVERY MECHANISM:
- Functions in this module are dynamically discovered by name
- No manual registration is required
- The filter key in inventory_filters directly maps to the function name

Example:
    # Define a new filter function
    def filter_by_platform(host: Host, platform: str) -> bool:
        \"\"\"Filter hosts by platform type.\"\"\"
        return host.platform == platform
    
    # Can be used in inventory_filters as:
    inventory_filters = {"platform": "ios"}
"""

from nornir.core.inventory import Host


def filter_by_hosts(host: Host, hosts: list[str]) -> bool:
    """
    Filter hosts by hostname.

    Args:
        host (Host): The Nornir host object to check
        hosts (list[str]): List of hostnames to match against

    Returns:
        bool: True if host's name is in the hosts list
    """
    return host.name in hosts


def filter_by_groups(host: Host, groups: list[str]) -> bool:
    """
    Filter hosts by group membership.

    Args:
        host (Host): The Nornir host object to check
        groups (list[str]): List of group names to match against

    Returns:
        bool: True if host belongs to any of the specified groups
    """
    return any(group in host.groups for group in groups)
