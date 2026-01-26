import requests

# Your local Flask server address
URL = "http://127.0.0.1:5055/api/generate-image"

# The payload matching your ImageServiceRegistry logic
payload = {
    "prompt": "An oak dining chair with ornate carvings and red cushion",
    "service": "imagen"
}

try:
    print(f"Sending request to {URL}...")
    response = requests.post(URL, json=payload)

    if response.status_code == 200:
        # Save the binary content received from send_file()
        with open("image.png", "wb") as f:
            f.write(response.content)
        print("Success! Image saved as 'image.png'")
    else:
        print(f"Failed with status code: {response.status_code}")
        print(f"Error detail: {response.text}")

except Exception as e:
    print(f"An error occurred: {e}")