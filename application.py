import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import json
from helpers import update_CKD

from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Mail, Message

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




#-----------------------------------
# Email part

# Configure mail server parameters
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'IDtoIT.CS@gmail.com'
app.config['MAIL_PASSWORD'] = 'harvardcs50'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

# Create an instance of the Mail class
mail = Mail(app)

# set configuration values
class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config())

# initialize scheduler
scheduler = APScheduler(BackgroundScheduler(timezone='Asia/Taipei'))
# if you don't wanna use a config, you can set options here:
scheduler.api_enabled = True
#scheduler.init_app(app)


db.app = app
db.init_app(app)

if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
    @scheduler.task('cron', id='notify', hour=23, minute=56, second=0)
    def notify():
        with db.app.app_context():
        	targets = db.execute("SELECT * FROM users WHERE JULIANDAY(date('now'))=(JULIANDAY(date_f)+7)")
        	if len(targets) == 0:
        		return
        	else:
        		for target in targets:
        		    if target["email"] != "NULL":
            			msg = Message('Diabetes Management System Automatic notification! ', sender = 'IDtoIT.CS@gmail.com', recipients = [target["email"]])
            			msg.body = "Hello {0} – It's time for your regualr diabetes mellitus check-up. Please schedule an appointment before {1}. See you then!".format(target["name"], target["date_f"])
            			mail.send(msg)
    scheduler.start()

#--------Email Part end---------#





Patient = "-1"


@app.route("/")
def index():
    """Show index page"""
    global Patient
    return render_template("index.html", Patient=Patient)


@app.route("/patient", methods=["GET", "POST"])
def patient():
    global Patient
    if request.method == "POST":
        # Check if patient exist
        patient = request.form.get("patient")
        if len(db.execute("SELECT * FROM users WHERE id=?", patient)) == 0 and patient != "-1":
            flash("This patient does not exist!")
        else:
            #Patient do exist
            GlobalList = globals()
            GlobalList['Patient'] = request.form.get("patient")
        
        return render_template("patient.html", Patient=Patient)
    
    else:
        return render_template("patient.html", Patient=Patient)



