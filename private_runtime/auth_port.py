"""Trusted bootstrap dependency only. No class/module selection from requests/config."""
from private_runtime.registry import current

def authenticated(config,consume,epoch):
    return current().authentication_factory(config,consume,epoch)
