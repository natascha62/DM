# CS50 Final Project - Diabetes Mellitus Management System
#### Video Demo:  <URL HERE>

  
## Authors  

Tsai, Wan-Chen - natascha62@gmail.com
  
Lo, Ta-Hsuan - b95401010@ntu.edu.tw
  
  
## About the website

This is my final project for [Harvard CS50x] course. It's a website for doctors and patients to manage diabetes mellitus. 
  
Patients with diabetes mellitus should undergo regular checkup and try to keep these indicators in target range. However, the target ranges are different for each patient according to their age and underlying diseases, such as coronary artery disease, chronic kidney disease, and hypertension...etc. By registering to this website and entering personal information, patients can get their personalized treatment targets.
  
In addition, the duration between each checkup also differs according to previous test results. The website will automatically calculate the latest checkup date for each patient. Furthermore, the system will send an e-mail 7 days prior to the checkup date automatically to notify the patient.
  
Once the patient provides the test results, the website can show the chart of the trend in these data. 

For doctors, the "set patient" page is unlocked so they can access or record patients' data.
  
  
## Built with

- python 3
- flask
- javasript
- sqlite
- cs50
- werkzeug
- chart.js
  

## How the webpage works?

  
### Registration
  
The user can register either as a patient. During registration you need to enter these fields:

- ID
- Password
- Password confirmation: ensure the password entered are correct
  
After registerd successfully, user will be directed to info page and provide different personal information according to their age.
  
### Routing

Each route checks if the user is authenticated. 
For patients, they are free to key in their blood test results, blood pressure, urine protein screening, ophthamlmic examination and neurological examination results.
After entering these data, the website will automatically update their personalized control target and the next checkup date.
  
For doctors, they should log in the webpage with "doctor" as ID. Each route check if the user's identity. If and only if the user log in with "doctor", he or she can access patients' data.
  
### Database

Database stores all users, background information, blood test result, urine protein status, body weight, ophthalmic and neurological examination results.
  
### Personalized control target
  
Factors affecting control target: age, sex, past medical history, familial medical history, smoking status, renal function and past examination results
Based on these factors, personalized control targets will be determined for each patient.

The target and latest data will be shown on a large table. Suggested checkup date will also be calculated automatically.

![截圖 2021-11-18 上午10 31 45](https://user-images.githubusercontent.com/81509261/142341249-c2c54062-c085-4cc5-afe1-64a2a4451b2f.png)

  
### Records
  
Once the patients log in, they can update recent test results. These data will be stored in the database.
Doctors can update every patient's data after they key in patient's ID on the "set patient" page.
  
![截圖 2021-11-18 上午10 42 14](https://user-images.githubusercontent.com/81509261/142341931-07b2e9a0-1ee7-4a5e-994d-35204a6464dc.png)

  
### Trend
  
This page will request serial data from the database and presented the trend by a line chart.
Items that could be request for trend includes: HbA1c, body weight, blood creatinine and lipid profile.

![截圖 2021-11-18 上午10 35 37](https://user-images.githubusercontent.com/81509261/142342095-bd40d0f3-39a2-4442-855d-b729e8771e47.png)

  
### Automatic e-mail notification
  
This function is built with APScheduler. The task runs every day.
It will send notification e-mail to the patients 7 days prior to the suggested checkup date.
  
  

## How to use

The website is hosted by PythonAnywhere:
[natascha62.pythonanywhere.com](https://natascha62.pythonanywhere.com/)




## Possible improvements

- Have a way for users to change their personal information, such as e-mail and phone numbers.
- Have administrator account which confirms user identity so doctors could register their own accounts.
- Ability to upload multiple blood test results on different date at the same time.
- Direct connection with Taiwanese National Health Insurance database so the test results could be downloaded and uploaded automatically. (An API might help?)
  
  
## Acknowledgements

- [American Diabetes Association](https://www.diabetes.org/)
- [Taiwanese Association of Diabetes Educators](https://www.tade.org.tw/en/)
