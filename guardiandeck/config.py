# vendor imports
from spgill.util.chassis import Chassis


chassis = Chassis(
    proxy="~/.guardiandeck.json",
    props={
        # Use config
        "apiKey": "",
        # Auth props
        "bungieId": "",
        "token": "",
        "tokenExpiration": "",
        "refreshToken": "",
        "refreshTokenExpiration": "",
        # Player props
        "membershipId": "",
        "membershipType": None,
        "characterId": "",
    },
)
