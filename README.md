![estg_logo](https://github.com/user-attachments/assets/af8d26e1-51f4-4955-a108-1af2d3eccec7)
<div align="center">
  <img src="https://github.com/user-attachments/assets/e41c77ea-1902-44e4-a0d8-28ea313526d1">
</div>

---
## Badges
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![standard-readme compliant](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg?style=flat-square)](https://github.com/RichardLitt/standard-readme)

## Table of Contents
  - [Description](#description)
  - [System Requirements](#system-requirements)
  - [Instaling Hacktux](#instaling-hacktux)
  - [Using Hacktux](#using-hacktux)
  - [Contributing](#contributing)
  - [License](#license)

## Description
Hacktux was a project developed for the Computer Project curricular unit of the Computer Engineering course at the Polytechnic of Leiria. The aim of this application is to control and run virtual laboratories for industrial environments. Hacktux is made up of a python application that, using an interactive UI, allows the user to interact with and activate the available virtual laboratories. It also uses the VMware Workstation Pro hypervisor to run the virtual machines that simulate the virtual environment.

<div align="center">
  <img src="https://github.com/user-attachments/assets/066e40b5-78ce-41e7-b4c8-dc88e4a8e92d">
</div>

Hacktux creates virtual environments thanks to 3 virtual machines that are connected to each other on the same local network. One of the machines is Kali Linux, which is used by users to carry out attacks and forensics on the virtual environment. The other two machines are 32-bit versions of Windows 10, one of which contains Codesys software to simulate the operation of a PLC and the other runs Factory IO software to simulate an industrial factory in 3D. Thanks to these machines and software, the user can have a more emersive experience as they can see the exchange of data between the two systems and can see the objects in the factory in motion. Furthermore, because they are virtual machines that require few resources, they can be run on several computers that don't need to contain very specialized hardware

<div align="center">
  <img src="https://github.com/user-attachments/assets/9bbd0e8f-e547-4889-a06d-4e00145610ba">
</div>

## System Requirements
Before you start, check if you have the following requirements:

  ### Software Requirements
  - The operating system must be Windows, the project was carried out on Windows 11, Windows 10 should work as well, older versions are not recommended such as Windows 7 or Windows Vista
  - The version of Python used by this project was 3.12, other versions have not yet been validated feel free to test with others
  - You must have VMware Worksation Pro installed, version 17.5.2 or higher, because in this version it is possible to use this hypervisor for free for personal use cases.

  ### Hardware Requirements
  - To run the virtual machines in their lightest state, the PC must have a total of 5GB of RAM dedicated just to them, so it is recommended that the PC has 8GB of RAM or more


## Contributing
This project was developed by:
  - Manuel José Antunes Eusébio
  - Duarte Bento Batista

With the help of the teachers
  - Dr.Leonel Filipe Simões Santos
  - Dr.Rogério Luís de Carvalho Costa 

