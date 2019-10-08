# stdlib imports
import pprint

# vendor imports
from PIL import Image, ImageDraw
from StreamDeck.ImageHelpers import PILHelper

# local imports
from guardiandeck.config import chassis, font12
from guardiandeck.frame import InteractionFrame
import guardiandeck.helpers as helpers


class BucketMenuStage(InteractionFrame):
    def setup(self):
        self.bucketIndex = self.options["bucketIndex"]
        self.bucketHash = self.options["bucketHash"]

        # Copy icon from the previous bucket
        self.keys[4][0] = self.deck._stack[1].keys[4][self.bucketIndex]

        # Figure out every item in this bucket
        bucketItems = []
        for item in self.deck.inventoryData["inventory"]["data"]["items"]:
            if item["bucketHash"] == self.bucketHash:
                bucketItems.append(item)

        print("BUCKET ITEMS")

        self.selections = {}

        # Insert icons
        for i, item in enumerate(bucketItems):
            # Convert index to local 3x3 grid (in reverse x-order)
            localX = i % 3
            localY = (i - localX) // 3
            localX = 3 - localX

            itemInstanceInfo = self.deck.inventoryData["itemComponents"][
                "instances"
            ]["data"][item["itemInstanceId"]]
            itemInfo = self.deck.manifestGet(
                "DestinyInventoryItemDefinition", item["itemHash"]
            )

            print(f'{i}: {itemInfo["displayProperties"]["name"]}')
            print(item)

            self.selections[(localX, localY)] = item["itemInstanceId"]

            self.keys[localX][localY] = helpers.generateItemIcon(
                self.deck, self.deck.inventoryData, item
            )

        print()

    async def press(self, x, y):
        if x == 4:
            self.deck.popFrame()
        elif x > 0 and x < 4:
            itemInstanceId = self.selections[(x, y)]

            response = self.deck.apiCall(
                "/Platform/Destiny2/Actions/Items/EquipItem/",
                method="post",
                data={
                    "itemId": itemInstanceId,
                    "characterId": self.deck.characterId,
                    "membershipType": self.deck.membershipType,
                },
            )

            print("equip response", response)

