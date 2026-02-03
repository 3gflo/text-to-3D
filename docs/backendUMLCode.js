classDiagram
    %% --- Controllers (API Layer) ---
    class PromptController {
        +optimize_prompt(org_prompt: str)
    }
    class ImageController {
        +generate_image_workflow(prompt: str)
        +analyze_image(image_url: str, prompt: str)
    }
    class 3DController {
        +convert_to_3d(image_url: str)
        +check_status(job_id: str)
    }

    %% --- Core Services (Logic Layer) ---
    class LLMService {
        +optimize_prompt(org_prompt: str) str
    }
    class CLIPScorerService {
        +calculate_score(image: str, prompt: str) float
        +is_score_passing(score: float) bool
    }
    class SheetManager {
        <<Singleton>>
        +add_entry(data: dict, sheet_name: str)
        +update_row(data: dict, sheet_name: str)
        +get_headers(sheet_name: str)
    }
    
    %% --- Registries (Factory Pattern) ---
    class ImageServiceRegistry {
        -services: dict
        +__init__(app_config)
        +get_service(service_name: str) AbstractImageGenerator
    }
    
    class 3DServiceRegistry {
        -services: dict
        +__init__(app_config)
        +get_service(service_name: str) Abstract3DGenerator
    }

    %% --- Generator Abstractions ---
    class AbstractImageGenerator {
        <<Interface>>
        +generate_image(prompt: str, params: dict) str
    }
    class Abstract3DGenerator {
        <<Interface>>
        +generate_model(images: List[str], prompt: str, params: dict) str
    }

    %% --- Concrete Implementations ---
    class ConcreteImageExample {
        +name: str
        +client: Client
        +generate_image(prompt: str, params: dict)
    }
    class MockImageGenerator {
        +name: str
        +client: Client
        +generate_image(prompt: str, params: dict)
    }
    
    class Concrete3DModelExample {
        +name: str
        +client: Client
        +generate_model(images: List[str], prompt: str, params: dict)
    }
    class Mock3DGenerator {
        +name: str
        +client: Client
        +generate_model(images: List[str], prompt: str, params: dict)
    }

    %% --- Infrastructure / Utils ---
    class AppConfig {
        +get(key: str)
    }

    class GoogleSheetsClient {
        +read_range(spreadsheet_id, range_name)
        +write_range(spreadsheet_id, range_name, values)
        +append_to_range(spreadsheet_id, sheet_name, values)
        -_authenticate()
    }

    %% --- Relationships ---
    %% Controllers use Services
    PromptController --> LLMService : uses
    PromptController --> SheetManager : logs data
    
    ImageController --> ImageServiceRegistry : requests generator
    ImageController --> CLIPScorerService : uses
    ImageController --> SheetManager : logs data

    3DController --> 3DServiceRegistry : requests generator
    3DController --> SheetManager : logs data

    %% SheetManager uses GoogleSheetsClient
    SheetManager --> GoogleSheetsClient : acts as a proxy

    %% Image Registry manages Implementations
    ImageServiceRegistry --> AppConfig : reads keys
    ImageServiceRegistry ..> ConcreteImageExample : instantiates
    ImageServiceRegistry ..> MockImageGenerator : fallback

    %% 3D Registry manages Implementations
    3DServiceRegistry --> AppConfig : reads keys
    3DServiceRegistry ..> Concrete3DModelExample : instantiates
    3DServiceRegistry ..> Mock3DGenerator : fallback

    %% Inheritance / Implementation
    ConcreteImageExample --|> AbstractImageGenerator
    MockImageGenerator --|> AbstractImageGenerator
    
    Concrete3DModelExample --|> Abstract3DGenerator
    Mock3DGenerator --|> Abstract3DGenerator