import zipfile
import base64
import json
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, request, send_file, jsonify, current_app
from .services.generation.threeD_generator import split_orthographic_sheet
from io import BytesIO

from .services.generation.prompt_generator import SYSTEM_INSTRUCTION

api_bp = Blueprint('api', __name__)

DEFAULT_VIEWPOINTS = ["front", "back", "left", "right"]


@api_bp.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}, 200)


@api_bp.route('/generate-image', methods=['POST'])
def generate_image():
    """Generate multi-view 2D images from an optimized prompt using the selected image service."""
    data = request.get_json()
    optimized_prompt: str = data.get('optimized_prompt')
    service_choice: str = data.get('service')
    viewpoints = data.get('viewpoints', DEFAULT_VIEWPOINTS)

    if not optimized_prompt:
        return {'error': 'No prompt provided'}, 400

    registry = current_app.extensions['image_registry']
    service = registry.get_service(service_choice)

    if not service:
        return {'error': f'Service {service_choice} not supported'}, 400

    viewpoint_images = {}
    failed_viewpoints = []

    # Step 1: Generate the front view first
    front_image_bytes = None
    front_prompt = f"{optimized_prompt}, front view, single view only"
    try:
        images = service.generate(front_prompt, num_images=1)
        if images and len(images) > 0:
            front_image_bytes = images[0]
            b64_str = base64.b64encode(front_image_bytes).decode('utf-8')
            viewpoint_images["front"] = f"data:image/png;base64,{b64_str}"
        else:
            viewpoint_images["front"] = None
            failed_viewpoints.append("front")
    except Exception as e:
        print(f"Image generation failed for front view: {e}")
        viewpoint_images["front"] = None
        failed_viewpoints.append("front")

    # Step 2: Generate remaining views in parallel, using front image as reference
    remaining_viewpoints = [vp for vp in viewpoints if vp != "front"]
    ref_generator = registry.get_reference_generator()

    def generate_viewpoint(viewpoint):
        viewpoint_prompt = f"{optimized_prompt}, {viewpoint} view, single view only. Use the provided front view as reference for consistency."
        try:
            if front_image_bytes is not None and service.supports_reference:
                # Use selected model's own reference-based generation
                images = service.generate_with_reference(viewpoint_prompt, front_image_bytes)
            elif front_image_bytes is not None and ref_generator is not None:
                # Fallback to Flux 2 Pro Edit for models that don't support reference (e.g. Imagen)
                images = ref_generator.generate_with_reference(viewpoint_prompt, front_image_bytes)
            else:
                images = service.generate(viewpoint_prompt, num_images=1)
            if images and len(images) > 0:
                b64_str = base64.b64encode(images[0]).decode('utf-8')
                return viewpoint, f"data:image/png;base64,{b64_str}"
            return viewpoint, None
        except Exception as e:
            print(f"Image generation failed for {viewpoint} view: {e}")
            return viewpoint, None

    with ThreadPoolExecutor(max_workers=3) as executor:
        results = executor.map(generate_viewpoint, remaining_viewpoints)

    for viewpoint, image_data in results:
        viewpoint_images[viewpoint] = image_data
        if image_data is None:
            failed_viewpoints.append(viewpoint)

    # If all viewpoints failed, return error
    if len(failed_viewpoints) == len(viewpoints):
        return {'error': 'Image generation failed for all viewpoints'}, 500

    response = {
        'status': 'success',
        'viewpoint_images': viewpoint_images,
        'viewpoints': viewpoints,
        'count': len(viewpoints) - len(failed_viewpoints)
    }

    if failed_viewpoints:
        response['failed_viewpoints'] = failed_viewpoints

    return jsonify(response), 200


