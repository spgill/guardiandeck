# stdlib imports
import datetime
import os
import pathlib
import pprint
from PIL import Image
import json
import json.decoder
import sqlite3
import sys
import threading
import time
import traceback
import urllib.request
import uuid
import webbrowser
import zipfile

# vendor imports
import requests
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

# local imports
import guardiandeck.config as config
from guardiandeck.ext.threadbox import MetaBox
from guardiandeck.stages.CharacterSelection import CharacterSelectionStage


class APIError(Exception):
    pass


class GuardianDeck:
    def __init__(self):
        # Gotta make sure there's an API key configured
        self.apiKey = config.chassis.props.apiKey.get()
        if not self.apiKey:
            raise RuntimeError("No API key configured!")

        # Open up a connection to the stream deck
        self.openDeck()

        # Setup the frame stack
        self.setupStack()

        # Create the api session
        self.apiSession = requests.Session()

        # Fetch and verify manifest information
        self.fetchManifestData()

        # Fetch the user information (which includes updating auth info)
        self.fetchUserInfo()

        # Start the event loop
        self.startLoop()

        # Close the connection to the deck
        self.closeDeck()

    def verifyAuth(self):
        # Get and decode the timestamps
        now, tokenExpiration, refreshTokenExpiration = None, None, None
        if config.chassis.props.token.get():
            now = datetime.datetime.now()
            tokenExpiration = datetime.datetime.fromisoformat(
                config.chassis.props.tokenExpiration.get()
            )
            refreshTokenExpiration = datetime.datetime.fromisoformat(
                config.chassis.props.refreshTokenExpiration.get()
            )

        # We have to fetch a whole new token if;
        # 1) there is no token at all
        # or
        # 2) the refresh token is expired
        if (
            not config.chassis.props.token.get()
            or refreshTokenExpiration <= now
        ):
            print("Fetching new token...")

            # Start an authorization request with the spgill server
            authState = str(uuid.uuid4())
            startUrl = f"https://home.spgill.me/bungie/start/{authState}"
            webbrowser.open_new_tab(startUrl)

            # Poll the server for a the token data
            tokenData = None
            while not tokenData:
                print("Polling...")
                pollResp = requests.get(
                    url=f"https://home.spgill.me/bungie/poll/{authState}"
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
            print("Refreshing token...")

            # Ask the server for a refresh
            refreshResp = requests.get(
                url=f"https://home.spgill.me/bungie/refresh",
                data={
                    "refresh_token": config.chassis.props.refreshToken.get()
                },
            )
            self.storeTokenResponse(refreshResp.json())

    def storeTokenResponse(self, response):
        config.chassis.props.bungieId.set(response["membership_id"])
        config.chassis.props.token.set(response["access_token"])
        config.chassis.props.tokenExpiration.set(
            (
                datetime.datetime.now()
                + datetime.timedelta(seconds=response["expires_in"])
            ).isoformat()
        )
        config.chassis.props.refreshToken.set(response["refresh_token"])
        config.chassis.props.refreshTokenExpiration.set(
            (
                datetime.datetime.now()
                + datetime.timedelta(seconds=response["refresh_expires_in"])
            ).isoformat()
        )
        config.chassis.props.sync()

    def apiCall(self, route, data={}, method="get", **kwargs):
        # Construct the headers
        headers = {
            "X-API-Key": self.apiKey,
            "Authorization": f"Bearer {config.chassis.props.token.get()}",
        }

        # Make the request
        response = getattr(self.apiSession, method.lower())(
            url=config.bungie + route, headers=headers, data=data, **kwargs
        )

        # Just return the json. Further functionality may
        # be needed in the future
        try:
            return response.json().get("Response", response)
        except json.decoder.JSONDecodeError:
            raise APIError(
                f"Expected JSON data from API. Received {response.status_code}"
            )

    def fetchImage(self, route):
        # Fetch the image
        fetchedImage = Image.open(
            requests.get(url=config.bungie + route, stream=True).raw
        )

        # Load it into memory and return
        fetchedImage.load()
        return fetchedImage

    def prepareImage(self, image):
        # Just convert to RGB and pass through the helper
        return PILHelper.to_native_format(self.device, image.convert("RGB"))

    def fetchManifestData(self):
        print("Fetching manifest data...")
        self.manifestData = self.apiCall(f"/Platform/Destiny2/Manifest/")
        version = self.manifestData["version"]

        # Make sure the cache dir exists
        cachePath = config.chassis.store.path / "cache"
        cachePath.mkdir(exist_ok=True)

        # Check the version
        if version != config.chassis.props.manifestVersion.get():
            print("Cached manifest data is out-of-date or missing")
            print("Reconstructing manifest cache...")

            # Fetch and decompress content file
            archivePath = cachePath / f"mwcp.{version}.zip"
            urllib.request.urlretrieve(
                config.bungie
                + self.manifestData["mobileWorldContentPaths"]["en"],
                archivePath,
            )
            with zipfile.ZipFile(archivePath) as archive:
                contentInfo = archive.infolist()[0]
                config.chassis.props.manifestContentName.set(
                    contentInfo.filename
                )
                archive.extract(contentInfo, path=cachePath)
            os.remove(archivePath)

            # Update stored manifest version
            config.chassis.props.manifestVersion.set(version)
            print("Done!")

        # Open a connection to the content database
        manifestContentPath = (
            cachePath / config.chassis.props.manifestContentName.get()
        )
        self.manifestContent = sqlite3.connect(
            f"file:{manifestContentPath}?mode=ro",
            uri=True,
            check_same_thread=False,
        )

        self.manifestGet("DestinyRaceDefinition", "2803282938")

    def manifestGet(self, table, hash):
        # Convert has to ID
        id = int(hash)
        if (id & (1 << (32 - 1))) != 0:
            id = id - (1 << 32)

        cursor = self.manifestContent.execute(
            f"SELECT json FROM {table} WHERE id={id}"
        )

        found = cursor.fetchone()[0]

        return json.loads(found)

    def fetchUserInfo(self):
        self.verifyAuth()

        # Request the bungie net user info
        bungieId = config.chassis.props.bungieId.get()
        player = self.apiCall(
            f"/Platform/User/GetMembershipsById/{bungieId}/0/"
        )

        # Store the destiny membership ID and membership type (we assume destiny membership number 0)
        membership = player["destinyMemberships"][0]
        self.membershipId = membership["membershipId"]
        self.membershipType = membership["membershipType"]

        # Request the player's destiny profile
        profile = self.apiCall(
            f"/Platform/Destiny2/{self.membershipType}/Profile/{self.membershipId}/?components=200"
        )

        # Iterate through characters and put them on the deck
        # for NOW just take the first one
        characters = profile["characters"]["data"]
        # for i, characterId in enumerate(characters):
        #     character = characters[characterId]
        #     self.device.set_key_image(
        #         self.key(i, 1),
        #         self.prepareImage(self.fetchImage(character["emblemPath"])),
        #     )
        #     self.characterId = characterId

        self.pushFrame(CharacterSelectionStage, {"characters": characters})

        config.chassis.props.sync()

    def openDeck(self):
        # Create a manager
        self.deviceManager = DeviceManager()
        decks = self.deviceManager.enumerate()

        # If there are no decks, throw an error
        if len(decks) < 1:
            raise RuntimeError("No Stream Decks detected :(")

        # Capture the first deck, open it, and reset it
        self.device = decks[0]
        self.device.open()
        self.device.reset()

        # Set callback for buttons
        self.device.set_key_callback(self.pressStack)

    def closeDeck(self):
        self.device.close()

    def key(self, x, y):
        return (y * 5) + x

    def coords(self, n):
        x = n % 5
        y = (n - x) // 5
        return (x, y)

    def startLoop(self):
        # try:
        #     while True:
        #         pass
        # except KeyboardInterrupt:
        #     return

        # apiPath = f"/Platform/Destiny2/{self.membershipType}/Profile/{self.membershipId}/Character/{self.characterId}/?components=205"
        # print("PATH", apiPath)
        # inventory = self.apiCall(apiPath)

        # pprint.pprint(inventory)

        # return

        # Wait until all application threads have terminated (for this example,
        # this is when all deck handles are closed)
        for t in threading.enumerate():
            if t is threading.currentThread():
                continue

            if t.is_alive():
                try:
                    t.join()
                except KeyboardInterrupt:
                    self.closeDeck()
                    print("Exiting...")

    def renderStack(self):
        # If the stack is empty, zero out all keys to black
        if len(self._stack) == 0:
            for x in range(5):
                for y in range(3):
                    self.device.set_key_image(
                        self.key(x, y), self.device.BLANK_KEY_IMAGE
                    )

        # Else, loop through the top-most stack and render its keys
        else:
            frame = self._stack[0]
            for x in range(5):
                for y in range(3):
                    self.device.set_key_image(self.key(x, y), frame.keys[x][y])

    def setupStack(self):
        self._stack = []
        self.renderStack()

    def pressStack(self, deck, key, state):
        if state is True:
            if len(self._stack):
                try:
                    self._stack[0].press(*self.coords(key))
                except Exception as e:
                    print(
                        "Unexpected error:\n",
                        "".join(traceback.format_exception(*sys.exc_info())),
                    )

    def pushFrame(self, frameClass, frameOptions):
        instance = frameClass(self, frameOptions)
        self._stack.insert(0, instance)
        self.renderStack()

    def popFrame(self):
        if len(self._stack):
            frame = self._stack.pop(0)
            frame.destroy()
            del frame
            self.renderStack()
