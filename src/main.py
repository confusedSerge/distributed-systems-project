import tomllib
from util import Multicast

with open("./config/config.dev.toml", "rb") as f:
    config = tomllib.load(f)

sender = True

if sender:
    print("Sender")
    multicast = Multicast(
        group=config["multicast"]["discovery-group"]["group"],
        port=config["multicast"]["discovery-group"]["port"],
        ttl=config["multicast"]["discovery-group"]["ttl"],
    )
    multicast.send("Hello World!")
else:
    print("Receiver")
    multicast = Multicast(
        group=config["multicast"]["discovery-group"]["group"],
        port=config["multicast"]["discovery-group"]["port"],
        ttl=config["multicast"]["discovery-group"]["ttl"],
    )
    print(multicast.receive())
