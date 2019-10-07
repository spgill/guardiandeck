# stdlib imports
import datetime
import os
import pathlib
import pprint
from PIL import Image, ImageDraw
import hashlib
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
from guardiandeck.frame import LoadingFrame
from guardiandeck.stages.CharacterSelection import CharacterSelectionStage

closingImage = Image.new(mode="RGB", size=(72, 72))
closingImageCanvas = ImageDraw.Draw(closingImage)
closingImageCanvas.text(
    (12, 26), "Closing...", fill=(255, 255, 255), font=config.font12
)


class APIError(Exception):
    pass


class GuardianDeck:
    def __init__(self):
        # Gotta make sure there's an API key configured
        self.apiKey = config.chassis.props.apiKey.get()
        if not self.apiKey:
            raise RuntimeError("No API key configured!")

        # Instance variables
        self.apiSession = requests.Session()
        self.hold1 = False
        self.iconCache = config.chassis.store.path / "cache" / "icons"

        self.iconCache.mkdir(exist_ok=True)

        # Open up a connection to the stream deck
        self.openDeck()

        # Setup the frame stack
        self.setupStack()

        # Ensure auth credentials are still good
        self.verifyAuth()

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
        if not config.chassis.props.token.get() or (
            refreshTokenExpiration <= now
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

    def fetchCachedImage(self, route):
        # Hash the image route to create a unique file path
        routeHash = hashlib.blake2b(
            route.encode("utf8"), digest_size=24
        ).hexdigest()
        hashedPath = self.iconCache / f"{routeHash}.png"

        # If the file already exists, load it
        if hashedPath.exists():
            return Image.open(hashedPath)

        # Else, fetch it and create it
        else:
            imageData = self.fetchImage(route)
            imageData.save(hashedPath)
            return imageData

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

    def manifestGetAll(self, table):
        for row in self.manifestContent.execute(f"SELECT json FROM {table}"):
            yield json.loads(row[0])

    def fetchUserInfo(self):
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

        # Remove the loading frame and then push the character selection frame
        self.popFrame()
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

    def cleanExit(self):
        # Insert the closing image
        self.device.set_key_image(
            self.key(2, 1), self.prepareImage(closingImage)
        )
        time.sleep(1)

        # Go through and destroy each frame in the stack
        for frame in self._stack:
            frame.setActive(False)
            frame.destroy()

        # Reset the deck and close the connection
        self.device.reset()
        self.closeDeck()

        print("Exiting...")
        exit()

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
                    pass

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
                    # self.device.set_key_image(self.key(x, y), frame.keys[x][y])
                    keyNo = self.key(x, y)
                    value = frame.keys[x][y]

                    # If the value is null, black out the key
                    if value is None:
                        self.device.set_key_image(
                            keyNo, self.device.BLANK_KEY_IMAGE
                        )

                    # If the value is a string, try and download from a url
                    if isinstance(value, str):
                        self.device.set_key_image(
                            keyNo,
                            self.prepareImage(self.fetchCachedImage(value)),
                        )

                    # Else try and directly transfer the value
                    else:
                        self.device.set_key_image(keyNo, value)

    def setupStack(self):
        self._stack = []
        # self.renderStack()
        self.pushFrame(LoadingFrame)

    def pressStack(self, deck, key, state):
        # Check for exit conditions
        if key == self.key(0, 2):
            self.hold1 = state
        elif key == self.key(0, 0) and self.hold1:
            self.cleanExit()

        if state is False:
            if len(self._stack):
                try:
                    self._stack[0].press(*self.coords(key))
                except Exception:
                    print(
                        "Unexpected error:\n",
                        "".join(traceback.format_exception(*sys.exc_info())),
                    )

    def pushFrame(self, frameClass, frameOptions={}):
        # Mark the current top frame as inactive
        if len(self._stack) > 0:
            self._stack[0].setActive(False)

        # Create instance of the new frame and push it to the stack
        instance = frameClass(self, True, frameOptions)
        self._stack.insert(0, instance)
        instance.setup()

        self.renderStack()

    def popFrame(self):
        if len(self._stack):
            # Pop out the top frame, deactivate it, and destroy it
            frame = self._stack.pop(0)
            frame.setActive(False)
            frame.destroy()
            del frame

            # If there's a frame left, set it as active
            if len(self._stack):
                self._stack[0].setActive(True)

            self.renderStack()
