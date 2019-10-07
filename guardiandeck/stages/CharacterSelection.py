# stdlib imports
import pprint

# vendor imports
from PIL import Image, ImageDraw
from StreamDeck.ImageHelpers import PILHelper

# local imports
from guardiandeck.config import chassis, font12
from guardiandeck.frame import InteractionFrame
from guardiandeck.stages.CharacterSplash import CharacterSplashStage


class CharacterSelectionStage(InteractionFrame):
    def setup(self):
        # Place choose graphic
        self.keys[2][0] = self.deck.prepareImage(
            Image.open(chassis.store.root / "assets" / "choose.png")
        )

        # Parse the characters
        self.characters = self.options["characters"]
        self.selections = []
        for i, characterId in enumerate(self.characters):
            character = self.characters[characterId]
            self.selections.append(characterId)

            # Insert character emblem
            self.keys[i + 1][1] = character["emblemPath"]

            # Insert information tile below
            self.keys[i + 1][2] = self.infoTile(character)

        blank = self.deck.prepareImage(
            Image.new("RGB", (72, 72), (50, 50, 50))
        )

        # Add empty selections
        for i in range(3 - len(self.characters)):
            self.keys[3 - i][1] = blank

    def infoTile(self, character):
        # Create blank canvas
        canvas = Image.new("RGB", (72, 72))
        brush = ImageDraw.Draw(canvas)

        # Get the character details
        charRace = self.deck.manifestGet(
            "DestinyRaceDefinition", character["raceHash"]
        )["displayProperties"]["name"]
        charClass = self.deck.manifestGet(
            "DestinyClassDefinition", character["classHash"]
        )["displayProperties"]["name"]

        # Write light level
        brush.multiline_text(
            (8, 8),
            f'lvl {character["light"]}\n{charRace}\n{charClass}',
            fill=(255, 255, 255),
            font=font12,
        )

        return self.deck.prepareImage(canvas)

    def press(self, x, y):
        # Check for the range that the buttons are in
        if x >= 1 and x <= 3 and y == 1:
            index = x - 1
            if index < len(self.selections):
                characterId = self.selections[index]
                self.deck.pushFrame(
                    CharacterSplashStage,
                    {"character": self.characters[characterId]},
                )
