# TravelFit

Mobile App for Android and IOS FastAPI and ReactNative

## Description

Mobile App users can search local gym's and purchase guest passes while travelings

## Getting Started

### Dependencies

* Windows OS
* Refer to Requirments.txt

### Installing

* Setup a python virtual environment, and activate.
* Install python packages: 
```
python3 -m pip install -r requirements.txt
```
* Any modifications needed to be made to files/folders

* Install Node.js:
https://nodejs.org/en/download

### Emulation Install
* FOR MAC USERS ONLY:
Ios Simulator Expo Install/Setup: https://docs.expo.dev/workflow/ios-simulator/

* Any Operating System:
Android Emulator Install/Setup: https://docs.expo.dev/workflow/android-studio-emulator/


### Running on Your own Device:
* Using Expo Go (Ios/Android) Install/Setup: https://docs.expo.dev/workflow/android-studio-emulator/

### Executing program

* How to run backend
```
cd FastAPI
```
```
uvicorn main:app --reload
```
* ctrl-c to stop server


* How to run frontend
```
cd React
cd TravelFit
npm install
npm run start
```

now you want to switch to expo go mode.
```
s //this will (s)witch to expo go mode from development mode 
```
assuming you have your preffered device installed. 
then from here you can choose to run on either android Emulator or Ios Simulator or your own device:

* Ios Simulator:
```
i //will run Ios simulator (MAC ONLY)
```
* Android Emulator:
```
a //will run Android Emulator
```
* Expo Go Device:
- Open Expo Go
- Ensure you are on the same wifi as your server
- (Ios) hit `i` on your node server
- (Android) scan qr code from the server

* ctrl-c to stop server

## Help

Any advise for common problems or issues.
```
command to run if program contains helper info
```

## Authors

Contributors
* David Fazio
* Bryan Garcia
* Bryan Rivas
* Timothy Vu
* Brandon Mejia


## License