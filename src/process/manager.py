from multiprocessing.managers import BaseManager

from constant import managed as mng
from model import Auction, AuctionAnnouncementStore


# General Memory Manager
class Manager(BaseManager):
    pass


# Register managed objects
Manager.register(mng.AUCTION, Auction)
Manager.register(mng.AUCTION_ANNOUNCEMENT_STORE, AuctionAnnouncementStore)
