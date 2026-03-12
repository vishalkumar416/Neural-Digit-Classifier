# import libraries
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from google_auth_oauthlib.flow import Flow
import requests
import numpy as np
import hashlib
import os
from dotenv import load_dotenv
from datetime import datetime
from tensorflow.keras.models import load_model
from streamlit_drawable_canvas import st_canvas
from PIL import Image

# load env

load_dotenv()

st.set_page_config(page_title="Digit Recognition", layout="centered")

# ui design

st.markdown("""
<style>

[data-testid="stToolbar"],[data-testid="stHeader"]{
display:none;
}

[data-testid="stAppViewContainer"]{
background:linear-gradient(135deg,#5bc8d4,#7b6fcf,#c84b9e,#d44b7b);
}

.block-container{
max-width:480px;
padding-top:3rem;
}

.app-title-box{
background:linear-gradient(135deg,#5bc8d4,#7b6fcf);
padding:16px;
border-radius:12px;
color:white;
font-weight:700;
text-align:center;
margin-bottom:25px;
font-size:22px;
}

div[data-testid="stButton"]>button{
width:100%;
height:48px;
border-radius:40px;
border:none;
background:linear-gradient(90deg,#5bc8d4,#b44fc8,#d44b7b);
color:white;
font-weight:700;
font-size:15px;
}

.google-btn{
display:flex;
align-items:center;
justify-content:center;
gap:10px;
width:100%;
height:48px;
border-radius:40px;
background:white;
border:2px solid #e0e0e0;
text-decoration:none;
color:#333;
font-weight:600;
font-size:15px;
margin-top:4px;
margin-bottom:4px;
}

.google-icon{
width:20px;
height:20px;
}

</style>
""", unsafe_allow_html=True)

# firebase setup
firebase_config = {
    "type": st.secrets["FIREBASE_TYPE"],
    "project_id": st.secrets["FIREBASE_PROJECT_ID"],
    "private_key_id": st.secrets["FIREBASE_PRIVATE_KEY_ID"],
    "private_key": st.secrets["FIREBASE_PRIVATE_KEY"].replace("\\n","\n"),
    "client_email": st.secrets["FIREBASE_CLIENT_EMAIL"],
    "client_id": st.secrets["FIREBASE_CLIENT_ID"],
    "auth_uri": st.secrets["FIREBASE_AUTH_URI"],
    "token_uri": st.secrets["FIREBASE_TOKEN_URI"],
    "auth_provider_x509_cert_url": st.secrets["FIREBASE_AUTH_PROVIDER_X509_CERT_URL"],
    "client_x509_cert_url": st.secrets["FIREBASE_CLIENT_X509_CERT_URL"]
}

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)
db = firestore.client()

# load model
model = load_model("model/mnist_model.keras")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_next_user_id():
    users = db.collection("users").get()
    return len(users) + 1

# google login
def google_login_flow():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    flow = Flow.from_client_secrets_file(
        "firebase/digit-classifier-client_secret.json",
        scopes=["https://www.googleapis.com/auth/userinfo.email","openid"],
        redirect_uri="http://localhost:8501/"
    )
    if "code" in st.query_params:
        flow.fetch_token(code=st.query_params["code"])
        creds = flow.credentials
        user_info = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            params={"access_token":creds.token}
        ).json()
        email = user_info["email"]
        name = user_info.get("name",email.split("@")[0])
        users = db.collection("users").where("email","==",email).get()
        if users:
            user_id = users[0].id
            user_name = users[0].to_dict()["name"]
            user_int_id = users[0].to_dict()["user_id"]

        else:
            user_int_id = get_next_user_id()

            doc = db.collection("users").add({
                "user_id":user_int_id,
                "name":name,
                "email":email,
                "phone":"",
                "password":"",
                "created_at":datetime.utcnow()
            })

            user_id = doc[1].id
            user_name = name
        st.session_state.user_id = user_id
        st.session_state.user_name = user_name
        st.session_state.user_int_id = user_int_id

        st.query_params.clear()
        st.rerun()
    else:
        auth_url,_ = flow.authorization_url(
            prompt="consent",
            access_type="offline",
            include_granted_scopes="true",
            code_challenge=None
        )
        st.markdown(f"""
        <a href="{auth_url}" class="google-btn">
        Continue with Google
        </a>
        """, unsafe_allow_html=True)

# home page
def home():
    st.markdown("<div class='app-title-box'>🔢 Neural Digit Classifier</div>", unsafe_allow_html=True)
    email = st.text_input("Email")
    password = st.text_input("Password",type="password")
    if st.button("LOGIN",use_container_width=True):
        users = db.collection("users").where("email","==",email).get()
        if users:
            user = users[0].to_dict()
            if user.get("password")==hash_password(password):
                st.session_state.user_id = users[0].id
                st.session_state.user_name = user["name"]
                st.session_state.user_int_id = user["user_id"]

                st.rerun()
            else:
                st.error("Invalid password")
        else:
            st.error("User not found")
    st.write("---")
    google_login_flow()
    st.write("---")
    if st.button("SIGN UP",use_container_width=True):
        st.session_state.page="register"
        st.rerun()

# register page
def register():
    st.markdown("<div class='app-title-box'>Create Account</div>", unsafe_allow_html=True)
    name = st.text_input("Full Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone")
    password = st.text_input("Password",type="password")
    if st.button("CREATE ACCOUNT"):
        users = db.collection("users").where("email","==",email).get()
        if users:
            st.error("User already exists")
        else:
            user_int_id = get_next_user_id()
            db.collection("users").add({
                "user_id":user_int_id,
                "name":name,
                "email":email,
                "phone":phone,
                "password":hash_password(password),
                "created_at":datetime.utcnow()
            })
            st.success("Account created successfully")
            st.session_state.page="home"
            st.rerun()
    if st.button("Back to Login"):
        st.session_state.page="home"
        st.rerun()

# dashboard
def dashboard():
    st.markdown("<div class='app-title-box'>🔢 Digit Recognition Dashboard</div>", unsafe_allow_html=True)
    st.sidebar.success("Welcome "+st.session_state.user_name)
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
    st.write("Draw a digit (0-9)")
    canvas = st_canvas(
        fill_color="black",
        stroke_width=15,
        stroke_color="white",
        background_color="black",
        width=280,
        height=280,
        drawing_mode="freedraw",
        key="canvas"
    )
    if st.button("Predict Digit",use_container_width=True):
        if canvas.image_data is not None:
            img_array = canvas.image_data.astype("uint8")
            img = Image.fromarray(img_array,mode="RGBA")
            background = Image.new("RGBA",img.size,(0,0,0,255))
            background.paste(img,mask=img.split()[3])
            img = background.convert("L").resize((28,28))
            img_np = np.array(img)/255.0
            img_np = img_np.reshape(1,28,28,1)
            prediction = model.predict(img_np,verbose=0)
            digit = int(np.argmax(prediction))
            confidence = float(np.max(prediction)*100)
            db.collection("digit_predictions").add({
                "user_id":st.session_state.get("user_int_id"),
                "digit":digit,
                "confidence":confidence,
                "created_at":datetime.utcnow()
            })
            st.success("Predicted Digit: "+str(digit))
            st.metric("Confidence",str(round(confidence,2))+"%")
        else:
            st.warning("Please draw a digit first!")

# routing

if "page" not in st.session_state:
    st.session_state.page="home"
if st.session_state.get("user_id"):
    dashboard()
elif "code" in st.query_params:
    google_login_flow()
elif st.session_state.page=="register":
    register()
else:
    home()