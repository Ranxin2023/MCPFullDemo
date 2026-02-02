# from dotenv import load_dotenv
# from pathlib import Path
# import anthropic
# import json
# import os
# env_path = Path(__file__).resolve().parent.parent / ".env"
# load_dotenv(env_path)

# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# if not ANTHROPIC_API_KEY:
#     raise RuntimeError(f"ANTHROPIC_API_KEY not found. Loaded env from: {env_path}")
# client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# # Test 1: Basic API call (should work)
# try:
#     response = client.messages.create(
#         model="claude-sonnet-4-5-20250929",
#         max_tokens=1024,
#         messages=[{"role": "user", "content": "Hello"}]
#     )
#     print("✓ Basic API works")
# except Exception as e:
#     print(f"✗ Basic API failed: {e}")

# # Test 2: Code execution only
# try:
#     response = client.beta.messages.create(
#         model="claude-sonnet-4-5-20250929",
#         max_tokens=1024,
#         betas=["code-execution-2025-08-25"],
#         messages=[{"role": "user", "content": "Calculate 2+2"}],
#         tools=[{"type": "code_execution_20250825", "name": "code_execution"}]
#     )
#     print("✓ Code execution works")
# except Exception as e:
#     print(f"✗ Code execution failed: {e}")

# # Test 3: Skills API without code execution
# try:
#     response = client.beta.messages.create(
#         model="claude-sonnet-4-5-20250929",
#         max_tokens=1024,
#         betas=["skills-2025-10-02", "files-api-2025-04-14"],
#         container=json.dumps({  # Convert dict to JSON string
#             "skills": [
#                 {
#                     "type": "anthropic",
#                     "skill_id": "pptx",
#                     "version": "latest"
#                 }
#             ]
#         }),
#         messages=[{"role": "user", "content": "Hello"}]
#     )
#     print("✓ Skills API works")
# except Exception as e:
#     print(f"✗ Skills API failed: {e}")

"""
PowerPoint Presentation Creator using Anthropic Claude API

This script demonstrates multiple approaches to create PowerPoint presentations:
1. Using Skills API (requires beta access)
2. Using Code Execution directly (fallback method)
3. Diagnostic tests to check API access

Requirements:
- anthropic Python SDK: pip install anthropic
- python-dotenv (optional): pip install python-dotenv
- Set ANTHROPIC_API_KEY environment variable
"""

import anthropic
import os
import json
from pathlib import Path

# Optional: Load API key from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, will use environment variable directly


def check_api_access():
    """Test basic API access and beta features"""
    print("=" * 60)
    print("TESTING API ACCESS")
    print("=" * 60)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("✗ ANTHROPIC_API_KEY not found in environment variables")
        print("  Please set it using: export ANTHROPIC_API_KEY='your-key-here'")
        return None
    
    print(f"✓ API key found (ends with: ...{api_key[-4:]})")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Test 1: Basic API
    print("\n1. Testing basic API access...")
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=100,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print("   ✓ Basic API works")
    except Exception as e:
        print(f"   ✗ Basic API failed: {e}")
        return None
    
    # Test 2: Code Execution
    print("\n2. Testing code execution...")
    try:
        response = client.beta.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            betas=["code-execution-2025-08-25"],
            messages=[{"role": "user", "content": "Calculate 2+2 using Python"}],
            tools=[{"type": "code_execution_20250825", "name": "code_execution"}]
        )
        print(f"   ✓ Code execution works with response: \n{response}")
    except Exception as e:
        print(f"   ✗ Code execution failed: {e}")
    
    # Test 3: Skills API List
    print("\n3. Testing Skills API access...")
    try:
        skills = client.beta.skills.list(
            source="anthropic",
            betas=["skills-2025-10-02"]
        )
        print("   ✓ Skills API access granted!")
        print(f"   Available skills: {len(skills.data)}")
        for skill in skills.data:
            print(f"     - {skill.id}: {skill.display_title}")
        return client, True
    except anthropic.PermissionDeniedError:
        print("   ✗ Skills API access denied (beta not enabled for your account)")
        return client, False
    except Exception as e:
        print(f"   ✗ Skills API error: {type(e).__name__}: {e}")
        return client, False


def create_presentation_with_skills(client, topic="renewable energy", num_slides=5):
    """
    Create presentation using Skills API (requires beta access)
    """
    print("\n" + "=" * 60)
    print(f"CREATING PRESENTATION WITH SKILLS API")
    print("=" * 60)
    
    try:
        response = client.beta.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            betas=["code-execution-2025-08-25", "skills-2025-10-02"],
            container={
                "skills": [
                    {
                        "type": "anthropic",
                        "skill_id": "pptx",
                        "version": "latest"
                    }
                ]
            },
            messages=[{
                "role": "user",
                "content": f"Create a professional presentation about {topic} with {num_slides} slides"
            }],
            tools=[{
                "type": "code_execution_20250825",
                "name": "code_execution"
            }]
        )
        
        print("\n✓ Presentation created successfully!")
        print("\nResponse content:")
        for i, block in enumerate(response.content):
            print(f"\nBlock {i+1} (type: {block.type}):")
            if hasattr(block, 'text'):
                print(f"  Text: {block.text[:200]}...")
            if hasattr(block, 'file_id'):
                print(f"  File ID: {block.file_id}")
                print(f"  File name: {block.file.name if hasattr(block, 'file') else 'N/A'}")
        
        return response
        
    except anthropic.BadRequestError as e:
        print(f"\n✗ Bad Request Error:")
        print(f"  {e}")
        if hasattr(e, 'body'):
            print(f"  Details: {e.body}")
        return None
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}")
        print(f"  {e}")
        return None


