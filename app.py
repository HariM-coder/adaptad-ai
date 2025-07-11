import streamlit as st
import boto3
import json
import base64
from io import BytesIO
from PIL import Image
import requests
import os
from datetime import datetime
import time

# Configure Streamlit page
st.set_page_config(
    page_title="AdaptAd AI - Multi-Audience Ad Generator",
    page_icon="🎯",
    layout="wide"
)

# AWS Configuration
@st.cache_resource
def init_aws_clients():
    """Initialize AWS clients"""
    session = boto3.Session(
        aws_access_key_id=st.secrets["aws"]["access_key_id"],
        aws_secret_access_key=st.secrets["aws"]["secret_access_key"],
        region_name=st.secrets["aws"]["region"]
    )
    
    bedrock = session.client('bedrock-runtime')
    s3 = session.client('s3')
    
    return bedrock, s3

def generate_ad_copy(bedrock_client, product_info, audience_profile, trending_topic=""):
    """Generate ad copy using Llama via Bedrock"""
    
    prompt = f"""
    Create a compelling advertisement copy for the following:
    
    Product/Service: {product_info['name']}
    Description: {product_info['description']}
    Key Features: {product_info['features']}
    Target Action: {product_info['action']}
    
    Target Audience: {audience_profile['name']}
    Audience Interests: {audience_profile['interests']}
    Preferred Tone: {audience_profile['tone']}
    
    {f"Current Trending Topic to incorporate: {trending_topic}" if trending_topic else ""}
    
    Generate a concise, engaging ad copy (max 100 words) that speaks directly to this audience.
    Include a strong call-to-action and incorporate audience-specific language and references.
    
    Return only the ad copy without any additional formatting or explanations.
    """
    
    try:
        body = {
            "prompt": prompt,
            "max_gen_len": 200,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        response = bedrock_client.invoke_model(
            modelId="meta.llama3-70b-instruct-v1:0",
            body=json.dumps(body)
        )
        
        result = json.loads(response.get('body').read())
        return result['generation']
        
    except Exception as e:
        st.error(f"Error generating ad copy: {str(e)}")
        return "Error generating ad copy. Please try again."

def generate_image(bedrock_client, product_info, audience_profile, ad_copy):
    """Generate image using Stable Diffusion via Bedrock"""
    
    # Create a detailed prompt for image generation
    style_mapping = {
        "Cinema Enthusiasts": "cinematic, movie poster style, dramatic lighting, professional photography",
        "Sports Fans": "dynamic action shot, energetic, bold colors, athletic aesthetic",
        "Political Enthusiasts": "authoritative, professional, patriotic colors, clean design",
        "Cartoon Lovers": "vibrant cartoon illustration, playful, colorful, animated style",
        "Tech Enthusiasts": "modern, sleek, futuristic, minimalist design",
        "Food Lovers": "appetizing, warm lighting, professional food photography"
    }
    
    style = style_mapping.get(audience_profile['name'], "modern, professional, clean design")
    
    prompt = f"""
    Create a high-quality advertisement image for {product_info['name']}.
    Product: {product_info['description']}
    Style: {style}
    Setting: Advertisement layout suitable for social media or billboard
    Include space for text overlay
    High resolution, professional quality
    No text or words in the image
    """
    
    try:
        body = {
            "textToImageParams": {
            "text": prompt
        },
        "taskType": "TEXT_IMAGE",
        "imageGenerationConfig": {
            "cfgScale": 7.0,
            "seed": int(time.time()) % 1000000,
            "quality": "standard",
            "width": 1024,
            "height": 1024,
            "numberOfImages": 1
        }
        }
        
        response = bedrock_client.invoke_model(
            modelId="amazon.titan-image-generator-v1",
            body=json.dumps(body)
        )
        
        result = json.loads(response['body'].read())
        
        # Decode base64 image
        image_data = result['images'][0]
        image_bytes = base64.b64decode(image_data)
        return Image.open(BytesIO(image_bytes))
    
    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        return None

def get_trending_topics():
    """Simulate trending topics for different audiences"""
    # In a real implementation, this would fetch from news APIs, social media APIs, etc.
    trending_topics = {
        "Cinema Enthusiasts": "New Marvel movie announcement breaking box office records",
        "Sports Fans": "Championship finals creating historic moments",
        "Political Enthusiasts": "Latest policy changes affecting businesses",
        "Cartoon Lovers": "New animated series becoming viral sensation",
        "Tech Enthusiasts": "Revolutionary AI breakthrough changing industries",
        "Food Lovers": "Celebrity chef's new restaurant opening nationwide"
    }
    return trending_topics

def main():
    st.title("🎯 AdaptAd AI - Multi-Audience Ad Generator")
    st.markdown("Generate personalized advertisements for different audience segments using AWS Bedrock AI")
    
    # Initialize AWS clients
    try:
        bedrock_client, s3_client = init_aws_clients()
    except Exception as e:
        st.error("Failed to initialize AWS clients. Please check your credentials.")
        st.stop()
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Product/Service Information
        st.subheader("Product/Service Details")
        product_name = st.text_input("Product/Service Name", "EcoSmart Water Bottle")
        product_description = st.text_area("Description", "Sustainable, temperature-controlled smart water bottle with hydration tracking")
        product_features = st.text_area("Key Features", "• 24-hour temperature control\n• Hydration tracking app\n• Eco-friendly materials\n• Leak-proof design")
        target_action = st.text_input("Target Action", "Visit our website and order now")
        
        # Audience Selection
        st.subheader("Target Audiences")
        audience_profiles = {
            "Cinema Enthusiasts": {
                "name": "Cinema Enthusiasts",
                "interests": "Movies, storytelling, visual arts, entertainment",
                "tone": "dramatic, narrative-driven"
            },
            "Sports Fans": {
                "name": "Sports Fans", 
                "interests": "Athletics, competition, fitness, team spirit",
                "tone": "energetic, motivational"
            },
            "Political Enthusiasts": {
                "name": "Political Enthusiasts",
                "interests": "Current events, policy, civic engagement",
                "tone": "authoritative, informative"
            },
            "Cartoon Lovers": {
                "name": "Cartoon Lovers",
                "interests": "Animation, humor, creativity, fun",
                "tone": "playful, whimsical"
            },
            "Tech Enthusiasts": {
                "name": "Tech Enthusiasts",
                "interests": "Innovation, gadgets, efficiency, future trends",
                "tone": "informative, cutting-edge"
            },
            "Food Lovers": {
                "name": "Food Lovers",
                "interests": "Culinary arts, health, lifestyle, experiences",
                "tone": "appetizing, lifestyle-focused"
            }
        }
        
        selected_audiences = st.multiselect(
            "Select Target Audiences",
            options=list(audience_profiles.keys()),
            default=["Cinema Enthusiasts", "Sports Fans", "Tech Enthusiasts"]
        )
        
        # Generation Settings
        st.subheader("Generation Settings")
        include_trending = st.checkbox("Include Trending Topics", value=True)
        
        # Generate Button
        generate_button = st.button("🚀 Generate Ads", type="primary")
    
    # Main content area
    if generate_button and selected_audiences:
        product_info = {
            "name": product_name,
            "description": product_description,
            "features": product_features,
            "action": target_action
        }
        
        # Get trending topics
        trending_topics = get_trending_topics() if include_trending else {}
        
        st.header("📊 Generated Advertisement Campaigns")
        
        # Generate ads for each selected audience
        for audience_name in selected_audiences:
            audience_profile = audience_profiles[audience_name]
            trending_topic = trending_topics.get(audience_name, "")
            
            with st.expander(f"🎯 {audience_name} Campaign", expanded=True):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader("Ad Copy")
                    with st.spinner(f"Generating ad copy for {audience_name}..."):
                        ad_copy = generate_ad_copy(
                            bedrock_client, 
                            product_info, 
                            audience_profile, 
                            trending_topic
                        )
                    
                    st.write(ad_copy)
                    
                    if trending_topic:
                        st.info(f"📈 Trending Topic: {trending_topic}")
                    
                    # Audience insights
                    st.subheader("Audience Insights")
                    st.write(f"**Interests:** {audience_profile['interests']}")
                    st.write(f"**Tone:** {audience_profile['tone']}")
                
                with col2:
                    st.subheader("Generated Visual")
                    with st.spinner(f"Generating image for {audience_name}..."):
                        generated_image = generate_image(
                            bedrock_client, 
                            product_info, 
                            audience_profile, 
                            ad_copy
                        )
                    
                    if generated_image:
                        st.image(generated_image, caption=f"Ad Visual for {audience_name}")
                        
                        # Download button
                        img_buffer = BytesIO()
                        generated_image.save(img_buffer, format='PNG')
                        img_buffer.seek(0)
                        
                        st.download_button(
                            label="📥 Download Image",
                            data=img_buffer,
                            file_name=f"ad_{audience_name.lower().replace(' ', '_')}.png",
                            mime="image/png"
                        )
                    else:
                        st.error("Failed to generate image")
                
                st.divider()
    
    elif generate_button and not selected_audiences:
        st.warning("Please select at least one target audience to generate ads.")
    
    # Footer
    st.markdown("---")
    st.markdown("Built with ❤️ using AWS Bedrock, Streamlit, and Claude AI")

if __name__ == "__main__":
    main()
