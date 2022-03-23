import numpy as np
import cv2 as cv
import requests
import os
import basicfunctions as base
from bs4 import BeautifulSoup as bs

WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
BLUE = (255, 0, 0)
RED = (0, 0, 255)


def loadAllNewPhoneImages(url, path):
    if not os.path.isdir(path):
        os.makedirs(path)

    website = requests.get(url)
    results = bs(website.content, 'html.parser')
    phones = results.findAll('div', class_='phone-item')

    for phone in phones:
        modelName = str(phone.find('div', class_='sm-text').text).strip()
        if modelName.__contains__("*"):
            modelName = modelName.replace("*", "")
        phoneClass = phone.find('img', class_='product')
        phoneSrc = str(phoneClass["src"])
        base.downloadFileIfNeccessary(path, phoneSrc, modelName, "https:")


def findPhoneEdgeInImage(img, filename):
        #Preprocessing
        #convert image to grayscale
        imgGray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        #blur
        imgBlur = cv.GaussianBlur(imgGray, (3, 3), cv.BORDER_DEFAULT)
        #edge detection
        imgCanny = cv.Canny(imgBlur, 0, 5)

        #try to find clear edges
        for i in range(10, 51, 10):
            x0, y0, x1, y1 = findEdge(imgCanny, iterations=i)
            if x0 != -1:
                return x0, y0, x1, y1
        print("Error 404: Could not find Edge in " + filename)
        return -1, -1, -1, -1


def findEdge(imgCanny, iterations):
    #pixel
    dim = imgCanny.shape
    pixelImage = dim[0] * dim[1]
    #merge border
    imgDil = cv.dilate(imgCanny, (15, 15), iterations=iterations)
    imgEro = cv.erode(imgDil, (15, 15), iterations=iterations)
    #contour detection
    contours, hierarchies = cv.findContours(imgEro, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    if contours is not None:
        contours = sorted(contours, key=cv.contourArea, reverse=True)
        for contour in contours:
            peri = cv.arcLength(contour, True)
            approx = cv.approxPolyDP(contour, 0.02 * peri, True)
            x0, y0, w, h = cv.boundingRect(approx)
            pixelContour = w * h
            if (pixelContour/pixelImage) > 2/3: #assumption: mobile phone size is at least 66.6% of the image
                return x0, y0, (x0+w), (y0+h)
    return -1, -1, -1, -1


def findNfcChipViaColor(img, filename):
    #Preprocessing
    hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)
    #pixel
    dim = img.shape
    pixelImage = dim[0] * dim[1]

    for sat in range(50, 11, -1): #samsung has no fixed color values
        for hue in range(98, 102):
            lowerRange = np.array([80, sat, 20])
            upperRange = np.array([hue, 255, 255])
            mask = cv.inRange(hsv, lowerRange, upperRange)
            contours, hierarchy = cv.findContours(mask, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
            bigContoures = []
            for contour in contours:
                area = cv.contourArea(contour)
                if area > 500:
                    bigContoures.append(contour)
            if len(bigContoures) != 0:
                x0, y0, x1, y1 = checkContoures(bigContoures, pixelImage)
                if x0 != -1:
                    return x0, y0, x1, y1
    print("Error 404: No Nfc-chip found for " + filename)
    return -1, -1, -1, -1


def checkContoures(contours, pixelImage): #TODO minMatchContour returns immediatly -> check after for loops -> checks shape not position
    minMatchVal = 0.1
    for contour in contours:
        for contourToCheck in contours:
            matchingValue = cv.matchShapes(contourToCheck, contour, 1, 0.0)
            if (matchingValue < minMatchVal) & (matchingValue != 0.0):
                minMatchVal = matchingValue
                peri = cv.arcLength(contour, True)
                approx = cv.approxPolyDP(contour, 0.02 * peri, True)
                x0, y0, w, h = cv.boundingRect(approx)
                pixelContour = w*h
                if (pixelContour/pixelImage) < 0.5: #assumption: nfc chip size is not 50% of the image
                    return x0, y0, (x0+w), (y0+h)
    return -1, -1, -1, -1


def main():
    loadAllNewPhoneImages('https://www.samsung.com/hk_en/nfc-support/', 'samsung/phones/')
    images, filenames = base.loadAllImagesOfFolder('samsung/phones/')
    nfcChipLocations = []
    for img, filename in zip(images, filenames):
        x0Nfc, y0Nfc, x1Nfc, y1Nfc = findNfcChipViaColor(img, filename)
        x0Edge, y0Edge, x1Edge, y1Edge = findPhoneEdgeInImage(img, filename)
        if x0Edge != -1 & x0Nfc != -1:
            x0, y0, x1, y1 = base.nfcChipCoordinatesInPercent(x0Nfc, y0Nfc, x1Nfc, y1Nfc, x0Edge, y0Edge, x1Edge, y1Edge)
        else:
            print("Error 400: Missing or Wrong Parameter to find the right Coordinates for: " + filename)
            x0, y0, x1, y1 = -1, -1, -1, -1
        nfcChipLocations.append(base.formatCoordinates(filename, x0, y0, x1, y1))

        #debug
        imgContours = img.copy()
        cv.rectangle(imgContours, (x0Nfc, y0Nfc), (x1Nfc, y1Nfc), BLUE, 5)
        cv.rectangle(imgContours, (x0Edge, y0Edge), (x1Edge, y1Edge), GREEN, 5)
        cv.imshow('img', img)
        cv.imshow('imgC', imgContours)
        if cv.waitKey(0) & 0xFF == ord('w'): #press w to reload
            continue
        if cv.waitKey(0) & 0xFF == ord('q'): #press q to quit
            break
        #end debug
    base.writeJsonFile(nfcChipLocations, 'nfcChipsOutput/', 'nfcChipsSamsung.json')


#run application
main()








