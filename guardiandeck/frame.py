# vendor imports
from PIL import Image, ImageDraw

# local imports
import guardiandeck.config as config


class InteractionFrame:
    def __init__(self, deck, active, options={}):
        # Copy args into instance
        self.deck = deck
        self.active = active
        self.options = options

        # Create empty grid structure for keys
        self.keys = [[None for y in range(3)] for x in range(5)]

    def setActive(self, flag):
        self.active = flag

    def setup(self):
        pass

    def destroy(self):
        pass

    async def press(self, x, y):
        pass


class LoadingFrame(InteractionFrame):
    def setup(self):
        tile = Image.new(mode="RGB", size=(72, 72))
        canvas = ImageDraw.Draw(tile)

        canvas.text(
            (12, 26), "Loading...", fill=(255, 255, 255), font=config.font12
        )

        self.keys[2][1] = self.deck.prepareImage(tile)
