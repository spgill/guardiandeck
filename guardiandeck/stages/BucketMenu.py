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
        self.inventoryData = self.options["inventoryData"]

        # Copy icon from the previous bucket
        self.keys[4][0] = self.deck._stack[1].keys[4][self.bucketIndex]

        # Figure out every item in this bucket
        bucketItems = []
        for item in self.inventoryData["inventory"]["data"]["items"]:
            if item["bucketHash"] == self.bucketHash:
                bucketItems.append(item)

        print("BUCKET ITEMS")

        # Insert icons
        for i, item in enumerate(bucketItems):
            # Convert index to local 3x3 grid (in reverse x-order)
            localX = i % 3
            localY = (i - localX) // 3
            localX = 3 - localX

            itemInstanceInfo = self.inventoryData["itemComponents"][
                "instances"
            ]["data"][item["itemInstanceId"]]
            itemInfo = self.deck.manifestGet(
                "DestinyInventoryItemDefinition", item["itemHash"]
            )

            print(f'{i}: {itemInfo["displayProperties"]["name"]}')

            self.keys[localX][localY] = helpers.generateItemIcon(
                self.deck, self.inventoryData, item
            )

        print()

    def press(self, x, y):
        if x == 4:
            self.deck.popFrame()

