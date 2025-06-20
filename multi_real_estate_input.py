import requests
import streamlit as st

# ---------------- CONFIG ---------------- #
# Store your API keys in Streamlit secrets for safety
RAPIDAPI_KEY = st.secrets["RAPIDAPI_KEY"]

# API Hosts for rapidapi (you need to subscribe to these APIs on RapidAPI)
ZILLOW_HOST = "zillow-com1.p.rapidapi.com"
REALTOR_HOST = "realtor.p.rapidapi.com"
REDFIN_HOST = "redfin.p.rapidapi.com"  # hypothetical, Redfin may not have a public API on RapidAPI

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
}

# ---------------- FETCH FUNCTIONS ---------------- #

def fetch_zillow(location="Indianapolis, IN", num_results=5):
    url = f"https://{ZILLOW_HOST}/propertyExtendedSearch"
    params = {"location": location, "status_type": "FOR_SALE", "home_type": "Houses", "sort": "newest"}
    headers = HEADERS.copy()
    headers["X-RapidAPI-Host"] = ZILLOW_HOST

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get("props", [])[:num_results]
    else:
        st.warning(f"Zillow API error: {response.status_code}")
        return []

def fetch_realtor(location="Indianapolis, IN", num_results=5):
    url = f"https://{REALTOR_HOST}/properties/v2/list-for-sale"
    headers = HEADERS.copy()
    headers["X-RapidAPI-Host"] = REALTOR_HOST

    # Realtor.com expects location split into city and state_code
    city = location.split(",")[0].strip()
    state = location.split(",")[1].strip() if "," in location else ""

    params = {
        "city": city,
        "state_code": state,
        "limit": num_results,
        "offset": 0,
        "sort": "newest"
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get("properties", [])[:num_results]
    else:
        st.warning(f"Realtor API error: {response.status_code}")
        return []

def fetch_redfin(location="Indianapolis, IN", num_results=5):
    # Placeholder since Redfin API is not publicly available
    st.info("Redfin API integration placeholder — no public API available currently.")
    return []

# ---------------- DISPLAY FUNCTION ---------------- #

def display_property(prop, source="Unknown"):
    if source == "Zillow":
        address = prop.get("address", "No address")
        price = prop.get("price", "N/A")
        beds = prop.get("beds", "N/A")
        baths = prop.get("baths", "N/A")
        area = prop.get("area", "N/A")
        img = prop.get("imgSrc", None)
    elif source == "Realtor":
        address = prop.get("address", {}).get("line", "No address")
        price = prop.get("price", "N/A")
        beds = prop.get("beds", "N/A")
        baths = prop.get("baths", "N/A")
        area = prop.get("building_size", {}).get("size", "N/A")
        img = prop.get("photo", None)
    else:
        address = prop.get("address", "No address")
        price = prop.get("price", "N/A")
        beds = prop.get("beds", "N/A")
        baths = prop.get("baths", "N/A")
        area = prop.get("area", "N/A")
        img = None

    st.subheader(f"{address} ({source})")
    st.write(f"Price: ${price}")
    st.write(f"Beds: {beds} | Baths: {baths} | Sq Ft: {area}")
    if img:
        st.image(img, width=350)
    st.markdown("---")

# ---------------- MAIN STREAMLIT APP ---------------- #

def main():
    st.title("📊 Ziplytics | Multi-Source Real Estate Listings")
    location = st.text_input("Enter city/state or ZIP code:", "Indianapolis, IN")
    num_results = st.slider("Number of results per source:", min_value=1, max_value=10, value=5)

    if st.button("Fetch Listings"):
        with st.spinner("Fetching listings..."):
            zillow_props = fetch_zillow(location, num_results)
            realtor_props = fetch_realtor(location, num_results)
            redfin_props = fetch_redfin(location, num_results)

            total_results = 0
            if zillow_props:
                st.markdown("### Zillow Listings")
                for p in zillow_props:
                    display_property(p, source="Zillow")
                total_results += len(zillow_props)

            if realtor_props:
                st.markdown("### Realtor.com Listings")
                for p in realtor_props:
                    display_property(p, source="Realtor")
                total_results += len(realtor_props)

            if redfin_props:
                st.markdown("### Redfin Listings")
                for p in redfin_props:
                    display_property(p, source="Redfin")
                total_results += len(redfin_props)

            if total_results == 0:
                st.warning("No listings found from any source.")

if __name__ == "__main__":
    main()
