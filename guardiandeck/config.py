# stdlib imports
import pathlib

# vendor imports
from PIL import ImageFont
from spgill.util.chassis import Chassis


bungie = "https://www.bungie.net"


chassis = Chassis(
    root=pathlib.Path(__file__).parent,
    uuid="68da549c-5018-4c02-b6a6-1786ef16275a",
    proxy="~/.guardiandeck.json",
    props={
        # Use config
        "apiKey": "ab4da0d60e4943d1997be3cb2773a6e7",
        # Auth props
        "bungieId": "",
        "token": "",
        "tokenExpiration": "",
        "refreshToken": "",
        "refreshTokenExpiration": "",
        # Manifest data
        "manifestVersion": "",
        "manifestContentName": "",
        # Player props
        "membershipId": "",
        "membershipType": None,
        "characterId": "",
    },
)


font12 = ImageFont.truetype(
    font=str(chassis.store.root / "assets" / "IBMPlexSans-Regular.ttf"),
    size=12,
)