def create_presentation_with_code_execution(client, topic="renewable energy", num_slides=5):
    """
    Create presentation using Code Execution directly (no Skills API needed)
    This is the fallback method that works without Skills API beta access
    """
    print("\n" + "=" * 60)
    print(f"CREATING PRESENTATION WITH CODE EXECUTION")
    print("=" * 60)
    
    prompt = f"""Create a PowerPoint presentation about {topic} with {num_slides} slides.

Use the python-pptx library to create a professional presentation. Include:
1. A title slide with the topic
2. Content slides with relevant information
3. Professional formatting with appropriate fonts and layouts
4. A conclusion slide

Install python-pptx if needed using pip, then create and save the presentation as 'presentation.pptx'.
After creating the file, show me the file path."""
    
    try:
        response = client.beta.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            betas=["code-execution-2025-08-25"],
            messages=[{
                "role": "user",
                "content": prompt
            }],
            tools=[{
                "type": "code_execution_20250825",
                "name": "code_execution"
            }]
        )
        
        print("\n✓ Presentation created successfully!")
        print("\nResponse content:")
        for i, block in enumerate(response.content):
            print(f"\nBlock {i+1} (type: {block.type}):")
            if hasattr(block, 'text'):
                print(f"  {block.text}")
            if block.type == "tool_use":
                print(f"  Tool: {block.name}")
                if hasattr(block, 'input'):
                    code = block.input.get('code', '')
                    print(f"  Code preview: {code[:200]}...")
        
        return response
        
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}")
        print(f"  {e}")
        return None


def download_file_from_response(client, response):
    """
    Download files from the API response
    Requires files-api-2025-04-14 beta
    """
    print("\n" + "=" * 60)
    print("DOWNLOADING FILES")
    print("=" * 60)
    
    file_ids = []
    for block in response.content:
        if hasattr(block, 'file_id'):
            file_ids.append(block.file_id)
    
    if not file_ids:
        print("No files found in response")
        return
    
    try:
        for file_id in file_ids:
            print(f"\nDownloading file: {file_id}")
            
            # Get file metadata
            file_info = client.beta.files.retrieve(
                file_id=file_id,
                betas=["files-api-2025-04-14"]
            )
            print(f"  File name: {file_info.name}")
            print(f"  File size: {file_info.size} bytes")
            
            # Download file content
            file_content = client.beta.files.content(
                file_id=file_id,
                betas=["files-api-2025-04-14"]
            )
            
            # Save file
            output_path = Path(file_info.name)
            with open(output_path, 'wb') as f:
                f.write(file_content.content)
            
            print(f"  ✓ Saved to: {output_path.absolute()}")
            
    except Exception as e:
        print(f"\n✗ Download error: {type(e).__name__}")
        print(f"  {e}")


def main():
    """Main function to run the presentation creator"""
    
    # Step 1: Check API access
    result = check_api_access()
    if result is None:
        print("\n❌ API access check failed. Please fix the issues above.")
        return
    
    client, has_skills_access = result
    
    # Step 2: Get user input
    print("\n" + "=" * 60)
    print("PRESENTATION CONFIGURATION")
    print("=" * 60)
    
    topic = input("\nEnter presentation topic (default: renewable energy): ").strip()
    if not topic:
        topic = "renewable energy"
    
    num_slides_input = input("Enter number of slides (default: 5): ").strip()
    try:
        num_slides = int(num_slides_input) if num_slides_input else 5
    except ValueError:
        print("Invalid number, using default: 5")
        num_slides = 5
    
    # Step 3: Create presentation
    if has_skills_access:
        print("\n📊 Using Skills API (recommended)")
        use_skills = input("Use Skills API? (Y/n): ").strip().lower()
        if use_skills != 'n':
            response = create_presentation_with_skills(client, topic, num_slides)
            if response:
                # Try to download files
                download_file_from_response(client, response)
            return
    
    print("\n📊 Using Code Execution (fallback method)")
    response = create_presentation_with_code_execution(client, topic, num_slides)
    
    if response:
        print("\n" + "=" * 60)
        print("✓ COMPLETE!")
        print("=" * 60)
        print("\nNote: With code execution, the file is created in Claude's")
        print("execution environment. To get the file, you would need to:")
        print("1. Use the Files API to download it, or")
        print("2. Have Claude encode it as base64 and send it back")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     PowerPoint Presentation Creator                     ║
║     Using Anthropic Claude API                          ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {type(e).__name__}")
        print(f"   {e}")