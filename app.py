import streamlit as st
from google import genai # WE ARE BACK!
from google.genai import types
from tavily import TavilyClient
import datetime
import pandas as pd
import json
import re
import pydeck as pdk
import requests
from duckduckgo_search import DDGS 
from streamlit_extras.let_it_rain import rain

@st.cache_data(ttl=3600) # Caches weather for 1 hour
def get_toronto_weather(target_date_iso):
    try:
        lat, lon = 43.7001, -79.4163
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max&timezone=America%2FNew_York&forecast_days=14"
        response = requests.get(url, timeout=5)
        return response.json()
    except:
        return None

# --- 1. SETUP & KEYS ---
GEMINI_KEY = st.secrets.get("GEMINI_KEY", "")
TAVILY_KEY = st.secrets.get("TAVILY_KEY", "")

if GEMINI_KEY:
    client = genai.Client(api_key=GEMINI_KEY)
else:
    st.error("🚨 Missing GEMINI_KEY in Streamlit Secrets!")
    st.stop()
    
if TAVILY_KEY:
    tavily = TavilyClient(api_key=TAVILY_KEY)
else:
    st.error("🚨 Missing TAVILY_KEY in Streamlit Secrets!")
    st.stop()

# Using your Paid Tier 2.5 Flash model
MODEL_ID = 'gemini-2.5-flash'

# --- 2. THE INTERFACE ---
st.set_page_config(page_title="Make it Special", page_icon="🌈", layout="wide")

CATEGORY_MAP = {
    "Arts and Culture": ["Art Galleries", "Art Workshops", "Theater", "Art Festivals" , "Museums", "Life Drawing"],
    "City Walk": ["Historical Architecture","Street Art Walks", "Waterfront Walk", "Hidden Courtyards","Beautiful Neighbourhoods","Cozy Streets", "Boutique Shopping", "Thifting"],
    "Food Experience": ["Hidden Speakeasies", "Vegan Tasting Menus", "Coffee Roasters", "Exotic Food Crawls", "Late Night Eats", "Romantic Dates"],
    "Animal Therapy": ["Cat Cafes", "Dog Parks", "Goat Yoga", "Reptile Shows", "Animal Farms"],
    "Nature and Outdoor": ["Hiking Trails", "Botanical Gardens", "Beach Walks","Foraging","Provincial Parks", "Bird Watching", "Picnic Spots","Star Gazing"],
    "Sports": ["Tennis", "Badminton", "Indoor Climbing", "Biking", "Running Clubs", "Swimming", "Ski and Snowboarding"],
    "Niche Markets": ["Flea Markets", "Artisan Pop-ups", "Farmers Markets", "Antique Fairs"],
    "Entertainment & Hobbies": ["Live Indie Music", "Board Game Meetups", "Hot Movies", "Community Festivals", "Comedy Shows"]
}

st.markdown("<h3 style='text-align: center;'>🌈 What can you do in this boring Toronto? 🧿 </h3>", unsafe_allow_html=True)
st.divider()
st.markdown("#### 🪄 Wave Your Wand ✨")

param_col1, param_col2 = st.columns(2)

with param_col1:
    start_loc = st.text_input("Starting Location", "York Mills, Toronto")
    selected_date = st.date_input("What day is the plan for?", datetime.date.today())
    budget = st.slider("Total Day Budget ($ per person)", 0, 300, 50, step=10)

with param_col2:
    group_type = st.selectbox("Setting", ["Solo", "Couple", "Friends", "Family"])
    transport_mode = st.radio("Primary Transport", ["TTC", "Walking", "Driving", "Biking"], horizontal=True)
    distance_range = st.slider("Distance Range (km)", 0, 100, 10, step=5)

col1, col2 = st.columns(2)

with col1:
    times = [f"{h:02d}:{m:02d}" for h in range(7, 24) for m in (0, 30)]
    st.markdown("**When are you ready?**")
    time_col1, time_col2 = st.columns(2)
    with time_col1:
        head_out = st.selectbox("Head Out Time", options=times, index=10) 
    with time_col2:
        back_home = st.selectbox("Back Home Time", options=times, index=22) 
    user_schedule = f"{head_out} to {back_home}"

