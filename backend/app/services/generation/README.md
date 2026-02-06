# Generative AI Modules


## Image Generation Module
An interface for generating 2D images using various AI services, abstracting the complexity of different API schemas and providing a unified binary output.

### Structure

| Component | Description |
| :--- | :--- | :--- |
| **Registry** | Central controller that manages service initialization based on available API keys. |
| **Services** | Contains specific class implementations for Imagen, GPT-image, and Nano-Banana. |
| **Fallback** | Includes a MockImageGenerator that returns a placeholder image if no valid API keys are detected. |

### Functions

These functions are managed via the ImageServiceRegistry and the individual service classes.

#### generate(prompt)

    Input: A text description of the image to be created.

    Process: Sends the prompt to the selected AI provider (e.g., OpenAI's DALL-E or Google's Imagen).

    Output: Returns raw bytes of the generated image (standardized to image/png format), allowing for immediate local saving or further processing.

#### get_service(service_name)

    Input: The string name of the desired service (e.g., "GPT-image", "imagen").

    Behavior: Returns the initialized service instance. If a service is requested but its API key is missing from the environment, it returns the Mock Generator to prevent system crashes.



## 3D Generation Module
A high-level interface for transforming 2D images into 3D assets (.glb meshes) using reconstruction models via the Fal.ai platform.

### Structure

| Component | Description |
| :--- | :--- | :--- |
| **Registry** | Handles the injection of the FAL_KEY into the environment and initializes the 3D generation backend. |
| **Services** | Implements dedicated classes for the Trellis and Hunyuan3D models. |
| **Utility** | Provides helper methods for converting image bytes to Data URIs and downloading final model files from remote URLs. |
| **Fallback** | Includes a MockGenerator that returns a placeholder .glb if no valid API key is detected. |


### Functions

These functions are located in the Base3DGenerator subclasses and are used to drive the 3D creation pipeline.

#### generate(image)

    Input: A list of image bytes (usually the output from the Image Generation module).

    Process:

        Converts the raw bytes into a Base64 Data URI.

        Submits the request to Fal.ai and waits for the result.

        Robustly parses the result for model_mesh or model_glb download URLs.

    Output: Returns the binary content of the generated .glb file.

#### get_service(service_name)

    Input: The string name of the desired service (e.g., "trellis", "hunyuan").

    Behavior: Returns the requested service instance or Trellis as a default. If no FALAI_KEY is provided, it returns the Mock3DGenerator to prevent system crashes.