@app.route("/target", methods=["GET", "POST"])
def target():
    ID = session["user_id"]
    if ID == "doctor":
        global Patient
        ID = Patient
        
    row = db.execute("SELECT * FROM users WHERE id = ?", ID)

    # Give edit options to enter new information/lab data
    if request.method == "POST":
        return redirect("/")

    # If user did not provide info
    elif row[0]["name"] == None:
        flash("Please provide personal information to calculate personalized control target!")
        return render_template("info.html")

    else:
        # Calculate Age
        Sex = row[0]["sex"]
        Birth = row[0]["birth"]
        HTN = row[0]["HTN"]
        FH = row[0]["FH"]
        CKD = row[0]["CKD"]
        CAD = row[0]["CAD"]
        CHF = row[0]["CHF"]
        Stroke = row[0]["stroke"]
        Smoking = row[0]["smoking"]
        Time = datetime.now()
        Age = Time.year - int(Birth[0:4])
        elderly_status = row[0]["elderly_status"]

        # Check if elderly_status is calculated
        if Age >= 65 and elderly_status==0:
            ckd = int(db.execute("SELECT * FROM users WHERE id=?", ID)[0]["CKD"])
            return render_template("elderly.html", ckd=ckd, Patient=Patient)

        # Present peronalized target
        else:
            update_CKD(Sex, Age)
            # Glycemic control
            # Calculate glycemic target
            if Age < 65:
                A1c_t = 7.0
                AC_t = "80-130 mg/dL"
                PC_t = "< 180 mg/dL"
            elif Age >= 65 and elderly_status==1:
                A1c_t = 7.5
                AC_t = "80-130 mg/dL"
                PC_t = "80-180 mg/dL"
            elif Age >=65 and elderly_status==2:
                A1c_t = 8.0
                AC_t = "90-150 mg/dL"
                PC_t = "100-180 mg/dL"
            elif Age >=65 and elderly_status==3:
                A1c_t = -1
                AC_t = "100-180 mg/dL"
                PC_t = "110-200 mg/dL"

            # Calculate LDL targe
            LDL_t = 100
            ASCVD_risk = 0
            for x in (HTN, FH, Smoking):
                if x == "T":
                    ASCVD_risk += 1
            if Sex == "M" and Age >= 45:
                ASCVD_risk += 1
            if Sex =="F" and Age >= 65:
                ASCVD_risk += 1
            # HDL <40mg/dL
            HDL_row = db.execute("SELECT * FROM records WHERE id=? AND NOT HDL=? ORDER BY date DESC", ID, "")
            if len(HDL_row) > 0:
                if HDL_row[0]["HDL"] < 40:
                    ASCVD_risk += 1
            if ASCVD_risk >= 1 or Stroke == "T":
                LDL_t = 70

            # Return HDL/Cre target
            if Sex == "F": 
                HDL_t = 50
                Cre_t = 1.3
            elif Sex =="M": 
                HDL_t = 40
                Cre_t = 1.5

            # BP target: if high ASCVD_risk or CKD(include CKD stage 1)--> BP <130/80.
            # Pending proteinuria!!!!
            if CAD == "T" or Stroke == "T" or CHF > 0 or CKD > 0:
                BP = "130/80"
            elif elderly_status == 3:
                BP = "150/90"
            else:
                BP = "140/90"

            # BW target: keep BMI 18.5-23.9; if overweight,
            # Initial BW goal = reduce 5-10% weight (0.5-1kg per week)=initial goal
            # cBW = current latest BW   # iBW = initial BW
            BH = float(row[0]["BH"])
            lower_BW = int(18.5 * BH * BH /10000)
            upper_BW = int(23.9 * BH * BH /10000)
            iBW = float (db.execute("SELECT * FROM BW WHERE id = ? ORDER BY date ASC", ID)[0]["BW"])
            cBW = float(db.execute("SELECT * FROM BW WHERE id = ? ORDER BY date DESC", ID)[0]["BW"])
            found = False

            while found == False:
                found = True
                if cBW <= lower_BW:
                    BW_t = lower_BW
                elif cBW >= upper_BW:
                    if iBW * 0.9 <= upper_BW:
                        BW_t = upper_BW
                    elif iBW * 0.9 > upper_BW:
                        if cBW >= iBW * 0.9:
                            BW_t = int(iBW*0.9)
                        else:
                            iBW = cBW
                            found = False
                else:
                    BW_t = -1

            #---------------Latest data/Follow-up date--------------#

            # Recruit latest BW
            BW_l = db.execute("SELECT * FROM BW WHERE id=? ORDER BY date DESC", ID)[0]["BW"]
            BW_d = db.execute("SELECT * FROM BW WHERE id=? ORDER BY date DESC", ID)[0]["date"]

            # Recruit lates BP
            BP_row = db.execute("SELECT * FROM BP WHERE id=? ORDER BY date DESC", ID)
            if len(BP_row) == 0:
                SBP_l = "No data"
                DBP_l = ""
                BP_d = ""
            else:
                SBP_l = BP_row[0]["SBP"]
                DBP_l = BP_row[0]["DBP"]
                BP_d = BP_row[0]["date"]

            # Recruit neuro screening
            MNSI_row = db.execute("SELECT * FROM records WHERE id=? AND NOT MNSI=? ORDER BY date DESC", ID, "")
            if len(MNSI_row) == 0:
                MNSI_l = "No data"
                MNSI_d = ""
                MNSI_f = datetime.now().date()
            else:
                MNSI_l = MNSI_row[0]["MNSI"]
                MNSI_d = MNSI_row[0]["date"]
                MNSI_f = datetime.strptime(MNSI_d, '%Y-%m-%d').date() + timedelta(days=336)

            # Recruit OPH exam
            OPH_row = db.execute("SELECT * FROM OPH WHERE id=? ORDER BY date DESC", ID)
            PDR = "Proliferative diabetic retinopathy"
            NPDR = "Non-proliferative diabetic retinopathy"
            CSME = "Clinical significant macular edema"
            if len(OPH_row) == 0:
                OPH_l = "No data"
                OPH_d = ""
                OPH_f = datetime.now().date()
            else:
                OPH_d = OPH_row[0]["date"]
                if OPH_row[0]["OPH_normal"] == 1:
                    OPH_l = "Normal"
                    OPH_f = datetime.strptime(OPH_d, '%Y-%m-%d').date() + timedelta(days=336)
                else:
                    OPH_l = ""
                if OPH_row[0]["CSME"] == 1:
                    OPH_l = "C"
                    OPH_f = datetime.strptime(OPH_d, '%Y-%m-%d').date() + timedelta(days=84) # F/U in 2-4M
                if OPH_row[0]["PDR"] == 1:
                    OPH_l = OPH_l + "P"
                    OPH_f = datetime.strptime(OPH_d, '%Y-%m-%d').date() + timedelta(days=84) # F/U in 2-4M
                elif OPH_row[0]["NPDR"] == 1:
                    OPH_l = OPH_l + "NP"
                    OPH_f = datetime.strptime(OPH_d, '%Y-%m-%d').date() + timedelta(days=168) # F/U in 6-12M

            # Recruit latest A1c
            A1c_row = db.execute("SELECT * FROM records WHERE id=? AND NOT A1c=? ORDER BY date DESC", ID, "")
            if len(A1c_row) == 0:
                A1c_l = "No data"
                A1c_d = ""
                A1c_f = datetime.now().date()
            else:
                A1c_l = A1c_row[0]["A1c"]
                A1c_d = A1c_row[0]["date"]
                A1c_f = datetime.strptime(A1c_d, '%Y-%m-%d').date() + timedelta(days=84)

            # Recruit LDL profile
            LDL_row = db.execute("SELECT * FROM records WHERE id=? AND NOT LDL=? ORDER BY date DESC", ID, "")
            if len(LDL_row) == 0:
                LDL_l = "No data"
                LDL_d = ""
            else:
                LDL_l = LDL_row[0]["LDL"]
                LDL_d = LDL_row[0]["date"]

            # Recruit HDL profile
            HDL_row = db.execute("SELECT * FROM records WHERE id=? AND NOT HDL=? ORDER BY date DESC", ID, "")
            if len(HDL_row) == 0:
                HDL_l = "No data"
                HDL_d = ""
            else:
                HDL_l = HDL_row[0]["HDL"]
                HDL_d = HDL_row[0]["date"]

            # Recruit latest sugar data
            AC_row = db.execute("SELECT * FROM sugar WHERE AC=1 AND id=? ORDER BY date DESC", ID)
            PC_row = db.execute("SELECT * FROM sugar WHERE PC=1 AND id=? ORDER BY date DESC", ID)
            # Get AC data
            if len(AC_row) == 0:
                AC_l = "No data"
                AC_d = ""
            else:
                AC_l = AC_row[0]["sugar"]
                AC_d = AC_row[0]["date"]
            # Get PC data
            if len(PC_row) == 0:
                PC_l = "No data"
                PC_d = ""
            else:
                PC_l = PC_row[0]["sugar"]
                PC_d = PC_row[0]["date"]

            # Recruit proteinuria
            UPM_row = db.execute("SELECT * FROM records WHERE id=? AND NOT UP_M=? ORDER BY date DESC", ID, "NULL")
            UACR_row = db.execute("SELECT * FROM records WHERE id=? AND NOT UACR=? ORDER BY date DESC", ID, "")
            UPCR_row = db.execute("SELECT * FROM records WHERE id=? AND NOT UPCR=? ORDER BY date DESC", ID, "")
            
            # Return urine dipstick data
            if len(UPM_row) == 0:
                UPM_l = "No data"
                UPM_d = ""
                UPM = False
            else:
                UPM_l = int(UPM_row[0]["UP_M"])
                UPM_d = UPM_row[0]["date"]
                UPM = True
            
            # Check UPCR and UACR
            if len(UPCR_row) == 0:
                UPCR_l = "No data"
                UPCR_d = ""
                UPCR = False
            else:
                UPCR_l = int(UPCR_row[0]["UPCR"])
                UPCR_d = UPCR_row[0]["date"]   
                UPCR = True
                
            if len(UACR_row) == 0:
                UACR_l = "No data"
                UACR_d = ""
                UACR = False
            else:
                UACR_l = UACR_row[0]["UACR"]
                UACR_d = UACR_row[0]["date"]
                UACR = True

            # Deterimne F/U date
            if UACR == False and UPCR == False:
                UP_f = datetime.now().date()
            elif UPCR == False:
                if UACR_l >= 30:
                    UP_f = datetime.strptime(UACR_d, '%Y-%m-%d').date() + timedelta(days=168)
                else:
                    UP_f = datetime.strptime(UACR_d, '%Y-%m-%d').date() + timedelta(days=336)
            else:
                if UACR_l >= 30 or UPCR_l >= 200:
                    date = min(UPCR_d, UACR_d)
                    UP_f = datetime.strptime(date, '%Y-%m-%d').date() + timedelta(days=168)
                else:
                    UP_f = datetime.strptime(UACR_d, '%Y-%m-%d').date() + timedelta(days=336)
            

            # Recruit Cre profile
            Cre_row = db.execute("SELECT * FROM records WHERE id=? AND NOT Cre=? ORDER BY date DESC", ID, "")
            if len(Cre_row) == 0:
                Cre_l = "No data"
                Cre_d = ""
                Cre_f = datetime.now().date()
            else:
                Cre_l = Cre_row[0]["Cre"]
                Cre_d = Cre_row[0]["date"]
                # Determine F/U date
                # Calculate eGFR
                if Sex =="F":
                    eGFR = 175 * Cre_l**(-1.154) * Age**(-0.203) * 0.742
                elif Sex == "M":
                    eGFR = 175 * Cre_l**(-1.154) * Age**(-0.203)
                else:
                    eGFR = -1
                #Determine F/U date
                if eGFR > 60:
                    Cre_f = datetime.strptime(Cre_d, '%Y-%m-%d').date() + timedelta(days=336)
                elif 45 <= eGFR <= 60:
                    Cre_f = datetime.strptime(Cre_d, '%Y-%m-%d').date() + timedelta(days=168)
                elif 30 <= eGFR < 45:
                    Cre_f = datetime.strptime(Cre_d, '%Y-%m-%d').date() + timedelta(days=84)
                elif 15 <= eGFR < 30:
                    Cre_f = datetime.strptime(Cre_d, '%Y-%m-%d').date() + timedelta(days=84)
                elif eGFR < 15:
                    Cre_f = datetime.strptime(Cre_d, '%Y-%m-%d').date() + timedelta(days=28) # 4-6W
                else:
                    Cre_f = datetime.now().date()

            #------------F/U date neareset-------#
            # Find the latest F/U date (date_f in user)
            date_f = min (A1c_f, UP_f, MNSI_f, OPH_f, Cre_f)
            db.execute("UPDATE users SET date_f=? WHERE id=?", date_f, ID)
            today = datetime.now().date()
            
            #-----------Save target into database for trend------#
            if len(db.execute("SELECT * FROM target WHERE id=?", ID)) == 0:
                db.execute("INSERT INTO target (A1c, LDL, HDL, Cre, BW, date_f, id) VALUES (?,?,?,?,?,?,?)", A1c_t, LDL_t, HDL_t, Cre_t, BW_t, date_f, ID)
            else:
                db.execute("UPDATE target SET A1c=?, LDL=?, HDL=?, Cre=?, BW=?, date_f=?", A1c_t, LDL_t, HDL_t, Cre_t, BW_t, date_f)


        return render_template("target.html", Patient=Patient, 
        A1c_t=A1c_t, AC_t=AC_t, PC_t=PC_t, LDL_t=LDL_t, HDL_t=HDL_t, BP=BP, lower_BW=lower_BW, upper_BW=upper_BW, BW_t=BW_t,
        BW_l=BW_l, BW_d=BW_d, SBP_l=SBP_l, DBP_l=DBP_l, BP_d=BP_d, MNSI_l=MNSI_l, MNSI_d=MNSI_d, OPH_l=OPH_l, OPH_d=OPH_d, A1c_l=A1c_l, A1c_d=A1c_d, HDL_l=HDL_l, LDL_l=LDL_l, HDL_d=HDL_d, LDL_d=LDL_d,
        Cre_l=Cre_l, Cre_d=Cre_d, AC_l=AC_l, AC_d=AC_d, PC_l=PC_l, PC_d=PC_d, A1c_f=A1c_f, MNSI_f=MNSI_f, OPH_f=OPH_f, Cre_f=Cre_f, UP_f=UP_f, 
        UPM_l=UPM_l, UPM_d=UPM_d, UACR=UACR, UACR_l=UACR_l, UACR_d=UACR_d, UPCR=UPCR, UPCR_l=UPCR_l, UPCR_d=UPCR_d, 
        date_f=date_f, today=today)



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
            return render_template("login.html")

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
    ID = session["user_id"]
    if ID == "doctor":
        global Patient
        ID = Patient
    if request.method == "POST":

        # Ensure all info are submitted
        if not request.form.get("name") or not request.form.get("birth") or not request.form.get("sex") or not request.form.get("phone") or not request.form.get("smoking") or not request.form.get("BW") or not request.form.get("BH") or not request.form.get("FH"):
            flash("Please provide all necessary personal information")
            return render_template("info.html", Patient=Patient)

        # Store info into database
        else:
            Name = request.form.get("name")
            Email = request.form.get("email")
            Birth = request.form.get("birth")
            Sex = request.form.get("sex")
            Phone = request.form.get("phone")
            Smoking = request.form.get("smoking")
            FH = request.form.get("FH")
            BW = request.form.get("BW")
            BH = request.form.get("BH")
            Time = datetime.now()

            HTN = CAD = Stroke = CHF = CKD = 0

            if request.form.get("HTN"):
                HTN = request.form.get("HTN")
            if request.form.get("CAD"):
                CAD = request.form.get("CAD")
            if request.form.get("stroke"):
                Stroke = request.form.get("stroke")
            if request.form.get("CKD"):
                CKD = request.form.get("CKD")
            if request.form.get("CHF"):
                CHF = request.form.get("CHF")

            db.execute("UPDATE users SET name=?, birth=?, sex=?, phone=?, smoking=?, HTN=?, CAD=?, stroke=?, CKD=?, CHF=?, FH=?, BH=?, email=? WHERE id=?", Name, Birth, Sex, Phone, Smoking, HTN, CAD, Stroke, CKD, CHF, FH, BH, Email, ID)
            db.execute("INSERT INTO BW (BW, id) VALUES (?,?) ", BW, ID)

            flash("Personal information stored!")

            # Determine if elderly info required

            Age = Time.year - int(Birth[0:4])
            if Age >= 65:
                ckd = int(db.execute("SELECT * FROM users WHERE id=?", ID)[0]["CKD"])
                return render_template("elderly.html", ckd=ckd, Patient=Patient)

        # Redirect user to info page
        return redirect("/")

    else:
        return render_template("info.html", Patient=Patient)



