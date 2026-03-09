import streamlit as st
from google import genai # The NEW SDK
from google.genai import types # The NEW SDK Types
from tavily import TavilyClient
import datetime
import pandas as pd
import json
import re
import pydeck as pdk
import requests
from duckduckgo_search import DDGS 
from streamlit_extras.let_it_rain import rain

# --- 1. SETUP ---
GEMINI_KEY = st.secrets.get("GEMINI_KEY", "")
TAVILY_KEY = st.secrets.get("TAVILY_KEY", "")

if GEMINI_KEY:
    client = genai.Client(api_key=GEMINI_KEY)
tavily = TavilyClient(api_key=TAVILY_KEY)

# Using the stable, high-capacity model to avoid 503 errors!
MODEL_ID = 'gemini-2.5-flash'

st.set_page_config(
    page_title="Make it Special", 
    page_icon="🌈", 
    layout="wide",
    initial_sidebar_state="expanded"  # THIS is the magic line!
)

# --- CATEGORY DICTIONARY (The Niche Engine) ---
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

# --- 2. SIDEBAR ---
with st.sidebar:
    st.title("🕵️ Personalization")
    start_loc = st.text_input("Starting Location", "York Mills, Toronto")
    group_type = st.selectbox("Setting", ["Solo", "Couple", "Friends", "Family"])
    budget = st.slider("Total Day Budget ($ per person)", 0, 300, 50, step=10)
    selected_date = st.date_input("What day is the plan for?", datetime.date.today())
    transport_mode = st.radio("Primary Transport", ["TTC", "Walking", "Driving", "Biking"])
    distance_range = st.slider("Distance Range (km)", 0, 100,10, step=5)
    st.divider()
    newsletter = st.text_area("Paste snippets from your email subscriptions here:", placeholder="e.g. 'Pop-up gallery on Broadview Ave'")

# --- 3. THE INTERFACE ---
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.title("🌈 What else in Toronto? ")
    st.markdown(f"### *Your special vibe for {selected_date.strftime('%A, %B %d')}*")

