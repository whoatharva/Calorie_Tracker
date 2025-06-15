# app.py

import streamlit as st
import openai
import os
import re

# Try to load secrets from Streamlit or fallback to .env
from dotenv import load_dotenv
load_dotenv()

def get_secret(key, default=""):
    return st.secrets.get(key) or os.getenv(key, default)

# Azure OpenAI Configuration
openai.api_type = "azure"
openai.api_key = get_secret("AZURE_OPENAI_API_KEY")
openai.api_base = get_secret("AZURE_OPENAI_ENDPOINT")
openai.api_version = get_secret("AZURE_OPENAI_API_VERSION")
deployment_id = get_secret("AZURE_OPENAI_DEPLOYMENT")

# App config
st.set_page_config(page_title="AI Calorie Tracker", layout="centered")
st.title("🥗 AI Calorie Tracker")

# Input field
food_description = st.text_input("Describe your food (e.g. '2 slices of pizza')")

# Analyze button
if st.button("Analyze"):
    if not food_description:
        st.warning("Please enter a food description.")
    else:
        with st.spinner("Analyzing with Azure OpenAI..."):
            try:
                response = openai.ChatCompletion.create(
                    deployment_id=deployment_id,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a nutrition assistant that returns calorie, protein, carbs, and fat information for foods."
                        },
                        {
                            "role": "user",
                            "content": f"Give nutritional info for: {food_description}"
                        }
                    ],
                    temperature=0.2
                )

                content = response["choices"][0]["message"]["content"]
                st.subheader("🔍 Nutrition Info (AI Response)")
                st.text(content)

                # Extract numerical values
                def extract(pattern, text):
                    match = re.search(pattern, text, re.I)
                    return float(match.group(1)) if match else None

                calories = extract(r"calories\s*[:\-]?\s*(\d+)", content)
                protein = extract(r"protein\s*[:\-]?\s*(\d+\.?\d*)", content)
                carbs = extract(r"carbs\s*[:\-]?\s*(\d+\.?\d*)", content)
                fat = extract(r"fat\s*[:\-]?\s*(\d+\.?\d*)", content)

                # Show metrics if found
                if all(v is not None for v in [calories, protein, carbs, fat]):
                    st.subheader("📊 Extracted Nutrients")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Calories", f"{int(calories)} kcal")
                    col2.metric("Protein", f"{protein} g")
                    col3.metric("Carbs", f"{carbs} g")
                    col4.metric("Fat", f"{fat} g")
                else:
                    st.warning("⚠️ AI response could not be fully parsed.")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
