## Table of Contents
1. [General Info](#general-info)
2. [Technologies](#technologies)
3. [Installation](#installation)
4. [Run Code](#run-code)
5. [Contributing / Security Policy](#contributing--security-policy)
6. [License](#license)

### General Info
***
NfcLocalization-Android is a project used to extract NFC-antenna-positions of smartphones from their manufacturers websites.
The positions which have been extracted are located in the "nfcChipsOutput"-folder.

## Technologies
***
The following tools are required:
* [python](https://www.python.org/): Version 3.9.14
* [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/): Version 4.11.1
* [easyocr](https://www.jaided.ai/easyocr/): Version 1.4.1
* [opencv 2](https://opencv.org/): Version 4.5.4.60
* [pandas](https://pandas.pydata.org/): Version 1.4.2
* [requests](https://requests.readthedocs.io/en/latest/): Version 2.27.1

## Installation
***
A list of installation steps you need to follow:
* download a python version 3.9.x for your system from https://www.python.org/ (python versions 3.10.x or higher are currently not supported)
* you may check the installation guide for your system from https://docs.python.org/3/using/
    * here is a guide for windows:
        * download and run the python installer
        * choose to add python to your path-variables or add it manually after the installation is finished
        * finish the installation process
* open a commandline tool and check if python is installed. Type: "python --version"
    * in case of failure you may need to install the python addon from the Windows store. Type: "python" to get to the right one easily.
* open a commandline tool to check if pip is installed. Type: "pip --version"
    * if it is not installed follow the guide to install it: https://pip.pypa.io/en/stable/installation/
* download and open the project
    * you may need plugins to run python code in your ide (for example in intellij you need to install the "python"-plugin from the market space)
* change the project sdk in your ide to your installed python version
* navigate to the folder of the "requirements.txt"-file of this project
* install all used packages. Type: "pip install -r requirements.txt"
* you may restart ide and open the project
* the installation is now complete.

## Run Code
***
A description of how to run the Code:
* open a commandline tool and navigate to the folder of the "runNfcLocalization"-file of this Project
* start the function. Type: "python runNfcLocalization.py"
    * if there is an opencv error try:
        * Type: "pip uninstall opencv-python-headless -y"
                "pip uninstall opencv-python -y"
                "pip install opencv-python --upgrade"

## Contributing / Security Policy

Since this software is not a productive version, please submit an issue or pull request for any bugs or vulnerabilities you find.

In case of a responsible disclosure, please follow instructions on https://www.gematik.de/datensicherheit#c1227.

## License

Copyright 2024 gematik GmbH

The NfcLocalization-Android is licensed under the European Union Public Licence (EUPL); every use of the NfcLocalization-Android Sourcecode must be in compliance with the EUPL.

You will find more details about the EUPL here: https://joinup.ec.europa.eu/collection/eupl

Unless required by applicable law or agreed to in writing, software distributed under the EUPL is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the EUPL for the specific language governing permissions and limitations under the License.