@app.route("/elderly", methods=["GET", "POST"])
def elderly():
    """Get elderly information"""
    ID = session["user_id"]
    if ID == "doctor":
        global Patient
        ID = Patient
            
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
        CAD = 0
        HTN = 0
        Stroke = 0
        if db.execute("SELECT CAD FROM users WHERE id = ?", ID)[0]["CAD"]=="T":
            CAD = 1
        if db.execute("SELECT HTN FROM users WHERE id = ?", ID)[0]["HTN"]=="T":
            HTN = 1
        if db.execute("SELECT stroke FROM users WHERE id = ?", ID)[0]["stroke"]=="T":
            Stroke = 1
        illness = ("falls", "depression", "arthritis", "incontinence", "stroke")
        for x in illness:
            if request.form.get(x) == "1":
                comorbidity += 1
        stage = (cancer,CHF,lung,CKD)
        for x in stage:
            if int(x) >= 1:
                comorbidity += 1
        comorbidity = comorbidity + CAD + HTN + Stroke


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
        if function==1 or function==2 or CHF==3 or CHF==4 or lung==2 or CKD==6 or cancer==2 or ADL>=2:
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
        ckd = int(db.execute("SELECT * FROM users WHERE id=?", ID)[0]["CKD"])
        return render_template("elderly.html", ckd=ckd, Patient=Patient)



