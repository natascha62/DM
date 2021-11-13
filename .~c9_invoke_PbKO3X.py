import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///data.db")


@app.route("/")
def index():
    """Show index page"""
    return render_template("index.html")



@app.route("/target", methods=["GET", "POST"])
def target():
    ID = session["user_id"]
    # Calculate Age
    row = db.execute("SELECT * FROM users WHERE id = ?", ID)
    Birth = row[0]["birth"]
    Sex = row[0]["sex"]
    HTN = row[0]["HTN"]
    FH = row[0]["FH"]
    CKD = row[0]["CKD"]
    CAD = row[0]["CAD"]
    CHF = row[0]["CHF"]
    Smoking = row[0]["smoking"]
    Time = datetime.now()
    Age = Time.year - int(Birth[0:4])
    elderly_status = row[0]["elderly_status"]

    # Give edit options to enter new information/lab data
    if request.method == "POST":
        return redirect("/")


    # Show personalized target page
    else:
        # Check if elderly_status is calculated
        if Age >= 65 and elderly_status==0:
            return render_template("elderly.html")
            
        # Present peronalized target
        else:
            # Calculate glycemic target
            if Age < 65: 
                A1c_t = "< 7.0%" 
                AC_t = "80-130 mg/dL"
                PC_t = "< 180 mg/dL"
            elif Age >= 65 and elderly_status==1: 
                A1c_t = "< 7.0%-7.5%" 
                AC_t = "80-130 mg/dL"
                PC_t = "80-180 mg/dL"
            elif Age >=65 and elderly_status==2: 
                A1c_t = "< 8.0%" 
                AC_t = "90-150 mg/dL"
                PC_t = "100-180 mg/dL"
            elif Age >=65 and elderly_status==3:
                A1c_t = "Avoid reliance on A1C. Decisions should be based on avoiding hypoglycemia and symptomatic hyperglycemia."
                AC_t = "100-180 mg/dL"
                PC_t = "110-200 mg/dL"
            
            # Calculate LDL targe
            LDL = 100
            ASCVD_risk = 0
            for x in (HTN, FH, Smoking):
                if x == "T":
                    ASCVD_risk += 1
            if Sex == "M" and Age >= 45:
                ASCVD_risk += 1
            if Sex =="F" and Age >= 65:
                ASCVD_risk += 1
            # HDL <40mg/dL--> not completed yet!
            if ASCVD_risk >= 1:
                LDL = 70
            
            # Return HDL target
            if Sex == "F": HDL = 50
            elif Sex =="M": HDL = 40
            
            # BP target: if high ASCVD_risk or CKD--> BP <130/80
            if CAD == "T" or CHF=="T" or CKD == "T":
                BP = "130/80"
            elif elderly_status == 3:
                BP = "150/90"
            else:
                BP = "140/90"
            
            # BW target: keep BMI 18.5-23.9; if overweight, reduce 5-10% weight (0.5-1kg per week)
            BH = float(row[0]["BH"])
            lower_BW = int(18.5 * BH * BH /10000)
            upper_BW = int(23.9 * BH * BH /10000)
            weight = db.execute("SELECT * FROM BW WHERE id = ? ORDER BY date", ID)
            BW = float(weight[0]["BW"])
            if BW <= lower_BW:
                BW_t = lower_BW
            elif BW >= upper_BW:
                if BW*0.95 <= upper_BW:
                    BW_t = upper_BW
                elif BW*0.9 >= upper_BW:
                    BW_t = int(BW*0.9)
            else:
                BW_t = "keep current weight" 

        return render_template("target.html", A1c_t=A1c_t, AC_t=AC_t, PC_t=PC_t, LDL=LDL, HDL=HDL, BP=BP, lower_BW=lower_BW, upper_BW=upper_BW, BW_t=BW_t)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("ID"):
            flash("Must provide ID card number!")
            return redirect("/login")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Must provide password!")
            return redirect("/login")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE id = ?", request.form.get("ID"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("invalid username and/or password")
            return redirect("/login")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        flash("Logged in!")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")



@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()
    flash("Logged out")

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
def quote():
    """Get stock quote."""


@app.route("/sell", methods=["GET", "POST"])
def sell():
    """Sell shares of stock"""


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("ID"):
            flash("must provide ID number")
            return redirect("/register")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("must provide password")
            return redirect("/register")
        elif not request.form.get("confirmation"):
            flash("must confirm password")
            return redirect("/register")

        # Ensure username does not exist
        ID = request.form.get("ID")
        rows = db.execute("SELECT * FROM users WHERE id = ?", ID)
        if len(rows) == 1:
            flash("ID already exists")
            return redirect("/register")

        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if password != confirmation:
            flash("passwords do not match")
            return redirect("/register")

        # insert username and password into database
        HASH = generate_password_hash(password)
        db.execute("INSERT INTO users (id, hash) VALUES (?,?)", ID, HASH)

        # Automatic log in the user after registration
        user_id = db.execute("SELECT id FROM users WHERE id = ?", ID)[0]["id"]

        # Remember which user has logged in
        session["user_id"] = user_id
        flash("Registered!")

        # Redirect user to home page
        return render_template("info.html")

    else:
        return render_template("register.html")



