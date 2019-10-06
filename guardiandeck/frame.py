class InteractionFrame:
    def __init__(self, deck, options={}):
        # Copy args into instance
        self.deck = deck
        self.options = options

        # Create empty grid structure for keys
        self.keys = [[None for y in range(3)] for x in range(5)]

        # Call setup function
        self.setup()

    def setup(self):
        pass

    def destroy(self):
        pass

    def press(self, x, y):
        pass
