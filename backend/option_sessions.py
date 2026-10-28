"""Bounded active computation continuations. No disk cache or cross-outing reuse."""
from collections import OrderedDict
from secrets import token_urlsafe
from threading import Lock, Timer
from time import monotonic
from backend.places import DiscoveryError


class OptionSessions:
    def __init__(self):
        self.entries = OrderedDict()
        self.lock = Lock()

    def create(self, context):
        with self.lock:
            now = monotonic()
            self.entries = OrderedDict((k, v) for k, v in self.entries.items() if now-v[0] < 600)
            while len(self.entries) >= 20:
                self.entries.popitem(last=False)
            token = token_urlsafe(32)
            self.entries[token] = (now, context, Lock())
            expiry = Timer(600, self.expire, args=(token,))
            expiry.daemon = True
            expiry.start()
            return token

    def expire(self, token):
        with self.lock:
            self.entries.pop(token, None)

    def get(self, token):
        with self.lock:
            entry = self.entries.get(token)
            if not entry or monotonic()-entry[0] >= 600:
                self.entries.pop(token, None)
                raise DiscoveryError('expired', 'The 10-minute search session has expired; this does not mean your outing date has passed. Saved pages remain viewable. Regenerate to start a new search; previous no-repeat history will reset.')
            return entry[1], entry[2]


option_sessions = OptionSessions()