@api_bp.route('/regenerate-view', methods=['POST'])
def regenerate_view():
    """Regenerate a single viewpoint image, optionally refining the prompt with user feedback."""
    data = request.get_json()
    optimized_prompt: str = data.get('optimized_prompt')
    viewpoint: str = data.get('viewpoint')
    service_choice: str = data.get('service')
    reference_image = data.get('reference_image')
    user_feedback = data.get('user_feedback')
    prompt_service_choice: str = data.get('prompt_service', 'gemini-3-flash-preview')

    context_images = data.get('context_images', [])

    if not optimized_prompt or not viewpoint:
        return {'error': 'Prompt and viewpoint are required'}, 400

    image_registry = current_app.extensions['image_registry']
    service = image_registry.get_service(service_choice)

    if not service:
        return {'error': f'Image service {service_choice} not supported'}, 400

    # Step 1: Refine prompt if user provided feedback (with visual context if available)
    prompt_to_use = optimized_prompt
    if user_feedback and user_feedback.strip():
        prompt_registry = current_app.extensions['prompt_registry']
        prompt_service = prompt_registry.get_service(prompt_service_choice)
        refined = prompt_service.refine(optimized_prompt, viewpoint, user_feedback, context_images or None)
        if refined:
            prompt_to_use = refined

    # Step 2: Build the viewpoint-specific prompt
    if viewpoint == "front":
        generation_prompt = f"{prompt_to_use}, front view, single view only"
    else:
        generation_prompt = f"{prompt_to_use}, {viewpoint} view, single view only. Use the provided front view as reference for consistency."

    # Step 3: Generate the image
    try:
        if viewpoint != "front" and reference_image and service.supports_reference:
            # Decode the reference image
            ref_data = reference_image
            if ',' in ref_data:
                ref_data = ref_data.split(',')[1]
            ref_bytes = base64.b64decode(ref_data)
            images = service.generate_with_reference(generation_prompt, ref_bytes)
        else:
            images = service.generate(generation_prompt, num_images=1)

        if images and len(images) > 0:
            b64_str = base64.b64encode(images[0]).decode('utf-8')
            return jsonify({
                'status': 'success',
                'viewpoint': viewpoint,
                'image': f"data:image/png;base64,{b64_str}"
            }), 200
        else:
            return {'error': f'Failed to regenerate {viewpoint} view'}, 500

    except Exception as e:
        print(f"Regeneration failed for {viewpoint} view: {e}")
        return {'error': f'Regeneration failed: {str(e)}'}, 500


@api_bp.route('/optimize-prompt', methods=['POST'])
def optimize_prompt():
    """Run an LLM prompt optimizer to produce a detailed image generation prompt."""
    data = request.get_json()
    prompt: str = data.get('prompt')
    service_choice: str = data.get('service', 'gemini-3-flash-preview')

    if not prompt:
        return {'error': 'No prompt provided'}, 400

    registry = current_app.extensions['prompt_registry']
    service = registry.get_service(service_choice)

    if not service:
        return {'error': f'Service {service_choice} not supported'}, 400

    optimized_prompt: str | None = service.generate(prompt)
    if optimized_prompt:
        return {
            'success': True,
            'original_prompt': prompt,
            'optimized_prompt': optimized_prompt,
            'service': service_choice
        }, 200

    return {'error': 'Prompt optimization failed'}, 500


@api_bp.route('/generate-3d-model', methods=['POST'])
def generate_3d_model():
    """
    Convert one or more base64-encoded images into a GLB 3D model.

    Expects JSON: { "images": ["data:image/png;base64,..."], "service": "trellis" }

    A single image is split into 4 orthographic views before being passed to the
    3D generator. Multiple images are passed through directly.
    """
    data = request.get_json()
    images_data: list[str] = data.get('images', [])
    service_choice: str = data.get('service', 'trellis')

    if not images_data:
        return {'error': 'No images provided. Please provide at least one image.'}, 400

    registry = current_app.extensions['3d_registry']
    service = registry.get_service(service_choice)

    if not service:
        return {'error': f'Service {service_choice} not supported'}, 400

    try:
        image_bytes_list: list[bytes] = []
        for img_str in images_data:
            if ',' in img_str:
                img_str = img_str.split(',')[1]
            image_bytes_list.append(base64.b64decode(img_str))

        if len(image_bytes_list) == 1:
            try:
                image_bytes_list = split_orthographic_sheet(image_bytes_list[0])
            except Exception as e:
                print(f"Image splitting failed: {e}")
                return {'error': 'Failed to split image'}

        model_bytes: bytes | None = service.generate(image_bytes_list)

        if not model_bytes:
            return {'error': 'Failed to generate 3D model'}, 500

        return send_file(
            BytesIO(model_bytes),
            mimetype='model/gltf-binary',
            as_attachment=True,
            download_name=f'generated_model_{service_choice}.glb'
        )

    except Exception as e:
        print(f"3D generation error ({type(e).__name__}): {e}")
        return {'error': 'Internal server error during 3D generation'}, 500


