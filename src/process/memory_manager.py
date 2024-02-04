from multiprocessing.managers import BaseManager

from constant import managed as mng
from model import Auction, Leader, AuctionAnnouncementStore, AuctionPeersStore


# General Memory Manager
class Manager(BaseManager):
    pass


# Register managed objects
Manager.register(mng.AUCTION, Auction)
Manager.register(mng.LEADER, Leader)
Manager.register(mng.AUCTION_ANNOUNCEMENT_STORE, AuctionAnnouncementStore)
Manager.register(mng.AUCTION_PEERS_STORE, AuctionPeersStore)
