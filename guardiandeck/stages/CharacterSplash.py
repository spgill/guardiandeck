# stdlib imports
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

        # Start the polling thread
        self.pollingThread = threading.Thread(target=self.poll)
        self.pollingThread.start()

    def destroy(self):
        if self.pollingThread.is_alive():
            self.killFlag = True
            self.pollingThread.join()

    def poll(self):
        # Get character data
        character = self.options["character"]
        characterId = character["characterId"]

        # Start the loop
        while True:
            # This is the escape hatch
            if self.killFlag:
                return

            # Get the character inventory
            self.deck.verifyAuth()
            self.inventoryData = self.deck.apiCall(
                f"/Platform/Destiny2/{self.deck.membershipType}/Profile/{self.deck.membershipId}/Character/{characterId}/?components=201,205,300"
            )

            # Hash the data
            currentHash = hashlib.blake2b(
                marshal.dumps(self.inventoryData)
            ).hexdigest()

            # If the hash has changed, then update the stored data
            if currentHash != self.inventoryHash:
                self.inventoryHash = currentHash

                # Insert icons for the three equipped weapons
                for item in self.inventoryData["equipment"]["data"]["items"]:
                    bucketHash = item["bucketHash"]
                    if bucketHash in self.buckets:
                        bucketIndex = self.buckets.index(bucketHash)

                        self.keys[4][bucketIndex] = helpers.generateItemIcon(
                            self.deck, self.inventoryData, item
                        )

                # Trigger a re-render
                if self.active:
                    self.deck.renderStack()

            # Sleep until the next poll
            time.sleep(5)
            continue

    def press(self, x, y):
        if x == 4:
            bucketIndex = y

            # Create a new frame for the chosen bucket
            self.deck.pushFrame(
                BucketMenuStage,
                {
                    "inventoryData": self.inventoryData,
                    "bucketHash": self.buckets[bucketIndex],
                    "bucketIndex": bucketIndex,
                },
            )