@api_bp.route('/available-models', methods=['POST'])
def available_models():
    """Return the list of registered service names for a given asset type (text, image, 3D)."""
    data = request.get_json()
    asset_type: str = data.get('asset_type')

    match asset_type:
        case "text":
            registry = current_app.extensions['prompt_registry']
        case "image":
            registry = current_app.extensions['image_registry']
        case "3D":
            registry = current_app.extensions['3d_registry']
        case _:
            return {'error': 'Invalid asset type'}, 400

    if asset_type == "image":
        services = [
            {"name": name, "supports_reference": svc.supports_reference}
            for name, svc in registry.get_services().items()
        ]
    else:
        services = list(registry.get_services().keys())

    return jsonify({'services': services}), 200


@api_bp.route('/evaluate-image', methods=['POST'])
def evaluate_image():
    """Score each provided image against the prompt using CLIP cosine similarity."""
    data = request.get_json()
    images_data: list[str] = data.get('images', [])
    prompt: str = data.get('prompt', '')

    if not images_data or not prompt:
        return {'error': 'Images and prompt are required'}, 400

    scorer = current_app.extensions.get('clip_scorer')
    evaluations: list[dict] = []

    for img_str in images_data:
        score = 0.0
        if scorer:
            try:
                b64_data = img_str.split(',')[1] if ',' in img_str else img_str
                img_bytes = base64.b64decode(b64_data)
                score = scorer.calculate_score(img_bytes, prompt)
            except Exception as e:
                print(f"Error scoring image: {e}")

        evaluations.append({'score': score})

    return jsonify({
        'status': 'success',
        'evaluations': evaluations
    }), 200


@api_bp.route('/convert-model', methods=['POST'])
def convert_model():
    """Convert a GLB file to OBJ (returned as a ZIP with textures) or FBX."""
    if 'model_file' not in request.files:
        return {'error': 'No file provided'}, 400

    file = request.files['model_file']
    target_format: str = request.form.get('format', 'obj').lower()

    try:
        file_bytes = file.read()
        import trimesh

        scene = trimesh.load(BytesIO(file_bytes), file_type='glb')
        out_buffer = BytesIO()

        if target_format == 'obj':
            export_data = scene.export(file_type='obj', include_texture=True, return_texture=True)

            # trimesh may return (obj_string, texture_dict) -- normalize to a dict
            if isinstance(export_data, tuple):
                obj_content = export_data[0]
                textures = export_data[1] if len(export_data) > 1 else {}
                if isinstance(textures, dict):
                    export_data = {**textures, 'generated_model.obj': obj_content}
                else:
                    export_data = obj_content

            if isinstance(export_data, dict):
                with zipfile.ZipFile(out_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for file_name, data in export_data.items():
                        zip_file.writestr(
                            file_name,
                            data.encode('utf-8') if isinstance(data, str) else data
                        )
                mimetype = 'application/zip'
                filename = 'generated_model_obj_package.zip'
            else:
                out_buffer.write(export_data.encode('utf-8') if isinstance(export_data, str) else export_data)
                mimetype = 'text/plain'
                filename = 'generated_model.obj'

        elif target_format == 'fbx':
            return {'error': 'FBX is a proprietary format and requires the Autodesk SDK or Blender installed on the server. Please download as OBJ or GLB.'}, 501
        else:
            return {'error': 'Unsupported format'}, 400

        out_buffer.seek(0)
        return send_file(out_buffer, mimetype=mimetype, as_attachment=True, download_name=filename)

    except ImportError:
        return {'error': 'Missing library. Please run: pip install trimesh'}, 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'error': f'Conversion failed: {str(e)}'}, 500