@app.route("/record", methods=["GET", "POST"])
def record():
    """Update user lab and info"""
    ID = session["user_id"]
    if ID == "doctor":
        global Patient
        ID = Patient
        
    Date = request.form.get("date")

    if request.method == "POST":

        Item = ("BW", "SBP", "DBP", "A1c", "AC", "PC", "TCHO", "LDL", "HDL", "TG", "Cre", "UP_M", "UACR", "UPCR", "MNSI", "OPH_normal", "NPDR", "PDR", "CSME")

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
            return render_template("record.html", Patient=Patient)

        # The user gives some data
        else:
            OPH_done = False

            for x in Data:
                # Update BW
                if x=="BW":
                    BW = request.form.get("BW")
                    if not db.execute("SELECT * FROM BW WHERE id=? AND date=?", ID, Date):
                        db.execute("INSERT INTO BW (BW, id, date) VALUES (?,?,?) ", BW, ID, Date)
                    else:
                        db.execute("UPDATE BW SET BW=? WHERE id=? AND date=?", BW, ID, Date)

                # Update records(A1c, lipid, Cre, UP_M, UACR, MNSI)
                # Previous data on the same date will be erased!!! Fix this later.
                if x in ("A1c", "LDL", "HDL", "TCHO", "TG", "Cre", "UP_M", "UACR", "UPCR", "MNSI"):
                    value = float(request.form.get(x))
                    if not db.execute("SELECT * FROM records WHERE id=? AND date=?", ID, Date):
                        db.execute("INSERT INTO records ({}, id, date) VALUES (?,?,?) ".format(x), value, ID, Date)
                    else:
                        db.execute("UPDATE records SET {}=? WHERE id=? AND date=?".format(x), value, ID, Date)
                    # Update proteinuria in each record, 0=no, 1=stick negative only, 2=stick <=2+, 3=stick >=3+, 4=UACR, 5=UPCR
                    if x == "UP_M":
                        if value == 0:
                            db.execute("UPDATE records SET proteinuria=1 WHERE id=? AND date=?", ID, Date)
                        elif value <= 2:
                            db.execute("UPDATE records SET proteinuria=2 WHERE id=? AND date=?", ID, Date)
                        elif value >=3:
                            db.execute("UPDATE records SET proteinuria=3 WHERE id=? AND date=?", ID, Date)
                    if x == "UACR":
                        if value < 30:
                            db.execute("UPDATE records SET proteinuria=0 WHERE id=? AND date=?", ID, Date)
                        elif value >= 30:
                            db.execute("UPDATE records SET proteinuria=4 WHERE id=? AND date=?", ID, Date)
                    if x == "UPCR" and value >= 200:
                        db.execute("UPDATE records SET proteinuria=5 WHERE id=? AND date=?", ID, Date)

                # Update OPH
                if OPH_done == False and x in ("OPH_normal", "NPDR", "PDR","CSME"):
                    OPH_normal = request.form.get("OPH_normal")
                    NPDR = request.form.get("NPDR")
                    PDR = request.form.get("PDR")
                    CSME = request.form.get("CSME")
                    if not db.execute("SELECT * FROM OPH WHERE id=? AND date=?", ID, Date):
                        db.execute("INSERT INTO OPH (OPH_normal, NPDR, PDR, CSME, id, date) VALUES (?,?,?,?,?,?) ", OPH_normal, NPDR, PDR, CSME, ID, Date)
                    else:
                        db.execute("UPDATE OPH SET OPH_normal=?, NPDR=?, PDR=?, CSME=? WHERE id=? AND date=?", OPH_normal, NPDR, PDR, CSME, ID, Date)

                    OPH_done = True

                # Update AC PC sugar, allow multiple value in one day!
                if x == "AC":
                    AC = request.form.get("AC")
                    db.execute("INSERT INTO sugar (AC, sugar, id, date) VALUES (1,?,?,?) ", AC, ID, Date)
                if x == "PC":
                    PC = request.form.get("PC")
                    db.execute("INSERT INTO sugar (PC, sugar, id, date) VALUES (1,?,?,?) ", PC, ID, Date)

                # Update BP
                if x == "SBP":
                    SBP = request.form.get("SBP")
                    DBP = request.form.get("DBP")
                    db.execute("INSERT INTO BP (SBP, DBP, id, date) VALUES (?,?,?,?) ", SBP, DBP, ID, Date)

            # Redirect user to info page
            flash("Data updated!")
            return redirect("/target")

    else:
        today = str(datetime.now().date())
        return render_template("record.html", Patient=Patient, today=today)



