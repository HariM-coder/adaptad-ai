import json
import boto3
import base64
from io import BytesIO
import time
from datetime import datetime

def lambda_handler(event, context):
    """
    AWS Lambda handler for ad generation
    Handles both text and image generation requests
    """
    
    # Initialize clients
    bedrock = boto3.client('bedrock-runtime')
    s3 = boto3.client('s3')
    
    try:
        # Parse request
        request_type = event.get('request_type', 'text')
        product_info = event.get('product_info', {})
        audience_profile = event.get('audience_profile', {})
        trending_topic = event.get('trending_topic', '')
        
        if request_type == 'text':
            # Generate ad copy
            result = generate_ad_copy(bedrock, product_info, audience_profile, trending_topic)
            
        elif request_type == 'image':
            # Generate image
            ad_copy = event.get('ad_copy', '')
            result = generate_image(bedrock, s3, product_info, audience_profile, ad_copy)
            
        elif request_type == 'trending':
            # Get trending topics
            result = get_trending_topics()
            
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid request type'})
            }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'result': result
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }

def generate_ad_copy(bedrock_client, product_info, audience_profile, trending_topic=""):
    """Generate ad copy using Claude via Bedrock"""
    
    prompt = f"""
    Create a compelling advertisement copy for the following:
    
    Product/Service: {product_info.get('name', 'Product')}
    Description: {product_info.get('description', 'Description')}
    Key Features: {product_info.get('features', 'Features')}
    Target Action: {product_info.get('action', 'Learn more')}
    
    Target Audience: {audience_profile.get('name', 'General')}
    Audience Interests: {audience_profile.get('interests', 'General interests')}
    Preferred Tone: {audience_profile.get('tone', 'Professional')}
    
    {f"Current Trending Topic to incorporate: {trending_topic}" if trending_topic else ""}
    
    Generate a concise, engaging ad copy (max 100 words) that speaks directly to this audience.
    Include a strong call-to-action and incorporate audience-specific language and references.
    
    Return only the ad copy without any additional formatting or explanations.
    """
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 200,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    })
    
    response = bedrock_client.invoke_model(
        body=body,
        modelId="meta.llama3-70b-instruct-v1:0",
        accept="application/json",
        contentType="application/json"
    )
    
    result = json.loads(response.get('body').read())
    return result['content'][0]['text']

def generate_image(bedrock_client, s3_client, product_info, audience_profile, ad_copy):
    """Generate image using Stable Diffusion via Bedrock"""
    
    style_mapping = {
        "Cinema Enthusiasts": "cinematic, movie poster style, dramatic lighting, professional photography",
        "Sports Fans": "dynamic action shot, energetic, bold colors, athletic aesthetic",
        "Political Enthusiasts": "authoritative, professional, patriotic colors, clean design",
        "Cartoon Lovers": "vibrant cartoon illustration, playful, colorful, animated style",
        "Tech Enthusiasts": "modern, sleek, futuristic, minimalist design",
        "Food Lovers": "appetizing, warm lighting, professional food photography"
    }
    
    style = style_mapping.get(audience_profile.get('name', 'General'), "modern, professional, clean design")
    
    prompt = f"""
    Create a high-quality advertisement image for {product_info.get('name', 'product')}.
    Product: {product_info.get('description', 'description')}
    Style: {style}
    Setting: Advertisement layout suitable for social media or billboard
    Include space for text overlay
    High resolution, professional quality
    No text or words in the image
    """
    
    body = json.dumps({
        "text_prompts": [
            {
                "text": prompt,
                "weight": 1.0
            }
        ],
        "cfg_scale": 7,
        "seed": int(time.time()) % 1000000,
        "steps": 30,
        "width": 1024,
        "height": 1024
    })
    
    response = bedrock_client.invoke_model(
        body=body,
        modelId="amazon.titan-image-generator-v1",
        accept="application/json",
        contentType="application/json"
    )
    
    result = json.loads(response.get('body').read())
    
    # Save image to S3
    image_data = base64.b64decode(result['artifacts'][0]['base64'])
    bucket_name = 'adaptad-generated-images'  # Replace with your bucket name
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audience_name = audience_profile.get('name', 'general').lower().replace(' ', '_')
    key = f"generated_ads/{audience_name}_{timestamp}.png"
    
    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=image_data,
        ContentType='image/png'
    )
    
    # Generate presigned URL for download
    presigned_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': key},
        ExpiresIn=3600  # 1 hour
    )
    
    return {
        'image_url': presigned_url,
        's3_key': key,
        'bucket': bucket_name
    }

def get_trending_topics():
    """Get trending topics for different audiences"""
    # In production, this would call external APIs
    trending_topics = {
        "Cinema Enthusiasts": "New Marvel movie announcement breaking box office records",
        "Sports Fans": "Championship finals creating historic moments",
        "Political Enthusiasts": "Latest policy changes affecting businesses",
        "Cartoon Lovers": "New animated series becoming viral sensation",
        "Tech Enthusiasts": "Revolutionary AI breakthrough changing industries",
        "Food Lovers": "Celebrity chef's new restaurant opening nationwide"
    }
    return trending_topics