@app.route("/info", methods=["GET", "POST"])
def info():
    """Get user information"""
    if request.method == "POST":

        # Ensure all info are submitted
        if not request.form.get("name") or not request.form.get("birth") or not request.form.get("sex") or not request.form.get("phone") or not request.form.get("smoking"):
            flash("Please provide all necessary personal information")
            return render_template("info.html")

        # Store info into database
        else:
            Name = request.form.get("name")
            Birth = request.form.get("birth")
            Sex = request.form.get("sex")
            Phone = request.form.get("phone")
            Smoking = request.form.get("smoking")
            HTN = request.form.get("HTN")
            CAD = request.form.get("CAD")
            FH = request.form.get("FH")
            BW = request.form.get("BW")
            BH = request.form.get("BH")
            ID = session["user_id"]
            Time = datetime.now()
            
            db.execute("UPDATE users SET name=?, birth=?, sex=?, phone=?, smoking=?, HTN=?, CAD=?, FH=?, BH=? WHERE id=?", Name, Birth, Sex, Phone, Smoking, HTN, CAD, FH, BH, ID)
            db.execute("INSERT INTO BW (BW, id) VALUES (?,?) ", BW, ID)

            flash("Personal information stored!")
            
            # Determine if elderly info required
            
            Age = Time.year - int(Birth[0:4])
            if Age >= 65:
                return render_template("elderly.html")

        # Redirect user to info page
        return redirect("/")

    else:
        return render_template("info.html")
        
        
        
@app.route("/elderly", methods=["GET", "POST"])
def elderly():
    """Get elderly information"""
    if request.method == "POST":

        # Get cancer status
        cancer = int(request.form.get("cancer"))
        # Get CHF status
        CHF = int(request.form.get("CHF"))
        # Get lung status
        lung = int(request.form.get("lung"))
        # Get CKD status
        CKD = int(request.form.get("CKD"))
        # Get function status
        function = int(request.form.get("function"))

        # Calculate comorbidity
        comorbidity = 0
        ID = session["user_id"]
        CAD = 0
        HTN = 0
        if db.execute("SELECT CAD FROM users WHERE id = ?", ID)[0]["CAD"]=="T":
            CAD = 1
        if db.execute("SELECT HTN FROM users WHERE id = ?", ID)[0]["HTN"]=="T":
            HTN = 1
        illness = ("falls", "depression", "arthritis", "incontinence", "stroke")
        for x in illness:
            if request.form.get(x) == "1":
                comorbidity += 1
        stage = (cancer,CHF,lung,CKD)
        for x in stage:
            if int(x) >= 1:
                comorbidity += 1
        comorbidity = comorbidity + CAD + HTN
        

        # Calculate ADL
        ADL_item = ("bathing","dressing","grooming","mouthcare","toileting","transfer","walking","climbstair","eating")
        bathing = request.form.get("bathing")
        ADL = 0
        for x in ADL_item:
            adl = request.form.get(x)
            if adl == "1":
                ADL +=1
                
        # Deal with elderly classification
        # Very complex elderly
        elderly_status = 0
        if function==1 or function==2 or CHF>=3 or lung==2 or CKD==6 or cancer==2 or ADL>=2:
            elderly_status = 3
        # Moderate elderly
        elif comorbidity>=3:
            elderly_status = 2
        else:
            elderly_status =1
        
        flash("comorbidity =")
        flash(comorbidity)
        flash(", elderly_status=")
        flash(elderly_status)
        
        # Store elderly status and CKD into database
        db.execute("UPDATE users SET elderly_status=?, CKD=?, CHF=? WHERE id=?", elderly_status, CKD, CHF,ID)
        

        # Redirect user to info page
        return redirect("/")

    else:
        return render_template("elderly.html")
        
        

@app.route("/record", methods=["GET", "POST"])
def record():
    """Update user lab and info"""
    ID = session["user_id"]
    Date = request.form.get("date")
    
    if request.method == "POST":
        
        Item = ("BW", "SBP", "DBP", "A1c", "AC", "PC", "TCHO", "LDL", "HDL", "TG", "Cre", "UP_M", "UACR", "MNSI", "OPH_normal", "NPDR", "PDR", "CSME")
        
        # Ensure there is data to be stored
        Nill = True
        Data = []
        for x in Item:
            if not request.form.get(x):
                continue
            else:
                Nill = False
                Data.append(x)

        # No data was entered
        if Nill == True:
            flash("please provide the data")
            return render_template("record.html")

        # The user gives some data            
        else:
            for x in Data:
                # Update BW
                if x=="BW":
                    BW = request.form.get("BW")
                    if not db.execute("SELECT * FROM BW WHERE id=? AND date=?", ID, Date):
                        db.execute("INSERT INTO BW (BW, id, Date) VALUES (?,?,?) ", BW, ID, Date)
                    else:
                        db.execute("UPDATE BW SET BW=? WHERE id=? AND date=?", BW, ID, Date)
                
                # Update records(A1c, lipid, Cre, UP_M, UACR, MNSI)
                if x in ("A1c", "LDL", "HDL", "TCHO", "TG", "Cre", "UP_M", "UACR", "MNSI"):
                    A1c = request.form.get("A1c")
                    TCHO = request.form.get("TCHO")
                    LDL = request.form.get("LDL")
                    HDL = request.form.get("HDL")
                    TG = request.form.get("TG")
                    Cre = request.form.get("Cre")
                    UP_M = request.form.get("UP_M")
                    UACR = request.form.get("UACR")
                    MNSI = request.form.get("MNSI")
                    if not db.execute("SELECT * FROM records WHERE id=? AND date=?", ID, Date):
                        db.execute("INSERT INTO records (BW, id, Date) VALUES (?,?,?) ", BW, ID, Date)
                    else:
                        db.execute("UPDATE BW SET BW=? WHERE id=? AND date=?", BW, ID, Date)

                
                
                
                
                # Update OPH
                
                
                # Update AC PC sugar
                
                # Update BP
                
                
                    



            


        # Redirect user to info page
            return redirect("/")

    else:
        return render_template("record.html")