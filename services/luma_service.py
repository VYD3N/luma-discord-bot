import requests
import os
from dotenv import load_dotenv
import json
import asyncio
import tempfile
from pathlib import Path
import base64
import time
import mimetypes
from PIL import Image
import io

class LumaService:
    def __init__(self):
        load_dotenv()
        self.base_url = "https://api.lumalabs.ai/dream-machine/v1"
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {os.getenv('LUMA_API_KEY')}"
        }
        self.imgbb_key = os.getenv('IMGBB_API_KEY')  # Get ImgBB key from .env
        
    async def upload_to_imgbb(self, image_data):
        """Upload image to ImgBB"""
        try:
            url = "https://api.imgbb.com/1/upload"
            payload = {
                "key": self.imgbb_key,  # Use key from .env
                "image": base64.b64encode(image_data).decode('utf-8')
            }
            
            response = requests.post(url, data=payload)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "url": data["data"]["url"]
                }
            else:
                return {
                    "success": False,
                    "error": f"ImgBB API Error: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to upload to ImgBB: {str(e)}"
            }

    async def download_and_upload_image(self, image_url: str) -> dict:
        """Download image from Discord and upload to ImgBB"""
        try:
            # Download image
            response = requests.get(image_url)
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": "Failed to download image"
                }

            # Upload to ImgBB
            result = await self.upload_to_imgbb(response.content)
            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to process image: {str(e)}"
            }

    async def create_capture(self, capture_type: str, prompt: str, aspect_ratio: str = "16:9", model: str = "photon-1"):
        try:
            endpoint = f"{self.base_url}/generations/image"
            payload = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "model": model
            }
            
            response = requests.post(endpoint, json=payload, headers=self.headers)
            data = response.json()
            
            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "id": data.get("id"),
                    "state": data.get("state"),
                    "details": data
                }
                
            return {
                "success": False,
                "error": f"API Error: {response.status_code}",
                "details": data
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

    async def get_capture_status(self, generation_id: str):
        """Get the status of a generation"""
        try:
            endpoint = f"{self.base_url}/generations/{generation_id}"
            
            print(f"\n=== Status Check for {generation_id} ===")
            response = requests.get(endpoint, headers=self.headers)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code}",
                    "details": response.text
                }
                
            data = response.json()
            state = data.get('state', 'unknown')
            failure_reason = data.get('failure_reason')
            
            if state == 'failed':
                print(f"Generation failed. Reason: {failure_reason}")
                return {
                    "success": False,
                    "error": f"Generation failed: {failure_reason}" if failure_reason else "Generation failed",
                    "details": data
                }
            
            return {
                "success": True,
                "status": state,
                "image_url": data.get('assets', {}).get('image'),
                "details": data,
                "progress_update": state in ['queued', 'dreaming']
            }
            
        except Exception as e:
            print(f"Status check error: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get status: {str(e)}"
            }

    async def list_captures(self):
        try:
            endpoint = f"{self.base_url}/generations"
            response = requests.get(endpoint, headers=self.headers)
            return response.json()
        except Exception as e:
            return {"error": f"Failed to list generations: {str(e)}"}

    async def wait_for_generation(self, generation_id: str, max_attempts: int = 300, delay: int = 2):
        """Wait for generation to complete with timeout (10 minutes max for reference images)"""
        for attempt in range(max_attempts):
            result = await self.get_capture_status(generation_id)
            
            if not result.get("success"):
                if attempt < 5:  # More retries at the start
                    await asyncio.sleep(delay)
                    continue
                return result
                
            state = result.get("status")
            result["elapsed_time"] = attempt * delay
            
            # Return immediately if completed or failed
            if state == "completed" and result.get("image_url"):
                return result
            elif state == "failed":
                return {
                    "success": False,
                    "error": "Generation failed",
                    "details": result.get("details")
                }
            
            # Progress update every 30 seconds
            if attempt > 0 and attempt % 15 == 0:
                result["progress_update"] = True
                return result
                
            # Add small delay between checks
            await asyncio.sleep(delay)
            
        return {
            "success": False,
            "error": "Timeout waiting for generation",
            "elapsed_time": max_attempts * delay
        }

    async def create_capture_with_ref(self, prompt: str, aspect_ratio: str = "16:9", 
                                    model: str = "photon-1", image_refs: list = None):
        try:
            if image_refs and isinstance(image_refs, list):
                new_refs = []
                for ref in image_refs:
                    if 'cdn.discordapp.com' in ref['url'] or 'media.discordapp.net' in ref['url']:
                        # Upload Discord image to ImgBB
                        upload_result = await self.download_and_upload_image(ref['url'])
                        if not upload_result['success']:
                            return upload_result
                        
                        new_refs.append({
                            "url": upload_result['url'],
                            "weight": ref.get('weight', 0.85)
                        })
                    else:
                        new_refs.append(ref)
                        
                image_refs = new_refs

            endpoint = f"{self.base_url}/generations/image"
            payload = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "model": model,
                "image_ref": image_refs
            }
            
            print(f"Sending payload: {json.dumps(payload, indent=2)}")
            response = requests.post(endpoint, json=payload, headers=self.headers)
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    "success": True,
                    "id": data.get("id"),
                    "state": data.get("state"),
                    "details": data
                }
                
            return {
                "success": False,
                "error": f"API Error: {response.status_code}",
                "details": response.text
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

    async def create_capture_with_style(self, prompt: str, aspect_ratio: str = "16:9", 
                                      model: str = "photon-1", style_refs: list = None):
        """Create a generation with style references"""
        try:
            endpoint = f"{self.base_url}/generations/image"
            
            # Debug: Print incoming parameters
            print("\n=== Style Generation Debug ===")
            print(f"Prompt: {prompt}")
            print(f"Aspect Ratio: {aspect_ratio}")
            print(f"Model: {model}")
            print(f"Style Refs: {json.dumps(style_refs, indent=2)}")
            
            # Process Discord URLs if needed
            if style_refs and isinstance(style_refs, list):
                new_refs = []
                for ref in style_refs:
                    url = ref['url']
                    if 'cdn.discordapp.com' in url or 'media.discordapp.net' in url:
                        print(f"Processing Discord URL: {url}")
                        upload_result = await self.download_and_upload_image(url)
                        if not upload_result['success']:
                            print(f"Failed to process URL: {upload_result['error']}")
                            return upload_result
                        new_refs.append({
                            "url": upload_result['url'],
                            "weight": ref['weight']
                        })
                    else:
                        new_refs.append(ref)
                style_refs = new_refs
            
            payload = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "model": model,
                "style_ref": style_refs  # Keep as list, don't extract single item
            }
            
            # Debug: Print final payload
            print("\n=== API Request ===")
            print(f"Endpoint: {endpoint}")
            print(f"Headers: {json.dumps({k:v for k,v in self.headers.items() if k != 'Authorization'}, indent=2)}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(endpoint, json=payload, headers=self.headers)
            
            # Debug: Print response
            print("\n=== API Response ===")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body: {response.text}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    "success": True,
                    "id": data.get("id"),
                    "state": data.get("state"),
                    "details": data
                }
                
            return {
                "success": False,
                "error": f"API Error: {response.status_code}",
                "details": response.text
            }
            
        except Exception as e:
            print(f"\n=== Exception ===")
            print(f"Error: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

    async def create_capture_with_char(self, prompt: str, aspect_ratio: str = "16:9", 
                                     model: str = "photon-1", char_images: list = None):
        """Create a generation with character references"""
        try:
            endpoint = f"{self.base_url}/generations/image"
            
            # Process Discord URLs if needed
            if char_images:
                processed_images = []
                for url in char_images:
                    if 'cdn.discordapp.com' in url or 'media.discordapp.net' in url:
                        print(f"Processing Discord URL: {url}")
                        upload_result = await self.download_and_upload_image(url)
                        if not upload_result['success']:
                            print(f"Failed to process URL: {upload_result['error']}")
                            return upload_result
                        processed_images.append(upload_result['url'])
                    else:
                        processed_images.append(url)
                char_images = processed_images
            
            # Build character reference structure exactly as in API docs
            payload = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "model": model,
                "character_ref": {
                    "identity0": {
                        "images": char_images if char_images else []
                    }
                }
            }
            
            print("\n=== API Request ===")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(endpoint, json=payload, headers=self.headers)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    "success": True,
                    "id": data.get("id"),
                    "state": data.get("state"),
                    "details": data
                }
                
            return {
                "success": False,
                "error": f"API Error: {response.status_code}",
                "details": response.text
            }
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            } 

    async def create_capture_with_mod(self, prompt: str, model: str = "photon-1", 
                                    image_url: str = None, weight: float = 0.85):
        """Create a generation that modifies an existing image"""
        try:
            endpoint = f"{self.base_url}/generations/image"
            
            # Process Discord URL if needed
            if 'cdn.discordapp.com' in image_url or 'media.discordapp.net' in image_url:
                print(f"Processing Discord URL: {image_url}")
                upload_result = await self.download_and_upload_image(image_url)
                if not upload_result['success']:
                    print(f"Failed to process URL: {upload_result['error']}")
                    return upload_result
                image_url = upload_result['url']
            
            # Build modification payload exactly as in API docs
            payload = {
                "prompt": prompt,
                "model": model,
                "modify_image_ref": {
                    "url": image_url,
                    "weight": weight
                }
            }
            
            print("\n=== API Request ===")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(endpoint, json=payload, headers=self.headers)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    "success": True,
                    "id": data.get("id"),
                    "state": data.get("state"),
                    "details": data
                }
                
            return {
                "success": False,
                "error": f"API Error: {response.status_code}",
                "details": response.text
            }
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            } 

    async def create_video(self, prompt: str, aspect_ratio: str = "16:9", loop: bool = False):
        """Create a video generation"""
        try:
            endpoint = f"{self.base_url}/generations"
            
            # Build payload
            payload = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "loop": loop
            }
            
            print("\n=== Video Generation Request ===")
            print(f"Endpoint: {endpoint}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(endpoint, json=payload, headers=self.headers)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    "success": True,
                    "id": data.get("id"),
                    "state": data.get("state"),
                    "details": data
                }
                
            return {
                "success": False,
                "error": f"API Error: {response.status_code}",
                "details": response.text
            }
            
        except Exception as e:
            print(f"Error in create_video: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to create video: {str(e)}"
            }

    async def wait_for_video_generation(self, generation_id: str, max_attempts: int = 600, delay: int = 2):
        """Wait for video generation to complete with timeout (20 minutes max)"""
        for attempt in range(max_attempts):
            result = await self.get_video_status(generation_id)
            
            if not result.get("success"):
                if attempt < 5:  # More retries at the start
                    await asyncio.sleep(delay)
                    continue
                return result
                
            state = result.get("status")
            result["elapsed_time"] = attempt * delay
            
            # Return immediately if completed or failed
            if state == "completed" and result.get("video_url"):
                return result
            elif state == "failed":
                return {
                    "success": False,
                    "error": "Generation failed",
                    "details": result.get("details")
                }
            
            # Progress update every 30 seconds
            if attempt > 0 and attempt % 15 == 0:
                result["progress_update"] = True
                return result
                
            # Add small delay between checks
            await asyncio.sleep(delay)
            
        return {
            "success": False,
            "error": "Timeout waiting for video generation",
            "elapsed_time": max_attempts * delay
        }

    async def get_video_status(self, generation_id: str):
        """Get the status of a video generation"""
        try:
            endpoint = f"{self.base_url}/generations/{generation_id}"
            response = requests.get(endpoint, headers=self.headers)
            
            print(f"\n=== Video Status Check ===")
            print(f"Generation ID: {generation_id}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code}",
                    "details": response.text
                }
                
            data = response.json()
            state = data.get('state', 'unknown')
            
            # For completed state, ensure we have a video URL
            if state == 'completed':
                video_url = data.get('assets', {}).get('video')
                if video_url:
                    return {
                        "success": True,
                        "status": state,
                        "video_url": video_url,
                        "details": data
                    }
            
            # For other states, return status info
            return {
                "success": True,
                "status": state,
                "video_url": None,
                "details": data,
                "progress_update": state in ['queued', 'processing']
            }
            
        except Exception as e:
            print(f"Status check error: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get status: {str(e)}"
            }

    async def create_image_video(
        self, 
        prompt: str, 
        image_url1: str,
        frame_type1: str,
        image_url2: str = None,
        frame_type2: str = None,
        aspect_ratio: str = "16:9",
        loop: bool = False
    ):
        """Create a video generation from one or two images"""
        try:
            endpoint = f"{self.base_url}/generations"
            
            # Process first image if it's from Discord
            if 'cdn.discordapp.com' in image_url1 or 'media.discordapp.net' in image_url1:
                print(f"Processing Discord URL 1: {image_url1}")
                upload_result = await self.download_and_upload_image(image_url1)
                if not upload_result['success']:
                    print(f"Failed to process URL 1: {upload_result['error']}")
                    return upload_result
                image_url1 = upload_result['url']
            
            # Initialize keyframes
            keyframes = {
                frame_type1: {
                    "type": "image",
                    "url": image_url1
                }
            }
            
            # Process second image if provided
            if image_url2 and frame_type2:
                if 'cdn.discordapp.com' in image_url2 or 'media.discordapp.net' in image_url2:
                    print(f"Processing Discord URL 2: {image_url2}")
                    upload_result = await self.download_and_upload_image(image_url2)
                    if not upload_result['success']:
                        print(f"Failed to process URL 2: {upload_result['error']}")
                        return upload_result
                    image_url2 = upload_result['url']
                
                keyframes[frame_type2] = {
                    "type": "image",
                    "url": image_url2
                }
            
            # Build payload
            payload = {
                "prompt": prompt,
                "keyframes": keyframes,
                "aspect_ratio": aspect_ratio,
                "loop": loop
            }
            
            print("\n=== Image-to-Video Generation Request ===")
            print(f"Endpoint: {endpoint}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(endpoint, json=payload, headers=self.headers)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    "success": True,
                    "id": data.get("id"),
                    "state": data.get("state"),
                    "details": data
                }
                
            return {
                "success": False,
                "error": f"API Error: {response.status_code}",
                "details": response.text
            }
            
        except Exception as e:
            print(f"Error in create_image_video: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to create video: {str(e)}"
            }

    async def extend_video(
        self,
        prompt: str,
        mode: str,
        video_id1: str,
        video_id2: str = None,
        image_url: str = None
    ):
        """Extend a video using various modes"""
        try:
            endpoint = f"{self.base_url}/generations"
            
            # Process image URL if provided (for modes that use images)
            if image_url and ('cdn.discordapp.com' in image_url or 'media.discordapp.net' in image_url):
                print(f"Processing Discord URL: {image_url}")
                upload_result = await self.download_and_upload_image(image_url)
                if not upload_result['success']:
                    print(f"Failed to process URL: {upload_result['error']}")
                    return upload_result
                image_url = upload_result['url']
            
            # Initialize keyframes based on mode
            keyframes = {}
            
            if mode == "extend":
                keyframes["frame0"] = {
                    "type": "generation",
                    "id": video_id1
                }
                
            elif mode == "reverse":
                keyframes["frame1"] = {
                    "type": "generation",
                    "id": video_id1
                }
                
            elif mode == "extend_end":
                keyframes["frame0"] = {
                    "type": "generation",
                    "id": video_id1
                }
                keyframes["frame1"] = {
                    "type": "image",
                    "url": image_url
                }
                
            elif mode == "reverse_start":
                keyframes["frame0"] = {
                    "type": "image",
                    "url": image_url
                }
                keyframes["frame1"] = {
                    "type": "generation",
                    "id": video_id1
                }
                
            elif mode == "interpolate":
                keyframes["frame0"] = {
                    "type": "generation",
                    "id": video_id1
                }
                keyframes["frame1"] = {
                    "type": "generation",
                    "id": video_id2
                }
            
            # Build payload
            payload = {
                "prompt": prompt,
                "keyframes": keyframes
            }
            
            print("\n=== Video Extension Request ===")
            print(f"Mode: {mode}")
            print(f"Endpoint: {endpoint}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(endpoint, json=payload, headers=self.headers)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    "success": True,
                    "id": data.get("id"),
                    "state": data.get("state"),
                    "details": data
                }
                
            return {
                "success": False,
                "error": f"API Error: {response.status_code}",
                "details": response.text
            }
            
        except Exception as e:
            print(f"Error in extend_video: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Failed to extend video: {str(e)}"
            }