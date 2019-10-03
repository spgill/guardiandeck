# stdlib imports
import datetime
import pathlib
import pprint
from PIL import Image
import sys
import time
import uuid
import webbrowser

# vendor imports
import requests

# local imports
import spgill.util.chassis as chassis
from StreamDeck import StreamDeck


GuardianChassis = chassis.createChassis(
    props={
        # Auth props
        'bungieId': '',
        'token': '',
        'tokenExpiration': '',
        'refreshToken': '',
        'refreshTokenExpiration': '',

        # Player props
        'destinyId': '',
        'characterId': '',
    }
)


class GuardianDeck(GuardianChassis):
    # Bungie URL root
    root = 'https://www.bungie.net'

    def __init__(self):
        # Open and read the __apiKey__ file
        self.apiKeyPath = pathlib.Path(sys.argv[0]).absolute() / '__apiKey__'
        with self.apiKeyPath.open('r') as apiKeyFile:
            self.apiKey = apiKeyFile.read().strip()

        # Open up a connection to the stream deck
        self.openDeck()

        # Create the api session
        self.apiSession = requests.Session()

        # Fetch the user information (which includes updating auth info)
        self.fetchUserInfo()

        # Start the event loop
        self.startLoop()

        # Close the connection to the deck
        self.closeDeck()

    def verifyAuth(self):
        # Get and decode the timestamps
        now, tokenExpiration, refreshTokenExpiration = None, None, None
        if self.store.props.token.get():
            now = datetime.datetime.now()
            tokenExpiration = datetime.datetime.fromisoformat(
                self.store.props.tokenExpiration.get()
            )
            refreshTokenExpiration = datetime.datetime.fromisoformat(
                self.store.props.refreshTokenExpiration.get()
            )

        # We have to fetch a whole new token if;
        # 1) there is no token at all
        # or
        # 2) the refresh token is expired
        if not self.store.props.token.get()\
           or refreshTokenExpiration <= now:
            print('Fetching new token...')

            # Start an authorization request with the spgill server
            authState = str(uuid.uuid4())
            startUrl = f'https://home.spgill.me/bungie/start/{authState}'
            webbrowser.open_new_tab(startUrl)

            # Poll the server for a the token data
            tokenData = None
            while not tokenData:
                print('Polling...')
                pollResp = requests.get(
                    url=f'https://home.spgill.me/bungie/poll/{authState}'
                )
                if pollResp.status_code != 404:
                    tokenData = pollResp.json()
                    continue
                time.sleep(0.25)

            # Store all the token data in the chassis
            self.storeTokenResponse(tokenData)

        # If just the normal token is expired, then just
        # request a refresh
        elif tokenExpiration <= now:
            print('Refreshing token...')

            # Ask the server for a refresh
            refreshResp = requests.get(
                url=f'https://home.spgill.me/bungie/refresh',
                data={
                    'refresh_token': self.store.props.refreshToken.get(),
                }
            )
            self.storeTokenResponse(refreshResp.json())

    def storeTokenResponse(self, response):
        self.store.props.bungieId.set(
            response['membership_id']
        )
        self.store.props.token.set(
            response['access_token']
        )
        self.store.props.tokenExpiration.set(
            (datetime.datetime.now() + datetime.timedelta(
                seconds=response['expires_in']
            )).isoformat()
        )
        self.store.props.refreshToken.set(
            response['refresh_token']
        )
        self.store.props.refreshTokenExpiration.set(
            (datetime.datetime.now() + datetime.timedelta(
                seconds=response['refresh_expires_in']
            )).isoformat()
        )
        self.storeSync()

    def apiCall(self, route, data={}, method='get', **kwargs):
        # Construct the headers
        headers = {
            'X-API-Key': self.apiKey,
            'Authorization': f'Bearer {self.store.props.token.get()}'
        }

        # Make the request
        response = getattr(self.apiSession, method.lower())(
            url=self.root + route,
            headers=headers,
            data=data,
            **kwargs,
        )

        # Just return the json. Further functionality may
        # be needed in the future
        return response.json().get('Response', response)

    def fetchImage(self, route):
        # Fetch the image
        fetchedImage = Image.open(
            requests.get(
                url=self.root + route,
                stream=True,
            ).raw
        )

        # Load it into memory and return
        fetchedImage.load()
        return fetchedImage

    def prepareImage(self, image):
        # First, resize the image
        resized = image.resize(
            size=(72, 72),
            resample=Image.LANCZOS,
        )

        # Correct image channel order
        (r, g, b) = resized.split()
        corrected = Image.merge(
            mode='RGB',
            bands=(b, g, r),
        )

        # Return the bytes of the image
        return corrected.tobytes()

    def fetchUserInfo(self):
        self.verifyAuth()

        # Request the user info
        bungieId = self.store.props.bungieId.get()
        player = self.apiCall(
            f'/Platform/User/GetMembershipsById/{bungieId}/0/'
        )

        # Store the destiny ID
        self.store.props.destinyId.set(
            player['destinyMemberships'][0]['membershipId']
        )

        # Request the player's destiny profile
        profile = self.apiCall(
            f'/Platform/Destiny2/4/Profile/' +
            self.store.props.destinyId.get() +
            '/?components=200'
        )

        # Iterate through characters and put them on the deck
        # for NOW just take the first one
        characters = profile['characters']['data']
        for i, characterId in enumerate(characters):
            # character = characters[characterId]
            # self.deck.set_key_image(
            #     self.key(i, 1),
            #     self.prepareImage(
            #         self.fetchImage(
            #             character['emblemPath']
            #         ),
            #     ),
            # )
            self.store.props.characterId.set(characterId)

        self.storeSync()


    def openDeck(self):
        # Create a manager
        self.deckManager = StreamDeck.DeviceManager()
        decks = self.deckManager.enumerate()

        # If there are no decks, throw an error
        if len(decks) < 1:
            raise RuntimeError(
                'No Stream Decks detected :('
            )

        # Capture the first deck, open it, and reset it
        self.deck = decks[0]
        self.deck.open()
        self.deck.reset()

    def closeDeck(self):
        self.deck.close()

    def key(self, x, y):
        return (y * 5) + (4 - x)

    def startLoop(self):
        # try:
        #     while True:
        #         pass
        # except KeyboardInterrupt:
        #     return

        inventory = self.apiCall(
            '/Platform/Destiny2/4/Profile/' +
            self.store.props.destinyId.get() +
            '/Character/' +
            self.store.props.characterId.get() +
            '/?components=205'
        )

        pprint.pprint(inventory)