from .seam_provider import SeamProvider


def get_lock_provider():
    return SeamProvider()


def get_thermostat_provider():
    return SeamProvider()


def get_noise_provider():
    return SeamProvider()
