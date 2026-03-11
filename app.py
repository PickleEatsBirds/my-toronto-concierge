import streamlit as st
from google import genai
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

# --- 2. PAGE CONFIG & SESSION STATE ---
st.set_page_config(page_title="Today is Different", page_icon="🌈", layout="wide")

# Initialize the state manager to keep track of which screen the user is on
if 'page_stage' not in st.session_state:
    st.session_state.page_stage = 'intro'
if 'mbti_choice' not in st.session_state:
    st.session_state.mbti_choice = None
if 'surprise_data' not in st.session_state:     
    st.session_state.surprise_data = None


# ==========================================
# SCREEN 1: THE SURPRISE INTRO
# ==========================================
if st.session_state.page_stage == 'intro':
    st.markdown("<h1 style='text-align: center; margin-top: 100px;'>Surprise? 🪄</h1>", unsafe_allow_html=True)
    st.write("")
    
    col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
    with col2:
        if st.button("✨ YES, SURPRISE ME!", use_container_width=True, type="primary"):
            st.session_state.page_stage = 'mbti_select'
            st.rerun()
    with col3:
        if st.button("📝 NO! I PLAN EVERYTHING!", use_container_width=True):
            st.session_state.page_stage = 'manual'
            st.rerun()

# ==========================================
# SCREEN 2: MBTI SELECTOR
# ==========================================
elif st.session_state.page_stage == 'mbti_select':
    if st.button("⬅️ Back to Start"):
        st.session_state.page_stage = 'intro'
        st.rerun()
        
    st.markdown("<h2 style='text-align: center; margin-top: 30px;'> Your MBTI euh? 🦄</h2>", unsafe_allow_html=True)
    # st.markdown("<p style='text-align: center;'>We will curate a magical day tailored exactly to your personality vibe.</p>", unsafe_allow_html=True)
    
    mbti_options = ["INFP", "INTJ", "INFJ", "INTP", "ISFP", "ISFJ", "ISTJ", "ISTP", "ENTJ", "ENTP",  "ENFJ", "ENFP", "ESTJ", "ESFJ", "ESTP", "ESFP"]
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        selected_mbti = st.selectbox("Choose your type:", mbti_options)
        st.write("")
        if st.button("🧪 Some Poison Just For You", use_container_width=True, type="primary"):
            st.session_state.mbti_choice = selected_mbti
            st.session_state.page_stage = 'generating_surprise'
            st.rerun()

# ==========================================
# SCREEN 3: MAGIC POT & SURPRISE GENERATION
# ==========================================
elif st.session_state.page_stage == 'generating_surprise':
    if st.button("⬅️ Start Over"):
        st.session_state.surprise_data = None # Dumps the memory so you can generate a new day next time
        st.session_state.page_stage = 'intro'
        st.rerun()
        
    # The Magic Pot Animation HTML/CSS
    pot_html = f"""
    <div style="display: flex; justify-content: center; align-items: center; flex-direction: column; margin-top: 20px; margin-bottom: 20px;">
        <img src="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExd2NuN2N6YzV1ODVoZ2puaWRpcnJkZ2dldjZzMDBnMzJnNjBiZGRreiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/hXpBDPn8bZFp7SlcFa/giphy.gif" width="250">
        <h3 style="margin-top: 15px; font-family: monospace; color: #4CAF50;">Brewing magical green liquid for an {st.session_state.mbti_choice}...</h3>
    </div>
    """
    st.markdown(pot_html, unsafe_allow_html=True)


    import random

    # --- SET DYNAMIC RANDOM PARAMETERS FOR THE SURPRISE ---
    # We use session state here so the random parameters don't scramble if they click download!
    if 'rand_start' not in st.session_state or st.session_state.surprise_data is None:
        surprise_locations = [
            "Union Station, Toronto", "Kensington Market, Toronto", "The Beaches, Toronto", "Downsview Park"
            "High Park, Toronto", "Danforth & Broadview, Toronto", "Yonge & Eglinton, Toronto", 
            "Scarborough Town Centre", "First Markham Place", "North York Centre, Toronto", "Little Italy", "Square One, Missisaugua"
        ]
        st.session_state.rand_start = random.choice(surprise_locations)
        st.session_state.rand_budget = random.choice([0, 30, 80, 150, 250]) # From broke to baller
        st.session_state.rand_group = random.choice(["Solo", "Couple", "Friends"]) 
        st.session_state.rand_transport = random.choice(["TTC", "Walking", "TTC", "Driving"]) # Weighted to TTC so it's accessible
        
        # Randomize a 4 to 8 hour day, starting anywhere between 9am and 2pm
        start_hour = random.randint(9, 14)
        duration = random.randint(4, 8)
        st.session_state.rand_schedule = f"{start_hour:02d}:00 to {start_hour + duration:02d}:00"

    # Assign the scrambled values to your variables
    start_loc = st.session_state.rand_start
    budget = st.session_state.rand_budget
    group_type = st.session_state.rand_group
    transport_mode = st.session_state.rand_transport
    user_schedule = st.session_state.rand_schedule
    
    distance_range = 15
    selected_date = datetime.date.today()
    
    date_str = selected_date.strftime("%B %d, %Y")
    interests_str = f"Hidden gems, authentic local spots, and highly specific activities perfectly suited for an {st.session_state.mbti_choice} personality type"

