class NornflowSettings:
    """
    This class is used to hold norsible settings parameters, which have sensible
    defaults that can be overwritten by the environment variables.
    """
    pass


GLOBAL_CONFIGS = None


def get_config():
    global GLOBAL_CONFIGS

    if GLOBAL_CONFIGS is None:
        GLOBAL_CONFIGS = NornflowSettings()

    return GLOBAL_CONFIGS