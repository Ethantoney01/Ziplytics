
import streamlit as st
from supabase import create_client, Client
import openai
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic

# --- CONFIG ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
OPENAI_KEY = st.secrets["OPENAI_KEY"]

openai.api_key = OPENAI_KEY
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Ziplytics", layout="wide")
st.title("🏕️ Ziplytics — Smarter Land Investing")

# --- HELPER FUNCTIONS ---

def detect_listing_scam(listing):
    prompt = f"""
You are a real estate listing fraud detector. Analyze this land listing:

Address: {listing['address']}
Price: ${listing['price']}
Acreage: {listing['acreage']}
Zoning: {listing['zoning']}
Buildable: {listing['buildable']}
Utilities - Water: {listing['water']}, Electricity: {listing['electricity']}, Internet: {listing['internet']}
Images: {len(listing.get('image_urls', []))}

Rate scam likelihood 0–10 and explain.
"""
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()

def insert_listing(data):
    insert_result = supabase.table("land_listings").insert(data).execute()
    return insert_result.data[0]["id"]

def update_flag(listing_id, score, reason):
    flagged = score >= 7
    supabase.table("land_listings").update({
        "flagged": flagged,
        "flag_reason": reason,
        "flag_score": score
    }).eq("id", listing_id).execute()
    return flagged

def is_within_radius(listing, center, radius_mi):
    try:
        return geodesic(center, (listing["latitude"], listing["longitude"])).miles <= radius_mi
    except:
        return False

# --- LAND SUBMISSION FORM ---
with st.expander("📤 Submit New Land Listing"):
    with st.form("land_form"):
        address = st.text_input("Property Address")
        acreage = st.number_input("Acreage", min_value=0.1, step=0.1)
        price = st.number_input("Price ($)", min_value=0.0, step=100.0)
        zoning = st.selectbox("Zoning", ["Residential", "Agricultural", "Commercial", "Mixed", "Unknown"])
        buildable = st.selectbox("Is it Buildable?", ["Yes", "No", "Unknown"])
        flood_zone = st.selectbox("Flood Zone?", ["Yes", "No", "Unknown"])
        terrain = st.text_input("Terrain (e.g. flat, wooded, hilly)")
        road_access = st.selectbox("Road Access?", ["Yes", "No", "Gravel", "Private", "Unknown"])
        water = st.selectbox("Water Access", ["City", "Well", "None", "Unknown"])
        electricity = st.selectbox("Electricity", ["Yes", "No", "Nearby", "Unknown"])
        internet = st.selectbox("Internet Access", ["Yes", "No", "Satellite Only", "Unknown"])
        sewer = st.selectbox("Sewer", ["City", "Septic", "None", "Unknown"])
        lat = st.number_input("Latitude", format="%.6f")
        lon = st.number_input("Longitude", format="%.6f")
        photos = st.file_uploader("Upload Photos", accept_multiple_files=True, type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("Submit Listing")

    if submitted:
        uploaded_urls = []
        for file in photos[:5]:
            path = f"land_photos/{address.replace(' ', '_')}_{file.name}"
            supabase.storage().from_("property-photos").upload(path, file.read(), {"content-type": file.type})
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/property-photos/{path}"
            uploaded_urls.append(public_url)

        data = {
            "address": address,
            "acreage": acreage,
            "price": price,
            "zoning": zoning,
            "buildable": buildable,
            "flood_zone": flood_zone,
            "terrain": terrain,
            "road_access": road_access,
            "water": water,
            "electricity": electricity,
            "internet": internet,
            "sewer": sewer,
            "latitude": lat,
            "longitude": lon,
            "image_urls": uploaded_urls,
        }

        listing_id = insert_listing(data)
        result = detect_listing_scam(data)
        scam_score = int(result.split(":")[1].split("\n")[0].strip())
        reason = result.split("\n")[1].split(":")[1].strip()

        if update_flag(listing_id, scam_score, reason):
            st.warning(f"⚠️ Listing flagged: {reason}")
        else:
            st.success("✅ Listing submitted and passed moderation.")

# --- MAP + RADIUS SEARCH ---
st.subheader("📍 Search by Radius")
default_location = (39.9506, -86.2615)  # Zionsville
radius = st.slider("Radius (miles)", 5, 50, 10)

m = folium.Map(location=default_location, zoom_start=10)
folium.Marker(default_location, tooltip="Center").add_to(m)
folium.Circle(default_location, radius=radius * 1609.34, color="blue", fill=True, fill_opacity=0.2).add_to(m)
st_map = st_folium(m, width=700, height=500)

listings = supabase.table("land_listings").select("*").eq("flagged", False).execute().data
filtered = [l for l in listings if is_within_radius(l, default_location, radius)]

st.write(f"Found {len(filtered)} listings within {radius} miles.")

for land in filtered:
    st.markdown(f"### {land['address']} — {land['acreage']} Acres")
    st.write(f"Price: ${land['price']:,} | Zoning: {land['zoning']} | Buildable: {land['buildable']}")
    if land.get("image_urls"):
        st.image(land["image_urls"], width=300)