# --- 4. INPUTS (Dynamic Sub-Categories) ---
col1, col2 = st.columns(2)
with col1:
    user_schedule = st.text_input("What time works for you?", placeholder="e.g. 1pm - 10pm")
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
    
    # --- STEP 1: OPEN-METEO WEATHER API ---
    with st.spinner("🌡️ Fetching exact meteorological data..."):
        try:
            lat, lon = 43.7001, -79.4163
            target_date_iso = selected_date.strftime("%Y-%m-%d")
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max&timezone=America%2FNew_York&forecast_days=14"
            
            response = requests.get(url)
            data = response.json()
            daily_dates = data['daily']['time']
            
            if target_date_iso in daily_dates:
                idx = daily_dates.index(target_date_iso)
                t_max = data['daily']['temperature_2m_max'][idx]
                t_min = data['daily']['temperature_2m_min'][idx]
                precip = data['daily']['precipitation_probability_max'][idx]
                wind = data['daily']['wind_speed_10m_max'][idx]
                
                w_res = f"High {t_max}°C, Low {t_min}°C, Rain Chance {precip}%, Max Wind {wind} km/h"

            else:
                w_res = "Forecast unavailable for this date (too far in the future)."
        except Exception as e:
            w_res = "Weather data unavailable."

  # --- STEP 2: SEARCH (THE LOCAL WHITELIST) ---
    with st.spinner(f"🔍 Scouting hidden gems for {interests_str}..."):
        # We keep the query simple...
        query = f"Toronto {interests_str} exact schedule {date_str}"
        
        # ...but we lock the search engine inside this specific list of local/niche websites!
        trusted_sites = [
            "reddit.com/r/askTO",       # The holy grail of local advice
            "reddit.com/r/toronto", 
            "reddit.com/r/FoodToronto", # Specifically for those niche eats
            "blogto.com/eat",           # Targeted at food
            "streetsoftoronto.com",     # Great for North York/Etobicoke gems
            "curiocity.com",            # New openings
            "eventbrite.ca", 
            "meetup.com", 
            "alltrails.com"
        ]
        
        search_results = tavily.search(
            query=query, 
            search_depth="advanced", 
            include_images=True,
            include_domains=trusted_sites # The API will ONLY search these sites!
        )

    # --- STEP 3: REASONING & STORYTELLING ---
    with st.spinner("🧠 Designing your perfect day..."):
        if not GEMINI_KEY:
            st.error("🚨 API Key missing! Cannot connect to the AI brain.")
            st.stop()

        prompt = f"""
        You are a passionate, witty Toronto Local Expert. 
        Start: {start_loc} | Budget: ${budget} | Interests: {interests_str} | Weather: {w_res} | Setting: {group_type}
        USER TIME WINDOW: {user_schedule}
        TRANSPORT MODE: {transport_mode}
        MAX DISTANCE: {distance_range}
        
        USER PERSONA: The user has lived in Toronto for 10 years. NO tourist traps. They want authentic, off-the-beaten-path local experiences.
        GEOGRAPHIC SCOPE: Expand the horizon to the entire GTA (Scarborough, North York, Etobicoke, Markham, Mississauga). 
        Authentic local favorites often exist in strip malls or residential pockets—if the search data suggests a highly-rated spot in the suburbs, PRIORITIZE it over a generic downtown cafe.

        INSTRUCTIONS FOR DYNAMIC ITINERARY:
        1. STRICT STOP RULES: Provide enough activities to smoothly fill the ENTIRE USER TIME WINDOW without massive gaps. Usually, this means 3 to 5 stops depending on the length of the window. Commuting DOES NOT count as an activity. 
        2. THE PIVOT RULE: If the search data shows no exact events, or if you cancel an outdoor activity due to bad weather, YOU MUST TELL THE USER WHY (e.g., "Since it's raining, we swapped the hike for..."). 
        3. EXACT SCHEDULES: Start each event with a specific time block. Name the EXACT movie title playing, EXACT Meetup group, etc. If suggesting a movie, suggest a real current or classic movie that would be playing.
        4. SPORTS & VENUE BOOKING (CRITICAL): If the user selects sports requiring a facility, you MUST find real, specific private clubs or dedicated courts that allow booking. Do NOT suggest generic unbookable public parks. 
        5. TRANSPORT & WEATHER: If 'Walking' or 'Cycling', max total distance is {distance_range}km. If Rain/Snow > 40%, keep stops indoors.
        6. PARKING: If 'Driving', include specific nearby parking (e.g., 'Park at Green P Carpark...') for EVERY location.
        7. MANDATORY FOOD: Include at least one restaurant/cafe that fits the local vibe.
        8. CHEERFUL EXPERT TONE: Be enthusiastic and friendly, but keep it grounded. Instead of saying "magical vibes," say something like "locals love the huge windows and the smell of fresh roasting coffee." Use 2-3 punchy, high-energy sentences that highlight a factual "wow factor" about the place.
        9. PRACTICAL BULLETS: After the story, use bullet points for the [Website Link], [Google Maps Link], Parking/Transit info, and a 'Local Tip'.
        10. SUMMARY (THE QUICK RECAP): End with a 2-sentence cheerful summary. Sentence 1: The overall mood of the plan. Sentence 2: A practical tip for the day (e.g., "Today is a high-energy mix of art and alleyway coffee! Don't forget an extra TTC token for the bus ride back.")
        11. TRANSPORT (TTC SPECIFIC): If 'TTC' is selected, you MUST provide the specific subway station or bus/streetcar route numbers for every stop. Use the format: "TTC: Take Line [X] to [Station Name] Station" or "TTC: Route [Number] [Direction]". Be literal. Do NOT use metaphors like 'descent' or 'journey'—just give the names of the stations.
        12.THE SUBURBAN GEM RULE: If you find a "newly opened" spot or a "Reddit favorite" that isn't in the downtown core, include it. The user values a 20-minute drive for a legendary meal over a 5-minute walk to a mediocre one.
        
        Search Data for context: {search_results}

        CRITICAL DATA BLOCK (MUST BE AT THE VERY END):
        Provide the map coordinates in a strict JSON block exactly like this. 
        *IMPORTANT: Your VERY FIRST point in the JSON array must be the Start Location ({start_loc}).*
        ```json
        {{
          "master_link": "http://googleusercontent.com/maps.google.com/...",
          "points": [
            {{"name": "Starting Point ({start_loc})", "lat": 43.74, "lon": -79.40}},
            {{"name": "Stop 1 Name", "lat": 43.65, "lon": -79.38}},
            {{"name": "Stop 2 Name", "lat": 43.66, "lon": -79.40}}
          ]
        }}
        ```
        """

        try:
            response = client.models.generate_content(model=MODEL_ID, contents=prompt)
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
            brackets_found = re.findall(r'\[(.*?)\]', clean_display)
            if brackets_found:
                with DDGS() as ddgs:
                    for venue_name in set(brackets_found):
                        search_term = f"{venue_name} Toronto official photo"
                        ddg_images = list(ddgs.images(keywords=search_term, region="wt-wt", safesearch="on", type="photo", max_results=1))
                        
                        if ddg_images:
                            image_url = ddg_images[0].get('image')
                            processed_html = processed_html.replace(f"[{venue_name}]", f"**{venue_name}**")
                            img_md = f"![{venue_name}]({image_url})"
                            processed_html = processed_html.replace(f"**{venue_name}**", f"{img_md}\n\n**{venue_name}**")
        except:
            pass # Gracefully skip if images fail
        
        # --- DISPLAY THE RESULTS ---
        st.success("✨ Your bespoke day is ready!")

        # --- WEATHER DISPLAY (MOVED HERE) ---
        try:
            if 't_max' in locals():
                st.metric(
                    label="Forecast (H / L)", 
                    value=f"{t_max}° / {t_min}°C", 
                    delta=f"🌧️ {precip}% | 💨 {wind} km/h", 
                    delta_color="off"
                )
            else:
                st.info(f"🌦️ {w_res}")
        except:
            pass
            
        st.divider()
        
        out_col1, out_col2 = st.columns([1.5, 1])
        
        with out_col1:
            st.markdown(processed_html, unsafe_allow_html=True)
            if master_link:
                st.write("") 
                st.link_button("🚗 OPEN TURN-BY-TURN ROUTE IN GOOGLE MAPS", master_link, type="primary", use_container_width=True)

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
            emoji="😻", 
            font_size=54, 
            falling_speed=5, 
            animation_length="1" # Runs the animation once!
        )
        
        # --- 6. THE EXPORT BUTTON ---
        st.divider()
        st.subheader("📥 Save Your Plan")
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
