import os
import cv2 as cv
import json
import requests


def loadAllImagesOfFolder(folder):
    images = []
    filenames = []
    for filename in os.listdir(folder):
        img = cv.imread(os.path.join(folder, filename))
        if img is not None:
            images.append(img)
            filenames.append(filename)
    return images, filenames


def downloadFileIfNeccessary(path, phoneSrc, modelName, webPrefix):
    pathToFile = path + str(modelName) + ".webp"
    if not os.path.exists(pathToFile):
        try:
            phoneLink = webPrefix + str(phoneSrc)
            print("Downloading: " + phoneLink)
            phoneImg = requests.get(phoneLink, stream=True).content
            with open(pathToFile, "wb+") as f:
                f.write(phoneImg)
        except:
            print("Error: Download of " + str(modelName) + " did not succeed")
            pass


def nfcChipCoordinatesInPercent(x0Nfc, y0Nfc, x1Nfc, y1Nfc, x0Edge, y0Edge, x1Edge, y1Edge):
    #x0-phoneEdge is 0
    x0Nfc = x0Nfc - x0Edge
    x1Nfc = x1Nfc - x0Edge
    x1Edge = x1Edge - x0Edge

    #y0-phoneEdge is 0
    y0Nfc = y0Nfc - y0Edge
    y1Nfc = y1Nfc - y0Edge
    y1Edge = y1Edge - y0Edge

    #NFC Chip Coordinates in Percent of Phone Screen
    x0Nfc = normalize(float(x0Nfc / x1Edge))
    y0Nfc = normalize(float(y0Nfc / y1Edge))
    x1Nfc = normalize(float(x1Nfc / x1Edge))
    y1Nfc = normalize(float(y1Nfc / y1Edge))

    #mirror x-axis
    x0Nfc = 1 - x0Nfc
    x1Nfc = 1 - x1Nfc
    return x1Nfc, y0Nfc, x0Nfc, y1Nfc


def normalize(x):
    if x < 0.0:
        return 0.0
    elif x > 1.0:
        return 1.0
    else:
        return x


def formatCoordinates(name, x0, y0, x1, y1):
    name = name.split(".")[0]
    nfcChipLocation = {
        "name": name,
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1
    }
    return nfcChipLocation


def writeJsonFile(nfcChipLocations, path, filename):
    path = path + filename
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(nfcChipLocations, f, ensure_ascii=False, indent=5)