# --- THE SURPRISE REVEAL TEXT ---
    st.markdown(f"""
    <div style='text-align: center; font-size: 18px; color: #666; margin-bottom: 20px; padding: 10px; border-radius: 10px; background-color: #f0f8ff;'>
        ✨ <b>The cauldron has spoken!</b> Brewing a <b>${budget}</b> day for <b>{group_type}</b> starting near <b>{start_loc.split(',')[0]}</b>.<br>
        <i>({user_schedule} via {transport_mode})</i>
    </div>
    """, unsafe_allow_html=True)

    # --- EXACT AI LOGIC (WRAPPED IN MEMORY CHECK) ---
    if st.session_state.surprise_data is None:
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
                
            with st.spinner(f"🔮 Scouting hidden gems for {interests_str}..."):
            # We split the start_loc to just grab the neighborhood name (e.g., "North York")
                local_area = start_loc.split(',')[0] 
                query = f"{local_area} Toronto {interests_str} exact schedule {date_str}"
            trusted_sites = [
                "reddit.com/r/askTO", "reddit.com/r/toronto", "reddit.com/r/FoodToronto", 
                "blogto.com/eat","blogto.com", "streetsoftoronto.com", "curiocity.com", 
                "eventbrite.ca", "meetup.com", "alltrails.com", "toronto.ca/explore-enjoy/festivals-events/",
                "toronto.ca/explore-enjoy/parks-recreation/"
            ]
            search_results = tavily.search(query=query, search_depth="advanced", include_images=True, include_domains=trusted_sites)

        with st.spinner("🦉 Hogwarts is listening to your heart..."):
            prompt = f"""
            You are a passionate, witty, and highly enthusiastic Toronto Local Expert. 
            Start: {start_loc} | Budget: ${budget} | Interests: {interests_str} | Weather: {w_res} | Setting: {group_type}
            USER TIME WINDOW: {user_schedule}
            TRANSPORT MODE: {transport_mode}
            MAX DISTANCE: {distance_range}
            
            MBTI TARGET: The user is an {st.session_state.mbti_choice}. TAILOR THE ENTIRE VIBE, venues, and storytelling exactly to the traits of this personality!
            
            USER PERSONA: NO tourist traps. They want authentic, off-the-beaten-path local experiences. Speak to them like a passionate peer—enthusiastic about the city's hidden gems, but keeping it real and grounded.
            GEOGRAPHIC SCOPE: Expand the horizon to the entire GTA (Scarborough, North York, Etobicoke, Markham, Mississauga, Barrie, Stratford, Elora, etc). 
            Authentic local favorites often exist in strip malls or residential pockets—if the search data suggests a highly-rated spot in the suburbs, PRIORITIZE it over a generic downtown cafe.

            INSTRUCTIONS FOR DYNAMIC ITINERARY:
           1. STRICT HUMAN PACING (MAX 4 STOPS): Humans are not robots! You MUST NOT schedule more than 4 actual stops/venues for the entire day, including meals. If the user's time window is massive (e.g., 8 to 15 hours), DO NOT pack it with more activities. Instead:
            - Allocate much longer, relaxed durations to each stop.
            - Schedule explicit "Rest/Wander Blocks" (e.g., "Spend 2 hours just wandering the boutique shops without a rigid plan", or "Grab a coffee, sit by the water, and just people-watch for an hour"). 
            - Prioritize a slow, stress-free pace so the user never feels rushed.
            2. LOCAL ANCHORING & CLUSTERING (CRITICAL): You MUST build the itinerary entirely within the {distance_range} from ({start_loc}). If they are starting late in the evening, keep them in North York, Markham, or Thornhill! DO NOT make the user commute 45+ minutes to downtown Toronto just to start their evening. Find the hidden gems in their immediate vicinity. Keep ALL activities strictly within a 15-20 minute radius of each other. Be a realistic human: if the schedule starts at 19:30, nobody wants to drive across the city just for dinner. Keep it local!
            3. THE PIVOT RULE: If the search data shows no exact events, or if you cancel an outdoor activity due to bad weather, YOU MUST TELL THE USER WHY (e.g., "Since it's raining, we swapped the hike for..."). 
            4. EXACT SCHEDULES: Start each event with a specific time block. Name the EXACT movie title playing, EXACT Meetup group, etc. If suggesting a movie, suggest a real current or classic movie that would be playing.
            5. NO BRACKETS: Do not use square brackets around venue names. Just bold them.
            6. SPORTS & VENUE BOOKING: If the user selects sports requiring a facility, you MUST find real, specific private clubs or dedicated courts that allow booking. Do NOT suggest generic unbookable public parks. 
            7. THE IRON-CLAD DISTANCE LIMIT: The ENTIRE itinerary must take place within a STRICT {distance_range}km radius of the Starting Location ({start_loc}). This applies to Driving, TTC, Walking, everything! If the user starts in North York with a 5km limit, DO NOT suggest Downtown Toronto, Queen West, or the CN Tower. Ban those words from your vocabulary. Keep them in their local {distance_range}km bubble!
            8. WEATHER: If Rain/Snow > 50%, keep all stops indoors.
            9. PARKING: If 'Driving', include specific nearby parking (e.g., 'Park at Green P Carpark...') for EVERY location.
            10. MANDATORY FOOD: 
              - Include at least one restaurant/cafe that fits the local vibe.
              - Don't pick these bubble team shops: The Alley, Coco, Chatime, TianRen.
              - (CRITICAL) Never have a agenda filled with FOOD and DRINK, at least non food-related event. 
            11. CHEERFUL & PASSIONATE TONE: Be enthusiastic and friendly! Highlight a factual "wow factor" about the place. Show genuine love for the city.
            12. THE SUBURBAN GEM RULE: If you find a "newly opened" spot or a "Reddit favorite" that isn't in the downtown core, include it. 
            13. TRANSPORT (TTC SPECIFIC): If 'TTC' is selected, you MUST provide the specific subway station or bus/streetcar route numbers for every stop. Be literal (e.g., "Take Line 2 to Christie Station").
            14. EXACT SCHEDULES & ZERO HALLUCINATION (CRITICAL): Start each event with a specific time block. If suggesting a movie, concert, or live event, you MUST ONLY use titles explicitly found in the provided 'Search Data'. If the Search Data does not list a specific movie title, DO NOT guess or invent one (e.g., do not guess unreleased movies). Instead, write "Catch a current release" and let the user check local listings.
            15. GROUP DYNAMICS (CRITICAL): Tailor the specific venue selection and storytelling vibe to the Setting ({group_type}). 

            FORMATTING TEMPLATE (YOU MUST FOLLOW THIS EXACTLY FOR EVERY STOP):
            ### ⏰ TIME BLOCK - 📍 **VENUE NAME**
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
        
        # SAVE EVERYTHING TO MEMORY
        st.session_state.surprise_data = {
            "clean_display": clean_display,
            "map_points": map_points,
            "master_link": master_link,
            "weather_data": weather_data,
            "w_res": w_res
        }
    else:
        # LOAD EVERYTHING FROM MEMORY
        clean_display = st.session_state.surprise_data["clean_display"]
        map_points = st.session_state.surprise_data["map_points"]
        master_link = st.session_state.surprise_data["master_link"]
        weather_data = st.session_state.surprise_data["weather_data"]
        w_res = st.session_state.surprise_data["w_res"]

    st.success("✨ Your bespoke surprise day is ready!")
    
    # --- WEATHER DISPLAY (Restored) ---
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
        st.markdown(clean_display, unsafe_allow_html=True)
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
            
    rain(emoji="🐱", font_size=54, falling_speed=5, animation_length="1")
    
    # --- THE EXPORT BUTTON ---
    st.divider()
    st.subheader("🪬 Save Your Plan")
    st.caption("Download the text version of your itinerary with clickable links.")
    file_name = f"Toronto_Itinerary_{selected_date.strftime('%b_%d')}.md"
    st.download_button(
        label="📄 Download Itinerary (.md)",
        data=clean_display.encode('utf-8'),  # <--- THIS IS THE MAGIC FIX! ✨
        file_name=file_name,
        mime="text/markdown",
        type="secondary",
        use_container_width=True
    )

# ==========================================
# SCREEN 4: ORIGINAL MANUAL FLOW (UNCHANGED)
# ==========================================
elif st.session_state.page_stage == 'manual':
    if st.button("⬅️ Back to Start"):
        st.session_state.page_stage = 'intro'
        st.rerun()
        
    CATEGORY_MAP = {
        "Arts and Culture": ["Galleries", "Theater", "Art Festivals" , "Museums", "Paint Night", "DIY workshops","Photography", "Musicals"],
        "City Walk": ["Historical Architecture","Street Art Walks", "Waterfront Walk", "Hidden Courtyards","Beautiful Neighbourhoods","Cozy Streets", "Boutique Shopping", "Thifting"],
        "Food Experience": ["Exotic Food Crawls", "Bubble Tea Time", "Asian Cuisine", "Authentic Chinese", "Hidden Speakeasies", "Late Night Eats", "Romantic Dates", "Vegan Tasting Menus", "Coffee Roasters", "Drink Up"],
        "Animal Therapy": ["Cat Cafes", "Dog Parks", "Goat Yoga", "Reptile Shows", "Animal Farms"],
        "Nature and Outdoor": ["Hiking Trails", "Botanical Gardens", "Beach Walks","Foraging","City Parks", "Bird Watching", "Picnic Spots","Star Gazing", "Biking Adventure", "Paddling"],
        "Sports & Fitness": ["Tennis", "Badminton", "Indoor Climbing", "Biking", "Running", "Swimming", "Skiing and Snowboarding", "Pickleball", "Yoga", "Dancing"],
        "Niche Markets": ["Flea Markets", "Artisan Pop-ups", "Farmers Markets", "Antique Fairs", "Toront Show Events"],
        "Entertainment": ["Live Music", "Board Game Meetups", "Movies", "Community Festivals", "Comedy Shows", "Arcade Games", "Karaoke"],
        "Relax and self-care":["Massage Therapy", "Aroma Spa", "Facial Spa", "Maniure", "Shopping", "Baking Class"]
    }

    st.markdown("<h3 style='text-align: center;'>🌈 What else in Toronto? 🧿 </h3>", unsafe_allow_html=True)
    st.divider()
    st.markdown("#### 🪄 Wave Your Wand ✨")

    param_col1, param_col2 = st.columns(2)

    with param_col1:
        start_loc = st.text_input("Starting Location", "York Mills, Toronto")
        selected_date = st.date_input("What day is the plan for?", datetime.date.today())
        budget = st.slider("Total Day Budget ($ per person)", 0, 300, 50, step=10)

    with param_col2:
        group_type = st.selectbox("Setting", ["Solo", "Couple", "Friends", "Family"])
        transport_mode = st.radio("Primary Transport", ["Driving", "TTC", "Walking", "Biking"], horizontal=True)
        distance_range = st.slider("Distance Range (km)", 0, 100, 10, step=5)

    col1, col2 = st.columns(2)

    with col1:
        # Changed to range(0, 24) to cover 00:00 to 23:30
        times = [f"{h:02d}:{m:02d}" for h in range(0, 24) for m in (0, 30)]
        st.markdown("**When are you ready?**")
        time_col1, time_col2 = st.columns(2)
        with time_col1:
            # Index 20 is 10:00 AM (since it starts at 00:00 now)
            head_out = st.selectbox("Head Out Time", options=times, index=20) 
        with time_col2:
            # Index 44 is 22:00 (10:00 PM)
            back_home = st.selectbox("Back Home Time", options=times, index=44) 
        
        # SMART MIDNIGHT LOGIC: If the end time is "earlier" than the start time, tell the AI it's tomorrow!
        if times.index(back_home) < times.index(head_out):
            user_schedule = f"{head_out} today to {back_home} the next day"
        else:
            user_schedule = f"{head_out} to {back_home}"

    with col2:
        st.markdown("**What are you in the mood for?**")
        main_categories = st.multiselect("1. Choose broad vibes:", list(CATEGORY_MAP.keys()), default=["Food Experience"])
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
            
            USER PERSONA: NO tourist traps. They want authentic, off-the-beaten-path local experiences. Speak to them like a passionate peer—enthusiastic about the city's hidden gems, but keeping it real and grounded.
            GEOGRAPHIC SCOPE: Expand the horizon to the entire GTA (Scarborough, North York, Etobicoke, Markham, Mississauga). 
            Authentic local favorites often exist in strip malls or residential pockets—if the search data suggests a highly-rated spot in the suburbs, PRIORITIZE it over a generic downtown cafe.

            INSTRUCTIONS FOR DYNAMIC ITINERARY:
           1. STRICT HUMAN PACING (MAX 4 STOPS): Humans are not robots! You MUST NOT schedule more than 4 actual stops/venues for the entire day, including meals. If the user's time window is massive (e.g., 8 to 15 hours), DO NOT pack it with more activities. Instead:
            - Allocate much longer, relaxed durations to each stop.
            - Schedule explicit "Rest/Wander Blocks" (e.g., "Spend 2 hours just wandering the boutique shops without a rigid plan", or "Grab a coffee, sit by the water, and just people-watch for an hour"). 
            - Prioritize a slow, stress-free pace so the user never feels rushed.
            2. LOCAL ANCHORING & CLUSTERING (CRITICAL): You MUST build the itinerary entirely within the {distance_range} from ({start_loc}). If they are starting late in the evening, keep them in North York, Markham, or Thornhill! DO NOT make the user commute 45+ minutes to downtown Toronto just to start their evening. Find the hidden gems in their immediate vicinity. Keep ALL activities strictly within a 15-20 minute radius of each other. Be a realistic human: if the schedule starts at 19:30, nobody wants to drive across the city just for dinner. Keep it local!
            3. THE PIVOT RULE: If the search data shows no exact events, or if you cancel an outdoor activity due to bad weather, YOU MUST TELL THE USER WHY (e.g., "Since it's raining, we swapped the hike for..."). 
            4. EXACT SCHEDULES: Start each event with a specific time block. Name the EXACT movie title playing, EXACT Meetup group, etc. If suggesting a movie, suggest a real current or classic movie that would be playing.
            5. NO BRACKETS: Do not use square brackets around venue names. Just bold them.
            6. SPORTS & VENUE BOOKING: If the user selects sports requiring a facility, you MUST find real, specific private clubs or dedicated courts that allow booking. Do NOT suggest generic unbookable public parks. 
            7. THE IRON-CLAD DISTANCE LIMIT: The ENTIRE itinerary must take place within a STRICT {distance_range}km radius of the Starting Location ({start_loc}). This applies to Driving, TTC, Walking, everything! If the user starts in North York with a 5km limit, DO NOT suggest Downtown Toronto, Queen West, or the CN Tower. Ban those words from your vocabulary. Keep them in their local {distance_range}km bubble!
            8. WEATHER: If Rain/Snow > 50%, keep all stops indoors.
            9. PARKING: If 'Driving', include specific nearby parking (e.g., 'Park at Green P Carpark...') for EVERY location.
            10. MANDATORY FOOD: 
              - Include at least one restaurant/cafe that fits the local vibe.
              - Don't pick these bubble team shops: The Alley, Coco, Chatime, TianRen.
              - (CRITICAL) Never have a agenda filled with FOOD and DRINK, at least non food-related event. 
            11. CHEERFUL & PASSIONATE TONE: Be enthusiastic and friendly! Highlight a factual "wow factor" about the place. Show genuine love for the city.
            12. THE SUBURBAN GEM RULE: If you find a "newly opened" spot or a "Reddit favorite" that isn't in the downtown core, include it. 
            13. TRANSPORT (TTC SPECIFIC): If 'TTC' is selected, you MUST provide the specific subway station or bus/streetcar route numbers for every stop. Be literal (e.g., "Take Line 2 to Christie Station").
            14. EXACT SCHEDULES & ZERO HALLUCINATION (CRITICAL): Start each event with a specific time block. If suggesting a movie, concert, or live event, you MUST ONLY use titles explicitly found in the provided 'Search Data'. If the Search Data does not list a specific movie title, DO NOT guess or invent one (e.g., do not guess unreleased movies). Instead, write "Catch a current release" and let the user check local listings.
            15. GROUP DYNAMICS (CRITICAL): Tailor the specific venue selection and storytelling vibe to the Setting ({group_type}). 
            - If 'Solo': Focus on exploration, quality 'me time', and connecting with the local community.
            - If 'Couple': Focus on intimate, relaxing, and romantic atmospheres.
            - If 'Friends': Focus on fun, highly social activities, and creating shared group memories.
            - If 'Family': Focus on accessible, universally engaging, and bonding experiences.

            FORMATTING TEMPLATE (YOU MUST FOLLOW THIS EXACTLY FOR EVERY STOP):
            ### ⏰ TIME BLOCK - 📍 **VENUE NAME**
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
            st.markdown(clean_display, unsafe_allow_html=True)
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
            data=clean_display.encode('utf-8'),  # <--- THIS IS THE MAGIC FIX! ✨
            file_name=file_name,
            mime="text/markdown",
            type="secondary",
            use_container_width=True
        )
