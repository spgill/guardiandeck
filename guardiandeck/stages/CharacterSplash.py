# stdlib imports
import json
import pprint

# vendor imports
from PIL import Image, ImageDraw, ImageFont
from StreamDeck.ImageHelpers import PILHelper

# local imports
from guardiandeck.config import bungie, chassis, font12
from guardiandeck.frame import InteractionFrame


class CharacterSplashStage(InteractionFrame):
    def setup(self):
        character = self.options["character"]
        characterId = character["characterId"]

        # Get the character inventory
        response = self.deck.apiCall(
            f"/Platform/Destiny2/{self.deck.membershipType}/Profile/{self.deck.membershipId}/Character/{characterId}/?components=201,205"
        )

        pprint.pprint(response)

        json.dump(
            response,
            open(chassis.store.path / "cache" / "dump.json", "w"),
            indent=2,
            sort_keys=True,
        )

        buckets = {}

        unabridged = (
            response["equipment"]["data"]["items"]
            + response["inventory"]["data"]["items"]
        )

        for item in unabridged:
            if item["bucketHash"] not in buckets:
                buckets[item["bucketHash"]] = 0
            buckets[item["bucketHash"]] += 1

            definition = self.deck.manifestGet(
                "DestinyInventoryItemDefinition", item["itemHash"]
            )
            print(definition["displayProperties"]["name"])

        print("BUCKETS")

        for bucket in buckets:
            definition = self.deck.manifestGet(
                "DestinyInventoryBucketDefinition", bucket
            )
            if "name" in definition["displayProperties"]:
                print(
                    f'{definition["displayProperties"]["name"]} [{bucket}]: {buckets[bucket]}'
                )

