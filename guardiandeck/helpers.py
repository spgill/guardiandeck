# vendor imports
from PIL import Image, ImageDraw

# local imports
import guardiandeck.config as config

damageColors = [
    ("#aeaeaeb4", "black"),  # kinetic
    ("#98d0efb4", "black"),  # arc
    ("#f6853ab4", "white"),  # solar
    ("#bf97d5b4", "white"),  # void
]

ammoIconRoutes = {
    1: "/common/destiny2_content/icons/dc4bb9bcdd4ae8a83fb9007a51d7d711.png",  # primary
    2: "/common/destiny2_content/icons/b6d3805ca8400272b7ee7935b0b75c79.png",  # special
    3: "/common/destiny2_content/icons/9fa60d5a99c9ff9cea0fb6dd690f26ec.png",  # heavy
}


def generateItemIcon(deck, inventoryData, item):
    # Fetch the item info from the manafest
    itemInfo = deck.manifestGet(
        "DestinyInventoryItemDefinition", item["itemHash"]
    )

    # Get the item instance info
    itemInstanceInfo = inventoryData["itemComponents"]["instances"]["data"][
        item["itemInstanceId"]
    ]

    # Start with the item icon
    tile = deck.fetchCachedImage(itemInfo["displayProperties"]["icon"]).resize(
        (72, 72), resample=Image.LANCZOS
    )
    canvas = ImageDraw.Draw(tile, "RGBA")

    # print("INSTANCE", itemInstanceInfo)
    [bgColor, fgColor] = damageColors[
        max(itemInstanceInfo["damageType"] - 1, 0)
    ]

    # Draw a box over the bottom
    canvas.rectangle((0, 56, 50, 72), fill=bgColor)
    canvas.text(
        (4, 54),
        str(itemInstanceInfo["primaryStat"]["value"]),
        fill=fgColor,
        font=config.font12,
    )

    # Paste the ammo type icon
    canvas.rectangle((50, 56, 72, 72), fill="#323232")
    ammoIcon = (
        deck.fetchCachedImage(
            ammoIconRoutes[itemInfo["equippingBlock"]["ammoType"]]
        )
        .resize((20, 20), resample=Image.LANCZOS)
        .convert("RGBA")
    )

    tile.paste(ammoIcon, (52, 54), ammoIcon)
    # tile.alpha_composite(ammoIcon, (0, 0))

    return deck.prepareImage(tile)
