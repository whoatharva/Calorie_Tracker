import streamlit as st
from dotenv import load_dotenv
import os
import json
from datetime import date
import pandas as pd
import plotly.express as px
from openai import AzureOpenAI
from streamlit_js_eval import streamlit_js_eval

# Load environment variables
load_dotenv()

# Azure OpenAI client setup
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

# App config
st.set_page_config(page_title="AI Calorie & Macro Tracker", layout="wide")
st.title("🥗 AI Calorie & Macro Tracker")

# Current date key
today_str = str(date.today())
today_key = f"meals-{today_str}"

# 📅 Allow selecting a date for viewing old logs
st.sidebar.header("📆 Select Date")
selected_date = st.sidebar.date_input("Date", value=date.today())
selected_key = f"meals-{str(selected_date)}"

# 🎯 Set goals
with st.sidebar:
    st.header("🎯 Daily Goals")
    goal_cal = st.number_input("Calories (kcal)", value=2000)
    goal_pro = st.number_input("Protein (g)", value=150)
    goal_carb = st.number_input("Carbs (g)", value=250)
    goal_fat = st.number_input("Fat (g)", value=70)

# Load meals for selected date from browser localStorage (✅ Fixed logic)
load_result = streamlit_js_eval(js_expressions=f"localStorage.getItem('{selected_key}')", key=f"load-{selected_key}")
if load_result:
    try:
        meals = json.loads(load_result)
    except json.JSONDecodeError:
        meals = []
else:
    meals = []

# 🚀 If selected date is today, allow adding meals
if selected_key == today_key:
    st.subheader("🍽️ Add a Meal")
    meal = st.text_input("What did you eat?", placeholder="e.g., 1 cup oats, 1 banana, peanut butter")

    if st.button("Analyze Meal"):
        if not meal:
            st.warning("Please enter a meal description.")
        else:
            prompt = (
                f"Estimate nutritional content of this meal: '{meal}'. "
                "Respond in JSON with calories, protein_g, carbs_g, fat_g. "
                "Example: {\"calories\": 400, \"protein_g\": 20, \"carbs_g\": 30, \"fat_g\": 10}"
            )

            try:
                response = client.chat.completions.create(
                    model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                    messages=[
                        {"role": "system", "content": "You are a certified nutritionist."},
                        {"role": "user", "content": prompt}
                    ]
                )
                nutrition = json.loads(response.choices[0].message.content.strip())

                meals.append({
                    "Meal": meal,
                    "Calories": nutrition.get("calories", 0),
                    "Protein (g)": nutrition.get("protein_g", 0),
                    "Carbs (g)": nutrition.get("carbs_g", 0),
                    "Fat (g)": nutrition.get("fat_g", 0)
                })

                meals_json = json.dumps(meals)
                streamlit_js_eval(js_expressions=f"localStorage.setItem('{today_key}', JSON.stringify({meals_json}))")
                st.success("✅ Meal added successfully.")
            except Exception as e:
                st.error(f"⚠️ Error: {e}")

# 📋 Display meals for selected date
if meals:
    df = pd.DataFrame(meals)
    st.subheader(f"📝 Meals on {selected_date.strftime('%B %d, %Y')}")
    st.dataframe(df, use_container_width=True)

    # 📊 Summary
    totals = df[["Calories", "Protein (g)", "Carbs (g)", "Fat (g)"]].sum()

    def format_remaining(value, goal, unit):
        diff = goal - value
        if diff >= 0:
            return f"{diff:.0f} {unit} remaining ✅"
        else:
            return f"{abs(diff):.0f} {unit} over ⚠️"

    st.markdown("### 📉 Daily Progress")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Calories", f"{int(totals['Calories'])} kcal", format_remaining(totals['Calories'], goal_cal, 'kcal'))
    col2.metric("Protein", f"{totals['Protein (g)']:.1f} g", format_remaining(totals['Protein (g)'], goal_pro, 'g'))
    col3.metric("Carbs", f"{totals['Carbs (g)']:.1f} g", format_remaining(totals['Carbs (g)'], goal_carb, 'g'))
    col4.metric("Fat", f"{totals['Fat (g)']:.1f} g", format_remaining(totals['Fat (g)'], goal_fat, 'g'))

    with st.expander("📊 Show Progress Bars"):
        st.progress(min(totals["Calories"] / goal_cal, 1.0), text="Calories")
        st.progress(min(totals["Protein (g)"] / goal_pro, 1.0), text="Protein")
        st.progress(min(totals["Carbs (g)"] / goal_carb, 1.0), text="Carbs")
        st.progress(min(totals["Fat (g)"] / goal_fat, 1.0), text="Fat")

    # 📈 Bar Chart - Calories per meal
    st.markdown("### 📈 Calories per Meal")
    fig_bar = px.bar(df, x="Meal", y="Calories", text="Calories", color="Calories", color_continuous_scale="YlGnBu")
    fig_bar.update_layout(xaxis_title="", yaxis_title="Calories", height=400)
    st.plotly_chart(fig_bar, use_container_width=True)

    # 🥧 Pie Chart - Macro Breakdown
    st.markdown("### 🥧 Macro Breakdown")
    pie_data = {
        "Macro": ["Protein", "Carbs", "Fat"],
        "Grams": [totals["Protein (g)"], totals["Carbs (g)"], totals["Fat (g)"]]
    }
    fig_pie = px.pie(pie_data, values="Grams", names="Macro", color_discrete_sequence=px.colors.sequential.RdBu)
    st.plotly_chart(fig_pie, use_container_width=True)

    # 🗑️ Clear meals if viewing today
    if selected_key == today_key and st.button("🗑️ Clear Today's Meals"):
        meals = []
        streamlit_js_eval(js_expressions=f"localStorage.setItem('{today_key}', JSON.stringify([]))")
        st.success("Cleared today's meals.")

else:
    st.info(f"No meals logged for {selected_date.strftime('%B %d, %Y')}.")
