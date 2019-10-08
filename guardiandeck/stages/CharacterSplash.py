# stdlib imports
import asyncio
import hashlib
import json
import marshal
import threading
import time

# vendor imports

# local imports
from guardiandeck.config import chassis
import guardiandeck.helpers as helpers
from guardiandeck.frame import InteractionFrame
from guardiandeck.stages.BucketMenu import BucketMenuStage


class CharacterSplashStage(InteractionFrame):
    def setup(self):
        # Variables
        self.killFlag = False
        self.inventoryHash = ""

        # Determine which buckets we need to track
        self.buckets = [None for i in range(3)]
        for bucket in self.deck.manifestGetAll(
            "DestinyInventoryBucketDefinition"
        ):
            index = bucket.get("index", None)
            if index >= 0 and index <= 2:
                self.buckets[index] = bucket["hash"]

        # Subscribe to inventory changes
        self.deck.subscribeInventory(self.updateInventory)

        # If inventory data already exists, call an immediate update
        if self.deck.inventoryData:
            print("Calling first update")
            asyncio.run(self.updateInventory())

    # def destroy(self):
    #     if self.pollingThread.is_alive():
    #         self.killFlag = True
    #         self.pollingThread.join()

    async def updateInventory(self):
        # Get character data
        # character = self.options["character"]
        # characterId = character["characterId"]

        print("Update!")

        # Insert icons for the three equipped weapons
        for item in self.deck.inventoryData["equipment"]["data"]["items"]:
            bucketHash = item["bucketHash"]
            if bucketHash in self.buckets:
                bucketIndex = self.buckets.index(bucketHash)

                self.keys[4][bucketIndex] = helpers.generateItemIcon(
                    self.deck, self.deck.inventoryData, item
                )

        # Trigger a re-render
        if self.active:
            self.deck.renderStack()

    async def press(self, x, y):
        if x == 4:
            bucketIndex = y

            # Create a new frame for the chosen bucket
            self.deck.pushFrame(
                BucketMenuStage,
                {
                    "bucketHash": self.buckets[bucketIndex],
                    "bucketIndex": bucketIndex,
                },
            )
