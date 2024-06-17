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


import os
import cv2 as cv
import json
import requests
import pandas as pd


class BaselineFunctions:
    @staticmethod
    def load_all_images_of_folder(folder):
        images = []
        file_names = []
        for file_name in os.listdir(folder):
            img = cv.imread(os.path.join(folder, file_name))
            if img is not None:
                images.append(img)
                file_names.append(file_name)
        return images, file_names

    @staticmethod
    def delete_all_files_in_folder(folder):
        for file_name in os.listdir(folder):
            os.remove(os.path.join(folder, file_name))

    @staticmethod
    def download_image(path, phone_src, model_name, web_prefix=''):
        path_to_file = path + str(model_name) + ".webp"
        if not os.path.exists(path_to_file):
            try:
                phone_link = web_prefix + str(phone_src)
                print("Downloading: " + phone_link)
                phone_img = requests.get(phone_link, stream=True).content
                with open(path_to_file, "wb+") as f:
                    f.write(phone_img)
            except:
                print("Error: Download of " + str(model_name) + " did not succeed")
                pass
        else:
            print("Image already exists at : " + path_to_file)

    @staticmethod
    def check_if_data_base_entry_exists(path, db_file_name, model_name):
        path_to_file = path + str(db_file_name)
        try:
            with open(path_to_file, 'r') as f:
                data_entries = json.load(f)
            for data_entry in data_entries:
                if data_entry["marketingName"] == str(model_name):
                    return True
            return False
        except:
            print("Error: DataBaseFile " + str(db_file_name) + " could not be opened")
            pass

    @staticmethod
    def nfc_chip_coordinates_in_percent(x0_nfc, y0_nfc, x1_nfc, y1_nfc, x0_edge, y0_edge, x1_edge, y1_edge):
        # x0-phoneEdge is 0
        x0_nfc = x0_nfc - x0_edge
        x1_nfc = x1_nfc - x0_edge
        x1_edge = x1_edge - x0_edge
        # y0-phoneEdge is 0
        y0_nfc = y0_nfc - y0_edge
        y1_nfc = y1_nfc - y0_edge
        y1_edge = y1_edge - y0_edge
        # NFC Chip Coordinates in Percent of Phone Screen
        x0_nfc = BaselineFunctions.normalize(float(x0_nfc / x1_edge))
        y0_nfc = BaselineFunctions.normalize(float(y0_nfc / y1_edge))
        x1_nfc = BaselineFunctions.normalize(float(x1_nfc / x1_edge))
        y1_nfc = BaselineFunctions.normalize(float(y1_nfc / y1_edge))
        # mirror x-axis
        x0_nfc = 1 - x0_nfc
        x1_nfc = 1 - x1_nfc
        return x1_nfc, y0_nfc, x0_nfc, y1_nfc

    @staticmethod
    def normalize(x):
        if x < 0.0:
            return 0.0
        elif x > 1.0:
            return 1.0
        else:
            return x

    @staticmethod
    def format_coordinates(manufacturer, name, model_names, x0, y0, x1, y1):
        name = name.split(".")[0]
        nfc_chip_location = {
            "manufacturer": manufacturer,
            "marketingName": name,
            "modelNames": model_names,
            "nfcPos": {
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1
            }
        }
        return nfc_chip_location

    @staticmethod
    def write_to_json_file(nfc_chip_locations, path, filename):
        full_path = path + filename
        try:
            if os.path.exists(full_path):
                data = []
                with open(full_path, 'r') as f:
                    data_entries = json.load(f)
                for data_entry in data_entries:
                    data.append(data_entry)
                for nfc_chip_location in nfc_chip_locations:
                    if not nfc_chip_location["marketingName"] in data:
                        data.append(nfc_chip_location)
                with open(full_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=5)
            else:
                with open(full_path, 'w', encoding='utf-8') as f:
                    json.dump(nfc_chip_locations, f, ensure_ascii=False, indent=5)
        except:
            print("Error: Path " + str(full_path) + " could not be reached")
            pass

    @staticmethod
    def load_google_play_device_list():
        url = "https://storage.googleapis.com/play_public/supported_devices.csv"
        return pd.read_csv(url, encoding="utf-16")
