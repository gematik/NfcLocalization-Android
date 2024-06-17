"""
/*
 * Copyright (c) 2024 gematik GmbH
 *
 * Licensed under the EUPL, Version 1.2 or – as soon they will be approved by
 * the European Commission - subsequent versions of the EUPL (the Licence);
 * You may not use this work except in compliance with the Licence.
 * You may obtain a copy of the Licence at:
 *
 *     https://joinup.ec.europa.eu/software/page/eupl
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the Licence is distributed on an "AS IS" basis,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the Licence for the specific language governing permissions and
 * limitations under the Licence.
 *
 */
"""


import numpy as np
import cv2 as cv
import requests
import os
from baselineFunctions import BaselineFunctions as base
from bs4 import BeautifulSoup as bs


class FindNfcChipForSamsung:
    @staticmethod
    def _load_all_new_phone_images(url, image_path, db_path, db_file_name):
        if not os.path.isdir(image_path):
            os.makedirs(image_path)

        website = requests.get(url)
        results = bs(website.content, 'html.parser')
        phones = results.findAll('div', class_='phone-item')

        for phone in phones:
            model_name = str(phone.find('div', class_='sm-text').text).strip()
            if "*" in model_name:
                model_name = model_name.replace("*", "")
            phone_class = phone.find('img', class_='product')
            phone_src = str(phone_class["src"])
            if not base.check_if_data_base_entry_exists(db_path, db_file_name, model_name):
                base.download_image(image_path, phone_src, model_name, "https:")
            else:
                print("Existing database entry found for: " + model_name)

    @staticmethod
    def _find_phone_edge_in_image(img, filename):
        # Preprocessing
        # convert image to grayscale
        img_gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        # blur
        img_blur = cv.GaussianBlur(img_gray, (3, 3), cv.BORDER_DEFAULT)
        # edge detection
        img_canny = cv.Canny(img_blur, 0, 5)
        # try to find clear edges
        for i in range(10, 51, 10):
            x0, y0, x1, y1 = FindNfcChipForSamsung._find_edge(img_canny, iterations=i)
            if x0 != -1:
                return x0, y0, x1, y1
        print("Could not find edge in " + filename)
        return -1, -1, -1, -1

    @staticmethod
    def _find_edge(img_canny, iterations):
        # pixel
        dim = img_canny.shape
        pixel_image = dim[0] * dim[1]
        # merge border
        img_dil = cv.dilate(img_canny, (15, 15), iterations=iterations)
        img_ero = cv.erode(img_dil, (15, 15), iterations=iterations)
        # contour detection
        contours, hierarchies = cv.findContours(img_ero, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        if contours is not None:
            contours = sorted(contours, key=cv.contourArea, reverse=True)
            for contour in contours:
                peri = cv.arcLength(contour, True)
                approx = cv.approxPolyDP(contour, 0.02 * peri, True)
                x0, y0, w, h = cv.boundingRect(approx)
                pixel_contour = w * h
                # assumption: mobile phone size is at least 66.6% of the image
                if (pixel_contour / pixel_image) > 2 / 3:
                    return x0, y0, (x0 + w), (y0 + h)
        return -1, -1, -1, -1

    @staticmethod
    def _find_nfc_chip_via_color(img, filename):
        # Preprocessing
        hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)
        # pixel
        dim = img.shape
        pixel_image = dim[0] * dim[1]
        for sat in range(50, 11, -1):  # samsung has no fixed color values
            for hue in range(98, 102):
                lower_range = np.array([80, sat, 20])
                upper_range = np.array([hue, 255, 255])
                mask = cv.inRange(hsv, lower_range, upper_range)
                contours, hierarchy = cv.findContours(mask, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
                big_contours = []
                for contour in contours:
                    area = cv.contourArea(contour)
                    if area > 500:
                        big_contours.append(contour)
                if len(big_contours) != 0:
                    x0, y0, x1, y1 = FindNfcChipForSamsung._check_contours(big_contours, pixel_image)
                    if x0 != -1:
                        return x0, y0, x1, y1
        print("No nfc-chip found for " + filename)
        return -1, -1, -1, -1

    @staticmethod
    def _check_contours(contours, pixel_image):
        min_match_val = 0.1
        for contour in contours:
            for contour_to_check in contours:
                matching_value = cv.matchShapes(contour_to_check, contour, 1, 0.0)
                if (matching_value < min_match_val) & (matching_value != 0.0):
                    min_match_val = matching_value
                    peri = cv.arcLength(contour, True)
                    approx = cv.approxPolyDP(contour, 0.02 * peri, True)
                    x0, y0, w, h = cv.boundingRect(approx)
                    pixel_contour = w * h
                    if (pixel_contour / pixel_image) < 0.5:  # assumption: nfc chip size is not 50% of the image
                        return x0, y0, (x0 + w), (y0 + h)
        return -1, -1, -1, -1

    @staticmethod
    def _get_model_names_of_device_list(google_device_list, file_name):
        full_name = file_name.split(".")[0]
        brand_name, marketing_name = full_name.split(" ", 1)
        return google_device_list.loc[
            (google_device_list['Retail Branding'] == brand_name) &
            (google_device_list['Marketing Name'] == marketing_name)]['Model'].values.tolist()

    @staticmethod
    def main():
        FindNfcChipForSamsung._load_all_new_phone_images('https://www.samsung.com/hk_en/nfc-support/',
                                                         'samsung/phones/', 'nfcChipsOutput/', 'nfc_positions.json')
        images, file_names = base.load_all_images_of_folder('samsung/phones/')
        google_device_list = base.load_google_play_device_list()
        nfc_chip_locations = []
        for img, file_name in zip(images, file_names):
            x0_nfc, y0_nfc, x1_nfc, y1_nfc = FindNfcChipForSamsung._find_nfc_chip_via_color(img, file_name)
            x0_edge, y0_edge, x1_edge, y1_edge = FindNfcChipForSamsung._find_phone_edge_in_image(img, file_name)
            if x0_edge != -1 & x0_nfc != -1:
                x0, y0, x1, y1 = base.nfc_chip_coordinates_in_percent(x0_nfc, y0_nfc, x1_nfc, y1_nfc, x0_edge, y0_edge,
                                                                      x1_edge, y1_edge)
                nfc_chip_locations.append(
                    base.format_coordinates("Samsung", file_name, FindNfcChipForSamsung._get_model_names_of_device_list(
                                            google_device_list, file_name), x0, y0, x1, y1))
            else:
                print("Missing or wrong parameter to find the right coordinates for: " + file_name)

        base.write_to_json_file(nfc_chip_locations, 'nfcChipsOutput/', 'nfc_positions.json')
        base.delete_all_files_in_folder('samsung/phones/')
