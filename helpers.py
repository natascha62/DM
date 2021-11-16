import os
import requests
import urllib.parse
from cs50 import SQL

from flask import redirect, render_template, request, session
from functools import wraps


def update_CKD(Sex, Age):
    ID = session["user_id"]
    db = SQL(os.getenv("postgres://ddbkgaxnissqhx:25074932dc176fee4fc964ef20d681f522b3bac67b747fdbc5839bd5a27f39ff@ec2-34-203-182-172.compute-1.amazonaws.com:5432/d272qc35s71bfm"))
    
    # Request proteinuria in records for each date, 0=no, 1=stick negative only, 2=stick <=2+, 3=stick >=3+, 4=UACR+, 5=UPCR+
    Data = db.execute("SELECT proteinuria FROM records WHERE id=? AND NOT proteinuria=-1 ORDER BY date DESC", ID)
    
    if len(Data) > 0:
        for i in range(len(Data)):
            proteinuria = Data[i]["proteinuria"]
            if Data in [0, 3, 4, 5]:
                db.execute("UPDATE users SET proteinuria=? WHERE id=?", proteinuria, ID)
                break
    
    
    # Calculate eGFR
    Cre_row = db.execute("SELECT * FROM records WHERE id=? AND NOT Cre=? ORDER BY date DESC", ID, "")
    Patient = db.execute("SELECT * FROM users WHERE id=?", ID)
    
    # No Cre data, keep current CKD stage, Do nothing
    if len(Cre_row) == 0:
        if Patient[0]["proteinuria"] >= 3:
            db.execute("UPDATE users SET CKD=1 WHERE id=?", ID)
        return
    else:
        Cre_l = Cre_row[0]["Cre"]
        # Calculate eGFR
        if Sex =="F":
            eGFR = 175 * Cre_l**(-1.154) * Age**(-0.203) * 0.742
        elif Sex == "M":
            eGFR = 175 * Cre_l**(-1.154) * Age**(-0.203)
    
        # Determine CKD stage
        # Update CKD status if not under RRT
        if Patient[0]["CKD"] != 6:
            if eGFR < 15:
                CKD = 5
            elif 15 <= eGFR < 30:
                CKD = 4
            elif 30 <= eGFR < 60:
                CKD = 3
            elif 60 <= eGFR < 90 and Patient[0]["proteinuria"] >= 3:
                CKD = 2
            elif Patient[0]["proteinuria"] >= 3:
                CKD = 1
            else:
                CKD = 0
            db.execute("UPDATE users SET CKD=? WHERE id=?", CKD, ID)
    
    return