@app.route("/trend", methods=["GET", "POST"])
def trend():
    ID = session["user_id"]
    if ID == "doctor":
        global Patient
        ID = Patient
    
    Item = request.form.get("item")
    Records = ["A1c", "LDL", "HDL", "Cre"]
    xValues = []
    yValues = []
    Target = []
    target = -1
    Y = ""


    if request.method == "POST":

        # Request dataset
        if Item == "BW":
            row = db.execute("SELECT BW, date FROM BW WHERE id=? ORDER BY date ASC LIMIT 168", ID)
        elif Item in Records:
            row = db.execute("SELECT {}, date FROM records WHERE id=? AND NOT {}=? ORDER BY date ASC LIMIT 20".format(Item, Item), ID, "")
        
        # Request target
        target_row = db.execute("SELECT * FROM target WHERE id=?", ID)
        if len(target_row) == 0:
            target = -1
        else:
            target = target_row[0][Item]
        

        if len(row) > 0:
            for point in row:
                xValues.append(point["date"])
                yValues.append(point.get(Item))
                
                # Set Target
                if target != -1:
                    Target.append(target)
                
            if Item == "BW":
                Y = "Body weight (kg)"
            elif Item == "A1c":
                Y = "HbA1c (%)"
            elif Item == "Cre":
                Y = "Creatinine (mg/dL)"
            else:
                Y = Item + "(mg/dL)"


        # Redirect user to home page
        return render_template("trend.html", Patient=Patient, xValues=xValues, yValues=yValues, Y=Y, Target=Target)

    else:
        return render_template("trend.html", Patient=Patient, xValues=xValues, yValues=yValues, Y=Y, Target=Target)