with col2:
    st.markdown("**What are you in the mood for?**")
    main_categories = st.multiselect("1. Choose broad vibes:", list(CATEGORY_MAP.keys()), default=["Arts and Culture"])
    final_interests = []
    if main_categories:
        for cat in main_categories:
            subs = st.multiselect(f"2. Pick specific '{cat}' activities:", CATEGORY_MAP[cat])
            final_interests.extend(subs)

st.divider()

# --- 5. THE AGENT LOGIC ---
if st.button("🚀 Build My Epic Route", use_container_width=True, type="primary"):
    
    if not final_interests:
        st.warning("Please pick at least one specific activity from the dropdowns above so I can find niche events!")
        st.stop()
        
    date_str = selected_date.strftime("%B %d, %Y")
    interests_str = ", ".join(final_interests)
    
    # --- STEP 1: WEATHER ---
    with st.spinner("🌡️ Fetching exact meteorological data..."):
        weather_data = None
        w_res = "Weather data unavailable."
        target_date_iso = selected_date.strftime("%Y-%m-%d")
        data = get_toronto_weather(target_date_iso)
        
        if data and 'daily' in data and target_date_iso in data['daily']['time']:
            idx = data['daily']['time'].index(target_date_iso)
            weather_data = {
                "max": data['daily']['temperature_2m_max'][idx],
                "min": data['daily']['temperature_2m_min'][idx],
                "precip": data['daily']['precipitation_probability_max'][idx],
                "wind": data['daily']['wind_speed_10m_max'][idx]
            }
            w_res = f"High {weather_data['max']}°C, Low {weather_data['min']}°C, Rain {weather_data['precip']}%, Wind {weather_data['wind']}km/h"
        else:
            w_res = "Forecast not available for this date yet."

    # --- STEP 2: SEARCH ---
    with st.spinner(f"🔮 Scouting hidden gems for {interests_str}..."):
        query = f"Toronto {interests_str} exact schedule {date_str}"
        trusted_sites = [
            "reddit.com/r/askTO", "reddit.com/r/toronto", "reddit.com/r/FoodToronto", 
            "blogto.com/eat","blogto.com", "streetsoftoronto.com", "curiocity.com", 
            "eventbrite.ca", "meetup.com", "alltrails.com", "toronto.ca/explore-enjoy/festivals-events/",
            "toronto.ca/explore-enjoy/parks-recreation/"
        ]
        search_results = tavily.search(query=query, search_depth="advanced", include_images=True, include_domains=trusted_sites)

    # --- STEP 3: REASONING & STORYTELLING (GEMINI) ---
    with st.spinner("🦉 Hogwarts is designing your perfect day..."):
        prompt = f"""
        You are a passionate, witty, and highly enthusiastic Toronto Local Expert. 
        Start: {start_loc} | Budget: ${budget} | Interests: {interests_str} | Weather: {w_res} | Setting: {group_type}
        USER TIME WINDOW: {user_schedule}
        TRANSPORT MODE: {transport_mode}
        MAX DISTANCE: {distance_range}
        
        USER PERSONA: The user has lived in Toronto for 10 years. NO tourist traps. They want authentic, off-the-beaten-path local experiences. Speak to them like a passionate peer—enthusiastic about the city's hidden gems, but keeping it real and grounded.
        GEOGRAPHIC SCOPE: Expand the horizon to the entire GTA (Scarborough, North York, Etobicoke, Markham, Mississauga). 
        Authentic local favorites often exist in strip malls or residential pockets—if the search data suggests a highly-rated spot in the suburbs, PRIORITIZE it over a generic downtown cafe.

        INSTRUCTIONS FOR DYNAMIC ITINERARY:
        1. STRICT STOP RULES: Provide enough activities to smoothly fill the ENTIRE USER TIME WINDOW without massive gaps. Usually, this means 3 to 5 stops depending on the length of the window. Commuting DOES NOT count as an activity. 
        2. NEIGHBORHOOD CLUSTERING (CRITICAL): Do NOT zig-zag across the city. All stops must logically flow and ideally stay within a 15-minute radius of each other.
        3. THE PIVOT RULE: If the search data shows no exact events, or if you cancel an outdoor activity due to bad weather, YOU MUST TELL THE USER WHY (e.g., "Since it's raining, we swapped the hike for..."). 
        4. EXACT SCHEDULES: Start each event with a specific time block. Name the EXACT movie title playing, EXACT Meetup group, etc. If suggesting a movie, suggest a real current or classic movie that would be playing.
        5. THE BRACKET RULE FOR IMAGES (CRITICAL): You MUST wrap the specific name of the MAIN VENUE in square brackets. Example: [Distillery District] or [BMV Books]. DO NOT put brackets around subway stations, neighborhoods, or movie titles. ONLY the physical venue/restaurant. This triggers our photo engine.
        6. SPORTS & VENUE BOOKING: If the user selects sports requiring a facility, you MUST find real, specific private clubs or dedicated courts that allow booking. Do NOT suggest generic unbookable public parks. 
        7. TRANSPORT & WEATHER: If 'Walking' or 'Cycling', max total distance is {distance_range}km. If Rain/Snow > 40%, keep stops indoors.
        8. PARKING: If 'Driving', include specific nearby parking (e.g., 'Park at Green P Carpark...') for EVERY location.
        9. MANDATORY FOOD: Include at least one restaurant/cafe that fits the local vibe.
        10. CHEERFUL & PASSIONATE TONE: Be enthusiastic and friendly! Highlight a factual "wow factor" about the place. Show genuine love for the city.
        11. THE SUBURBAN GEM RULE: If you find a "newly opened" spot or a "Reddit favorite" that isn't in the downtown core, include it. 
        12. TRANSPORT (TTC SPECIFIC): If 'TTC' is selected, you MUST provide the specific subway station or bus/streetcar route numbers for every stop. Be literal (e.g., "Take Line 2 to Christie Station").
        13. EXACT SCHEDULES & ZERO HALLUCINATION (CRITICAL): Start each event with a specific time block. If suggesting a movie, concert, or live event, you MUST ONLY use titles explicitly found in the provided 'Search Data'. If the Search Data does not list a specific movie title, DO NOT guess or invent one (e.g., do not guess unreleased movies). Instead, write "Catch a current release" and let the user check local listings.

        FORMATTING TEMPLATE (YOU MUST FOLLOW THIS EXACTLY FOR EVERY STOP):
        ### 💫 TIME BLOCK - 🐸 [VENUE NAME]
        * **The Vibe:** [1-2 passionate sentences about why locals love it]
        * **Transit/Parking:** [Specific TTC Line/Route or Parking advice]
        * **Links:** [Website](https://www.google.com/search?q=VENUE+NAME+Toronto) | [Google Maps](https://www.google.com/maps/search/[Venue+Name]+Toronto)
        * 💡 **Local Tip:** [One highly practical or insider tip]
        ---
        
        13. SUMMARY (THE QUICK RECAP): End the entire itinerary with a 2-sentence cheerful summary. Sentence 1: The overall mood. Sentence 2: A practical tip.

        Search Data for context: {search_results}

        CRITICAL DATA BLOCK (MUST BE AT THE VERY END EXACTLY AS SHOWN):
        Provide the map coordinates in a strict JSON block exactly like this. 
        *IMPORTANT: Your VERY FIRST point in the JSON array must be the Start Location ({start_loc}).*
        ```json
        {{
          "master_link": "http://googleusercontent.com/maps.google.com/...",
          "points": [
            {{"name": "Starting Point ({start_loc})", "lat": 43.74, "lon": -79.40}},
            {{"name": "Stop 1 Name", "lat": 43.65, "lon": -79.38}}
          ]
        }}
        ```
        """
        try:
            # Gemini Call!
            response = client.models.generate_content(
                model=MODEL_ID, 
                contents=prompt
            )
            full_text = response.text
            
            map_points = []
            master_link = ""
            clean_display = full_text
            
            json_match = re.search(r'```json\n(.*?)\n```', full_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                map_points = data.get("points", [])
                master_link = data.get("master_link", "")
                clean_display = re.sub(r'```json\n(.*?)\n```', '', full_text, flags=re.DOTALL)
                
        except Exception as e:
            st.error(f"🕵️ Route API Error: {e}")
            st.stop()

# --- STEP 4: VISUAL GUARDRAIL (DuckDuckGo) ---
    with st.spinner("🖼️ Fetching relevant local photos..."):
        processed_html = clean_display
        try:
            # Find everything inside [brackets]
            brackets_found = re.findall(r'\[(.*?)\]', clean_display)
            
            # Filter out junk
            junk = ["Website", "Google Maps", "Insert Time Block", "Insert Venue Name"]
            venues_to_search = [v for v in set(brackets_found) if v not in junk and len(v) > 3]

            # 🛠️ DEBUG 1: Tell us what it found!
            st.info(f"🔍 DEBUG - Venues detected: {venues_to_search}")

            if venues_to_search:
                with DDGS() as ddgs:
                    for venue_name in venues_to_search[:3]:
                        try:
                            search_term = f"{venue_name} Toronto"
                            ddg_images = list(ddgs.images(keywords=search_term, region="wt-wt", safesearch="on", max_results=1))
                            
                            if ddg_images:
                                image_url = ddg_images[0].get('image')
                                # Added extra spacing for Streamlit Markdown rendering
                                img_md = f"**{venue_name}**\n\n![{venue_name}]({image_url})\n\n"
                                processed_html = processed_html.replace(f"[{venue_name}]", img_md)
                                
                                # 🛠️ DEBUG 2: Success!
                                st.success(f"📸 DEBUG - Image loaded for: {venue_name}")
                            else:
                                processed_html = processed_html.replace(f"[{venue_name}]", f"**{venue_name}**")
                                
                                # 🛠️ DEBUG 3: Empty Results
                                st.warning(f"⚠️ DEBUG - DuckDuckGo found NO photos for: {venue_name}")
                        except Exception as img_e:
                            processed_html = processed_html.replace(f"[{venue_name}]", f"**{venue_name}**")
                            
                            # 🛠️ DEBUG 4: Blocked / Error
                            st.error(f"🚨 DEBUG - DuckDuckGo Blocked us on {venue_name}: {img_e}")
            else:
                st.warning("⚠️ DEBUG - The AI forgot to use [Brackets] around the venues!")
                
        except Exception as e:
            st.error(f"📸 Master image loop crashed: {e}")
        
        st.success("✨ Your bespoke day is ready!")

    # --- WEATHER DISPLAY ---
        if weather_data:
            st.metric(
                label=f"Forecast for {selected_date.strftime('%B %d')}", 
                value=f"{weather_data['max']}° / {weather_data['min']}°C", 
                delta=f"🌧️ {weather_data['precip']}% | 💨 {weather_data['wind']} km/h", 
                delta_color="off"
            )
        else:
            st.info(f"🌦️ Note: {w_res}")
            
        st.divider()
        
        out_col1, out_col2 = st.columns([1.5, 1])
        
        with out_col1:
            st.markdown(processed_html, unsafe_allow_html=True)
            if master_link:
                st.write("") 
                st.link_button("🧚 OPEN TURN-BY-TURN ROUTE IN GOOGLE MAPS", master_link, type="primary", use_container_width=True)

        with out_col2:
            if map_points and len(map_points) > 1:
                st.markdown("### 🗺️ Visual Route")
                st.caption("A high-level view of your journey!")
                
                df = pd.DataFrame(map_points)
                path_coords = [[row['lon'], row['lat']] for index, row in df.iterrows()]
                path_data = pd.DataFrame({'path': [path_coords]})
                
                scatter_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df,
                    get_position='[lon, lat]',
                    get_color='[255, 75, 75, 255]',
                    get_radius=250,
                    pickable=True
                )
                
                path_layer = pdk.Layer(
                    "PathLayer",
                    data=path_data,
                    get_path="path",
                    get_color="[0, 150, 255, 200]", 
                    width_scale=20,
                    width_min_pixels=3,
                )
                
                view_state = pdk.ViewState(
                    latitude=df['lat'].mean(),
                    longitude=df['lon'].mean(),
                    zoom=11,
                    pitch=0
                )
                
                r = pdk.Deck(layers=[path_layer, scatter_layer], initial_view_state=view_state, tooltip={"text": "{name}"})
                st.pydeck_chart(r)
            else:
                st.info("Visual map unavailable this time.")
                
        rain(
            emoji="🐱", 
            font_size=54, 
            falling_speed=5, 
            animation_length="1"
        )
        
        # --- 6. THE EXPORT BUTTON ---
        st.divider()
        st.subheader("🪬 Save Your Plan")
        st.caption("Download the text version of your itinerary with clickable links.")
        file_name = f"Toronto_Itinerary_{selected_date.strftime('%b_%d')}.md"
        st.download_button(
            label="📄 Download Itinerary (.md)",
            data=clean_display,
            file_name=file_name,
            mime="text/markdown",
            type="secondary",
            use_container_width=True
        )
