"""Same real FastAPI/request-management/owned ordinary boundary, HTTPS RPC client."""
def main():
 from experiments.ordinary_network.dns import install
 install()
 from experiments.ordinary_network.metrics import install as measure
 measure()
 from experiments.ordinary_ui import public_server as public
 from experiments.ordinary_network.client import Client
 from experiments.ordinary_network.identity import verify
 from experiments.ordinary_ui import identity
 identity.verify=verify;public.Client=Client
 public.main()
if __name__=='__main__':main()
