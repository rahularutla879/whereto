"""Only the transport changes in this synthetic adapter; parent guards remain."""
from experiments.ordinary_network.client import Client

def main():
 from experiments.ordinary_network.dns import install
 install()
 from experiments.ordinary_network.metrics import install as measure
 measure()
 from experiments.hosted_identity import server as host
 from experiments.service_isolation import runtime
 from experiments.ordinary_ui import server as ui
 host.Client=Client;runtime.Client=Client;ui.Client=Client
 from experiments.ordinary_network.identity import verify
 from experiments.ordinary_ui import identity as ui_identity
 ui_identity.verify=verify
 ui.main()
if __name__=='__main__':main()
