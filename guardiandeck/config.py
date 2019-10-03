# vendor imports
from spgill.util.chassis import Chassis


chassis = Chassis(
    props={
        # Auth props
        "bungieId": "",
        "token": "",
        "tokenExpiration": "",
        "refreshToken": "",
        "refreshTokenExpiration": "",
        # Player props
        "destinyId": "",
        "characterId": "",
    }
)