@api_bp.route('/save-job', methods=['POST'])
def save_job():
    """Persist a completed generation job to Google Sheets."""
    data = request.get_json()

    try:
        sheets_manager = current_app.extensions['sheet_manager']

        sheets_data = {
            "User": data.get('user', ''),
            "Description": data.get('description', ''),
            "Image Prompt": data.get('input_prompt', ''),
            "LLM Used": data.get('text_model', ''),
            "System Prompt": SYSTEM_INSTRUCTION,
            "Optimized Image Prompt": data.get('optimized_prompt', ''),
            "Image Generator": data.get('image_model', ''),
            "Image 1": data.get('image_1', ''),
            "Image 2": data.get('image_2', ''),
            "Image 3": data.get('image_3', ''),
            "Image 4": data.get('image_4', ''),
            "3D Model Generator": data.get('three_d_model', ''),
            "Model link": data.get('model_link', ''),
            "Analysis": data.get('analysis', ''),
        }

        sheets_manager.update_row(sheets_data, "Sheet1")
        return jsonify({'status': 'success'}), 200

    except Exception as e:
        print(f"Failed to save job to Sheets: {e}")
        return {'error': 'Failed to save job to Sheets'}, 500


@api_bp.route('/analyze-discrepancies', methods=['POST'])
def analyze_discrepancies():
    """
    Compare the 2D concept image against a snapshot of the generated 3D model using Gemini.

    Returns a brief analysis of discrepancies and a suggested re-optimized prompt that
    addresses the problem areas for the next generation run.
    """
    data = request.get_json()
    original_prompt: str = data.get('original_prompt', '')
    input_images: list[str] = data.get('input_images', [])
    model_snapshots: list[str] = data.get('model_snapshots', [])

    if not input_images or not model_snapshots:
        return {'error': 'Both input images and model snapshots are required'}, 400

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=current_app.config['GOOGLE_KEY'])

        prompt_text = f"""
        You are an expert 3D QA engineer. You are evaluating a 3D generation pipeline.
        The user originally prompted the image generator with: "{original_prompt}"

        I am providing you with two sets of images:
        1. The generated 2D concept image(s) (what the 3D model *should* look like).
        2. Snapshots of the final generated 3D model.

        Task:
        1. Analyze the discrepancies between the 2D concept and the 3D model (e.g., missing details, distorted geometry, texture failures).
        2. Based on these failures, write a NEW, optimized image generation prompt. This new prompt should emphasize the problematic areas to force the 2D image generator to create clearer, more distinct features that the 3D generator will have an easier time interpreting.

        Respond STRICTLY in JSON format with the following keys:
        "analysis": "A brief 2-3 sentence analysis of the discrepancies.",
        "suggested_prompt": "The new optimized prompt string."
        """

        contents = [prompt_text]

        def attach_images(img_list: list[str]) -> None:
            for img_str in img_list:
                if ',' in img_str:
                    img_str = img_str.split(',')[1]
                contents.append(
                    types.Part.from_bytes(data=base64.b64decode(img_str), mime_type='image/png')
                )

        attach_images(input_images)
        attach_images(model_snapshots)

        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=contents,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )

        result_data = json.loads(response.text)

        return jsonify({
            'status': 'success',
            'analysis': result_data.get('analysis', ''),
            'suggested_prompt': result_data.get('suggested_prompt', '')
        }), 200

    except Exception as e:
        print(f"Discrepancy analysis error: {e}")
        return {'error': str(e)}, 500
