from model import Auction
from message import AuctionInformationResponse


def auction2auction_information_response(
    request_id: str, auction: Auction
) -> AuctionInformationResponse:
    """Converts an auction to an auction information response.

    Args:
        request_id (str): The request id of the auction information request.
        auction (Auction): The auction to convert.

    Returns:
        AuctionInformationResponse: The converted auction.
    """
    return AuctionInformationResponse(
        _id=request_id,
        auction_id=auction._id,
        item=auction._item,
        price=auction._price,
        time=auction._time,
        multicast_group=auction._multicast_group,
        multicast_port=auction._multicast_port,
        auction_state=auction._auction_state,
        bid_history=auction._bid_history,
        winner=auction._winner,
    )


def auction_information_response2auction(
    auction_information_response: AuctionInformationResponse,
) -> Auction:
    """Converts an auction information response to an auction.

    Args:
        auction_information_response (AuctionInformationResponse): The auction information response to convert.

    Returns:
        Auction: The converted auction.
    """
    auction = Auction(
        _id=auction_information_response.auction_id,
        item=auction_information_response.item,
        price=auction_information_response.price,
        time=auction_information_response.time,
        multicast_group=auction_information_response.multicast_group,
        multicast_port=auction_information_response.multicast_port,
    )
    auction._auction_state = auction_information_response.auction_state
    auction._bid_history = auction_information_response.bid_history
    auction._winner = auction_information_response.winner
    return auction
