import logging
from pathlib import Path
from typing import Dict, Any, Optional
import discord
import asyncio
import threading
import json

# Core components
from core.PathManager import PathManager
from core.config.config_manager import ConfigManager  # If needed; remove if unused
from core.recovery.recovery_engine import RecoveryEngine
from core.chat_engine.chat_engine_manager import ChatEngineManager
from core.factories.prompt_factory import PromptFactory
from core.meredith.meredith_dispatcher import MeredithDispatcher
from core.meredith.profile_scraper import ScraperManager
from core.meredith.resonance_scorer import ResonanceScorer
from core.memory.MeritChainManager import MeritChainManager
from core.chatgpt_automation.OpenAIClient import OpenAIClient

# System loading and rendering
from core.system_loader import DreamscapeSystemLoader
from core.rendering.template_engine import TemplateEngine
from core.prompt_cycle_orchestrator import PromptCycleOrchestrator

# Cursor-based refactor loop
from chat_mate.core.refactor.CursorSessionManager import CursorSessionManager

# UI / Interface services
from interfaces.pyqt.services.ProjectScanner import ProjectScanner
from interfaces.pyqt.services.MetricsService import MetricsService
from interfaces.pyqt.mock_service import MockService
# --- Test Runner ---
from interfaces.pyqt.services.TestRunner import TestRunner 
# --- END Test Runner ---
# --- Git Manager ---
from interfaces.pyqt.services.GitManager import GitManager
# --- END Git Manager ---
# --- Prompt Service Deps ---
from core.DriverManager import DriverManager # For PromptService
from core.services.prompt_execution_service import PromptService
# --- END Prompt Service Deps ---

# --- Cursor Dispatcher ---
from core.refactor.cursor_dispatcher import CursorDispatcher
# --- END Cursor Dispatcher ---

# --- NEW: Automation Loop Services ---
from core.services.task_queue_service import TaskQueueService
from core.services.elephant_builder_service import ElephantBuilderService
# --- END NEW ---

# --- Task Management & Feedback for PromptExecutionService ---
from core.task_manager import TaskManager
from core.task_feedback import TaskFeedbackManager
from core.PromptExecutionService import PromptExecutionService
# --- END Task Management ---

# --- TODO Scanner ---
from core.utils.todo_scanner import TodoScanner
# --- END TODO Scanner ---

from core.services.discord.DiscordBatchDispatcher import DiscordBatchDispatcher
from core.services.discord.DiscordLogger import DiscordLogger
from core.services.discord.DiscordManager import DiscordManager

from core.merit.test_generator_service import TestGeneratorService
from core.merit.test_coverage_analyzer import TestCoverageAnalyzer


class ServiceInitializationError(Exception):
    """Custom exception for critical service initialization failures."""
    pass


class ServiceInitializer:
    """
    Handles the initialization of all core and UI services. Critical failures raise
    ServiceInitializationError. Non-critical failures gracefully degrade to mock services.
    """

    @staticmethod
    def initialize_all(
        logger: logging.Logger, 
        path_manager: PathManager,
        discord_client: Optional[discord.Client] = None, 
        loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> Dict[str, Any]:
        """
        Initialize required services for Dream.OS, including newly added automation loop services.

        Args:
            logger: Python logger instance for debug/info/error messages.
            path_manager: Provides consistent path references throughout the system.
            discord_client: Optional initialized discord.py client instance.
            loop: Optional asyncio event loop instance.

        Returns:
            A dictionary containing all successfully initialized services.
        :raises ServiceInitializationError: If any critical service fails irrecoverably.
        """

        services = {
            'core_services': {},
            'component_managers': {},
            'prompt_manager': None,
            'chat_manager': None,
            # Initialize other keys used directly
            'system_loader': None,
            'template_manager': None,
            'config_manager': None,
            'prompt_cycle_orchestrator': None,
            'cursor_session_manager': None,
            'project_scanner': None,
            'metrics': None,
            'recovery': None,
            'merit_chain_manager': None,
            'openai_client': None,
            'meredith_dispatcher': None,
            'scraper_manager': None,
            'resonance_scorer': None,
            # --- NEW: Automation Loop Services ---
            'task_queue_service': None,
            'elephant_builder_service': None,
            # --- END NEW ---
        }

        logger.info("ServiceInitializer: Initializing services...")

        # -------------------------------------------------------------
        # 0. Core Managers (PathManager already passed in, ConfigManager)
        # -------------------------------------------------------------
        try:
            config_manager_instance = ConfigManager()
            services['config_manager'] = config_manager_instance
            logger.info("ServiceInitializer: ConfigManager initialized.")
        except Exception as e:
            logger.critical(f"ServiceInitializer: CRITICAL - Failed to initialize ConfigManager: {e}", exc_info=True)
            raise ServiceInitializationError(f"ConfigManager failed: {e}") from e
            
        # -------------------------------------------------------------
        # 1. System Loader & Template Engine (CRITICAL)
        # -------------------------------------------------------------
        try:
            system_loader = DreamscapeSystemLoader()
            config_path = path_manager.get_path("memory") / "config.yml"
            system_loader.load_config(config_path=config_path)
            services['system_loader'] = system_loader
            logger.info("ServiceInitializer: DreamscapeSystemLoader initialized")

            template_manager = TemplateEngine()
            system_loader.register_service("template_manager", template_manager)
            services["template_manager"] = template_manager
            logger.info("ServiceInitializer: TemplateEngine registered as template_manager")

        except Exception as e:
            logger.critical(
                f"ServiceInitializer: CRITICAL - Failed to initialize DreamscapeSystemLoader or TemplateManager: {e}"
            )
            raise ServiceInitializationError(f"SystemLoader/TemplateManager failed: {e}") from e

        # -------------------------------------------------------------
        # 2. Prompt Manager (CRITICAL)
        # -------------------------------------------------------------
        try:
            logger.info("ServiceInitializer: Initializing PromptManager via factory...")
            prompt_manager_instance = PromptFactory.create_prompt_manager()
            if prompt_manager_instance:
                services['prompt_manager'] = prompt_manager_instance
                logger.info("ServiceInitializer: PromptManager initialized successfully.")
            else:
                # Factory returning None is a critical failure
                raise RuntimeError("PromptFactory returned None")
        except Exception as e:
            logger.critical(
                f"ServiceInitializer: CRITICAL - Failed to initialize PromptManager: {e}",
                exc_info=True
            )
            raise ServiceInitializationError(f"PromptManager failed: {e}") from e

        # -------------------------------------------------------------
        # 3. Prompt Cycle Orchestrator (CRITICAL)
        # -------------------------------------------------------------
        try:
            orchestrator = PromptCycleOrchestrator()
            services['prompt_cycle_orchestrator'] = orchestrator
            if services['system_loader']:
                services['system_loader'].register_service('prompt_cycle_orchestrator', orchestrator)
            logger.info("ServiceInitializer: PromptCycleOrchestrator initialized")
        except Exception as e:
            logger.critical(
                f"ServiceInitializer: CRITICAL - Failed to initialize PromptCycleOrchestrator: {str(e)}"
            )
            raise ServiceInitializationError(f"PromptCycleOrchestrator failed: {e}") from e

        # -------------------------------------------------------------
        # 4. Cursor Session Manager (CRITICAL)
        # -------------------------------------------------------------
        try:
            cursor_session_manager = CursorSessionManager(
                project_root=str(path_manager.get_path('project_root')),
                dry_run=False
            )
            cursor_session_manager.start_loop()
            services['cursor_session_manager'] = cursor_session_manager
            logger.info("ServiceInitializer: CursorSessionManager initialized and started")
        except Exception as e:
            logger.critical(f"ServiceInitializer: CRITICAL - Failed to initialize CursorSessionManager: {str(e)}")
            raise ServiceInitializationError(f"CursorSessionManager failed: {e}") from e

        # -------------------------------------------------------------
        # 5. Project Scanner (CRITICAL)
        # -------------------------------------------------------------
        try:
            project_scanner = ProjectScanner(
                project_root=str(path_manager.get_path('project_root')),
                cache_path=str(path_manager.get_path('cache') / 'analysis_cache.json')
            )
            if not project_scanner.load_cache()["files"]:
                project_scanner.scan_project(max_files=100)
            services['project_scanner'] = project_scanner
            logger.info("ServiceInitializer: ProjectScanner initialized")
        except Exception as e:
            logger.critical(f"ServiceInitializer: CRITICAL - Failed to initialize ProjectScanner: {str(e)}")
            raise ServiceInitializationError(f"ProjectScanner failed: {e}") from e

        # -------------------------------------------------------------
        # 6. Metrics Service & Recovery Engine (CRITICAL)
        # -------------------------------------------------------------
        try:
            metrics_dir = path_manager.get_path("metrics")
            metrics_service = MetricsService(metrics_dir)
            services["metrics"] = metrics_service
            logger.info("ServiceInitializer: Initialized metrics service")

            recovery_engine = RecoveryEngine(
                cursor_session=services.get('cursor_session_manager'),
                metrics_service=metrics_service
            )
            services["recovery"] = recovery_engine
            logger.info("ServiceInitializer: Initialized recovery engine")
        except Exception as e:
            logger.critical(f"ServiceInitializer: CRITICAL - Failed to initialize metrics/recovery services: {e}")
            raise ServiceInitializationError(f"Metrics/Recovery failed: {e}") from e

        # -------------------------------------------------------------
        # 7. Chat Engine Manager (CRITICAL)
        # -------------------------------------------------------------
        try:
            logger.info("ServiceInitializer: Initializing ChatEngineManager...")
            chat_manager_instance = ChatEngineManager(
                config=services.get('config_manager'),
                logger=logger,
                prompt_manager=services.get('prompt_manager'),
                discord_manager=services.get('discord_manager')
            )
            services['chat_manager'] = chat_manager_instance
            logger.info("ServiceInitializer: ChatEngineManager initialized successfully.")
        except Exception as e:
            logger.critical(f"ServiceInitializer: CRITICAL - Failed to initialize ChatEngineManager: {e}",
                            exc_info=True)
            raise ServiceInitializationError(f"ChatEngineManager failed: {e}") from e

        # -------------------------------------------------------------
        # 8. Meredith-Related Services (Mixed Criticality)
        # -------------------------------------------------------------
        # --- ADD path_manager TO services BEFORE MeredithDispatcher init --- #
        services['path_manager'] = path_manager # Make it available for injection
        # --------------------------------------------------------------------- #

        # MeritChainManager (Non-Critical 🟡)
        try:
            memory_path = path_manager.get_path("data") / "meritchain.json"
            schema_path = path_manager.get_path("core") / "schemas" / "merit_chain_schema.json"
            if not schema_path.exists():
                logger.warning(
                    f"ServiceInitializer: MeritChain schema not found at {schema_path}. "
                    f"MeritChainManager will be mocked."
                )
                raise FileNotFoundError("Merit chain schema missing")

            merit_chain_manager = MeritChainManager(str(memory_path), str(schema_path))
            services['merit_chain_manager'] = merit_chain_manager
            logger.info("ServiceInitializer: MeritChainManager initialized.")
        except Exception as e:
            logger.warning(f"ServiceInitializer: Failed to initialize MeritChainManager: {e}. Using MockService.")
            services['merit_chain_manager'] = MockService('merit_chain_manager')

        # OpenAI Client (Non-Critical 🟡)
        try:
            cache_path = path_manager.get_path("cache")
            profile_dir = cache_path / "browser_profiles" / "default"
            profile_dir.mkdir(parents=True, exist_ok=True)
            openai_client = OpenAIClient(profile_dir=str(profile_dir))
            services['openai_client'] = openai_client
            logger.info("ServiceInitializer: OpenAIClient initialized.")
        except Exception as e:
            logger.warning(f"ServiceInitializer: Failed to initialize OpenAIClient: {e}. Using MockService.")
            services['openai_client'] = MockService('openai_client')

        # MeredithDispatcher (Non-Critical 🟡)
        try:
            meredith_dispatcher = MeredithDispatcher(services)
            services['meredith_dispatcher'] = meredith_dispatcher
            logger.info("ServiceInitializer: MeredithDispatcher initialized.")
        except Exception as e:
            logger.warning(
                f"ServiceInitializer: Failed to initialize MeredithDispatcher: {e}. Using MockService."
            )
            services['meredith_dispatcher'] = MockService('meredith_dispatcher')

        # ScraperManager (CRITICAL ✅)
        try:
            scraper_manager = ScraperManager(headless=True)
            scraper_manager.register_default_scrapers()
            services['scraper_manager'] = scraper_manager
            logger.info("ServiceInitializer: ScraperManager initialized.")
        except Exception as e:
            logger.critical(f"ServiceInitializer: CRITICAL - Failed to initialize ScraperManager: {e}")
            raise ServiceInitializationError(f"ScraperManager failed: {e}") from e

        # ResonanceScorer (CRITICAL ✅)
        try:
            # Check if PathManager provides the specific sub-path key, else construct manually
            try:
                model_dir_path = path_manager.get_path("resonance_match_models") # Try specific key first
            except KeyError:
                logger.warning("Path key 'resonance_match_models' not found, constructing path from core.")
                # Fallback: Construct path relative to 'core' if the specific key isn't in paths.yml
                core_path = path_manager.get_path("core")
                model_dir_path = core_path / "meredith" / "resonance_match_models"
            
            # Ensure the directory exists
            model_dir_path.mkdir(parents=True, exist_ok=True)
            
            # --- Pass the DIRECTORY path to ResonanceScorer --- 
            resonance_scorer = ResonanceScorer(str(model_dir_path))
            # ----------------------------------------------------
            
            services['resonance_scorer'] = resonance_scorer
            logger.info("ServiceInitializer: ResonanceScorer initialized.")
        except KeyError as e:
            logger.critical(
                f"ServiceInitializer: CRITICAL - PathManager missing '{e}' key. Cannot initialize ResonanceScorer."
            )
            raise ServiceInitializationError(f"PathManager key missing for ResonanceScorer: {e}") from e
        except Exception as e:
            logger.critical(f"ServiceInitializer: CRITICAL - Failed to initialize ResonanceScorer service: {e}")
            raise ServiceInitializationError(f"ResonanceScorer failed: {e}") from e

        # -------------------------------------------------------------
        # 9. NEW: Automation Loop Services (CRITICAL ✅)
        # -------------------------------------------------------------
        try:
            logger.info("ServiceInitializer: Initializing ElephantBuilderService...")

            # Example: ElephantSpec at config/specs/ElephantSpec.json
            spec_path = path_manager.get_path("config") / "specs" / "ElephantSpec.json"
            if not spec_path.exists():
                logger.critical(
                    f"ServiceInitializer: CRITICAL - ElephantSpec.json not found at {spec_path}"
                )
                raise FileNotFoundError(f"ElephantSpec.json not found at {spec_path}")

            template_base_path = path_manager.get_path("templates") / "elephant"

            elephant_builder = ElephantBuilderService(
                path_manager=path_manager,
                template_manager=services.get('template_manager'),
                openai_client=services.get('openai_client'),
                spec_path=spec_path,
                template_base_path=template_base_path
            )
            services['elephant_builder_service'] = elephant_builder
            logger.info("ServiceInitializer: ElephantBuilderService initialized.")

        except Exception as e:
            logger.critical(
                f"ServiceInitializer: CRITICAL - Failed to initialize ElephantBuilderService: {e}",
                exc_info=True
            )
            raise ServiceInitializationError(f"ElephantBuilderService failed: {e}") from e

        try:
            logger.info("ServiceInitializer: Initializing TaskQueueService...")

            queue_path = path_manager.get_path("data") / "queues" / "task_queue.json"
            if not queue_path.exists():
                logger.warning(f"ServiceInitializer: Task queue file not found at {queue_path}. Creating empty file.")
                queue_path.parent.mkdir(parents=True, exist_ok=True)
                with open(queue_path, 'w', encoding='utf-8') as f:
                    f.write("[]")  # Initialize with empty JSON array

            task_queue = TaskQueueService(
                path_manager=path_manager,
                builder_service=services.get('elephant_builder_service'),
                queue_file_path=queue_path
            )
            services['task_queue_service'] = task_queue
            logger.info("ServiceInitializer: TaskQueueService initialized.")

        except Exception as e:
            logger.critical(
                f"ServiceInitializer: CRITICAL - Failed to initialize TaskQueueService: {e}",
                exc_info=True
            )
            raise ServiceInitializationError(f"TaskQueueService failed: {e}") from e

        # --- Initialize other critical services ---
        # CursorDispatcher
        try:
            logger.info("ServiceInitializer: Initializing CursorDispatcher...")
            templates_base_dir = path_manager.get_path("templates")
            cursor_prompts_base_dir = path_manager.get_path("cursor_prompts") 
            templates_dir = templates_base_dir / "prompt_templates"
            output_dir = cursor_prompts_base_dir / "outputs" 
            templates_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)
            cursor_dispatcher_instance = CursorDispatcher(
                templates_dir=str(templates_dir),
                output_dir=str(output_dir)
            )
            services['cursor_dispatcher'] = cursor_dispatcher_instance
            if system_loader := services.get('system_loader'):
                 system_loader.register_service('cursor_dispatcher', cursor_dispatcher_instance)
            logger.info("ServiceInitializer: CursorDispatcher initialized and registered.")
        except KeyError as e:
            logger.critical(f"ServiceInitializer: CRITICAL - PathManager missing key '{e}' needed for CursorDispatcher.")
            raise ServiceInitializationError(f"CursorDispatcher failed due to missing path key: {e}") from e
        except Exception as e:
            logger.critical(f"ServiceInitializer: CRITICAL - Failed to initialize CursorDispatcher: {e}", exc_info=True)
            raise ServiceInitializationError(f"CursorDispatcher failed: {e}") from e

        # TestRunner
        try:
            logger.info("ServiceInitializer: Initializing TestRunner...")
            test_runner_instance = TestRunner(project_root=str(path_manager.get_path('project_root')))
            services['test_runner'] = test_runner_instance
            if system_loader := services.get('system_loader'):
                system_loader.register_service('test_runner', test_runner_instance)
            logger.info("ServiceInitializer: TestRunner initialized and registered.")
        except Exception as e:
            logger.critical(f"ServiceInitializer: CRITICAL - Failed to initialize TestRunner: {e}", exc_info=True)
            raise ServiceInitializationError(f"TestRunner failed: {e}") from e
            
        # GitManager
        try:
            logger.info("ServiceInitializer: Initializing GitManager...")
            git_manager_instance = GitManager(project_root=str(path_manager.get_path('project_root')))
            services['git_manager'] = git_manager_instance
            if system_loader := services.get('system_loader'):
                system_loader.register_service('git_manager', git_manager_instance)
            logger.info("ServiceInitializer: GitManager initialized and registered.")
        except Exception as e:
            logger.critical(f"ServiceInitializer: CRITICAL - Failed to initialize GitManager: {e}", exc_info=True)
            raise ServiceInitializationError(f"GitManager failed: {e}") from e

        # DriverManager (Required by PromptService)
        try:
            logger.info("ServiceInitializer: Initializing DriverManager...")
            config_manager = services.get('config_manager')
            if not config_manager:
                 raise ServiceInitializationError("ConfigManager not found for DriverManager init")
            profile_dir = None
            cookie_file = None
            try: 
                profile_dir = str(path_manager.get_path("chrome_profile"))
                cookie_file = str(path_manager.get_path("cookies") / "default.pkl")
            except KeyError as path_key_error:
                 logger.warning(f"ServiceInitializer: Path key missing for DriverManager ({path_key_error}). Using defaults.")
            driver_manager_instance = DriverManager(
                headless=config_manager.get('HEADLESS_MODE', True),
                profile_dir=profile_dir,
                cookie_file=cookie_file,
                undetected_mode=config_manager.get('USE_UNDETECTED_DRIVER', True),
            )
            services['driver_manager'] = driver_manager_instance
            logger.info("ServiceInitializer: DriverManager initialized.")
        except Exception as e:
            logger.critical(f"ServiceInitializer: CRITICAL - Failed to initialize DriverManager: {e}", exc_info=True)
            raise ServiceInitializationError(f"DriverManager failed: {e}") from e

        # PromptService
        try:
            logger.info("ServiceInitializer: Initializing PromptService...")
            config_manager = services.get('config_manager')
            if not config_manager:
                 raise ServiceInitializationError("ConfigManager not found for PromptService init")
            prompt_service_instance = PromptService(
                config_manager=config_manager,
                path_manager=path_manager, 
                config_service=config_manager,
                prompt_manager=services.get('prompt_manager'),
                driver_manager=services.get('driver_manager'),
                feedback_engine=services.get('feedback_engine'), # Optional
                cursor_dispatcher=services.get('cursor_dispatcher'), # Optional
                cursor_manager=services.get('cursor_session_manager'), # Optional
                discord_manager=services.get('discord_manager') # Pass the manager
            )
            services['prompt_service'] = prompt_service_instance
            logger.info("ServiceInitializer: PromptService initialized successfully.")
        except Exception as e:
            logger.critical(f"ServiceInitializer: CRITICAL - Failed to initialize PromptService: {e}", exc_info=True)
            raise ServiceInitializationError(f"PromptService failed: {e}") from e

        # DreamscapeGenerationService (replaces EpisodeService)
        try:
            # Correct the import path to import from the package
            from chat_mate.core.dreamscape import DreamscapeGenerationService 
            services['episode_service'] = DreamscapeGenerationService() # Instantiate the correct class
            logger.info("ServiceInitializer: DreamscapeGenerationService (as episode_service) initialized successfully.")
        except ImportError as e:
            logger.critical(f"ServiceInitializer: CRITICAL - DreamscapeGenerationService module not found! Import Error: {e}")
            raise ServiceInitializationError(f"DreamscapeGenerationService module not found") from e

        # ExportService
        try:
            from core.services.export_service import ExportService
            services['export_service'] = ExportService() # Assuming simple init
            logger.info("ServiceInitializer: ExportService initialized successfully.")
        except ImportError:
            logger.critical(f"ServiceInitializer: CRITICAL - ExportService module not found!")
            raise ServiceInitializationError(f"ExportService module not found")
        except Exception as e:
            logger.critical(f"ServiceInitializer: CRITICAL - Failed to initialize ExportService: {e}", exc_info=True)
            raise ServiceInitializationError(f"ExportService failed: {e}") from e
        # --- END MOVED INITIALIZATIONS ---
        
        # -------------------------------------------------------------
        # 10. Development / Optional Mocks
        # -------------------------------------------------------------
        # Mocking the "task_orchestrator"
        services['core_services']['task_orchestrator'] = MockService('task_orchestrator')
        logger.info("ServiceInitializer: Using mock task_orchestrator for development.")

        # Note: Specific initialization for critical services is handled above.
        # This section is only for truly optional/development mocks.

        # Mocking WebScraper if it's non-critical and fails
        try:
            from core.services.web_scraper import WebScraper # Keep import local if only used here
            services['web_scraper'] = WebScraper() # Assuming simple init
            logger.info("ServiceInitializer: WebScraper initialized successfully.")
        except ImportError:
             logger.warning("ServiceInitializer: WebScraper module not found. Using mock.")
             services['web_scraper'] = MockService('web_scraper')
        except Exception as e:
            logger.warning(f"ServiceInitializer: Non-critical - Failed to initialize WebScraper: {e}. Using mock.", exc_info=True)
            services['web_scraper'] = MockService('web_scraper')
            
        # UI Manager (Non-Critical 🟡 - Mock OK)
        services['component_managers']['ui_manager'] = MockService('ui_manager')
        logger.info("ServiceInitializer: Using mock ui_manager for development")

        # --- ADD DiscordManager Initialization ---
        try:
            logger.info("ServiceInitializer: Initializing DiscordManager...")
            # DiscordManager handles its own config loading internally
            discord_manager_instance = DiscordManager() 
            # We might want to trigger bot run here or in the main application logic
            # For now, just initialize the manager instance.
            services['discord_manager'] = discord_manager_instance
            logger.info("ServiceInitializer: DiscordManager initialized.")
        except Exception as e:
            logger.error(f"ServiceInitializer: Failed to initialize DiscordManager: {e}", exc_info=True)
            services['discord_manager'] = MockService('discord_manager')
            logger.warning("ServiceInitializer: Using mock DiscordManager.")
        # ----------------------------------------

        # --- Initialize DiscordLogger using the DiscordManager ---
        try:
            logger.info("ServiceInitializer: Initializing DiscordLogger...")
            # Get DiscordManager 
            discord_manager = services.get('discord_manager') 

            # Update error check for DiscordManager
            if not discord_manager or isinstance(discord_manager, MockService):
                 raise ServiceInitializationError("DiscordManager not found or mocked for DiscordLogger init")

            # DiscordLogger instantiation uses DiscordManager
            discord_logger_instance = DiscordLogger(
                discord_manager=discord_manager
            )
            services['discord_logger'] = discord_logger_instance
            # Optionally register with system_loader if needed elsewhere
            # if system_loader := services.get('system_loader'):
            #     system_loader.register_service('discord_logger', discord_logger_instance)
            logger.info("ServiceInitializer: DiscordLogger initialized.")
        except Exception as e:
            logger.error(f"ServiceInitializer: Failed to initialize DiscordLogger: {e}", exc_info=True)
            services['discord_logger'] = MockService('discord_logger')
            logger.warning("ServiceInitializer: Using mock DiscordLogger.")
        # --------------------------------------

        # --- ADD Test Generator and Analyzer Initialization ---
        try:
            logger.info("ServiceInitializer: Initializing TestGeneratorService...")
            test_generator_instance = TestGeneratorService(
                prompt_manager=services.get('prompt_manager'),
                chat_manager=services.get('chat_manager'), # Assumes chat_manager is initialized before this
                config=services.get('config_manager'),
                logger=logger
            )
            services['test_generator'] = test_generator_instance
            logger.info("ServiceInitializer: TestGeneratorService initialized.")
        except Exception as e:
            logger.error(f"ServiceInitializer: Failed to initialize TestGeneratorService: {e}", exc_info=True)
            services['test_generator'] = MockService('test_generator')
            logger.warning("ServiceInitializer: Using mock TestGeneratorService.")

        try:
            logger.info("ServiceInitializer: Initializing TestCoverageAnalyzer...")
            coverage_file_path = path_manager.get_path('project_root') / ".coverage"
            test_analyzer_instance = TestCoverageAnalyzer(
                config=services.get('config_manager'),
                coverage_data_file=str(coverage_file_path), # Pass path
                logger=logger
            )
            services['test_analyzer'] = test_analyzer_instance
            logger.info("ServiceInitializer: TestCoverageAnalyzer initialized.")
        except Exception as e:
            logger.error(f"ServiceInitializer: Failed to initialize TestCoverageAnalyzer: {e}", exc_info=True)
            services['test_analyzer'] = MockService('test_analyzer')
            logger.warning("ServiceInitializer: Using mock TestCoverageAnalyzer.")
        # ----------------------------------------------------

        # --- Initialize Task/Feedback Managers and PromptExecutionService (for TODO Scanner etc.)
        try:
            logger.info("ServiceInitializer: Initializing TaskManager, TaskFeedbackManager, and PromptExecutionService...")
            
            task_manager_instance = TaskManager()
            services['task_manager'] = task_manager_instance
            logger.info("ServiceInitializer: TaskManager initialized.")

            # Define paths needed by PromptExecutionService
            template_dir = path_manager.get_path('templates') / 'cursor_templates'
            queued_dir = path_manager.get_path('project_root') / '.cursor' / 'queued_tasks'
            memory_dir = path_manager.get_path('memory')
            memory_file_path = memory_dir / 'task_history.json'

            # Ensure directories exist
            template_dir.mkdir(parents=True, exist_ok=True)
            queued_dir.mkdir(parents=True, exist_ok=True)
            memory_dir.mkdir(parents=True, exist_ok=True)
            if not memory_file_path.exists():
                 with open(memory_file_path, 'w', encoding='utf-8') as f:
                     json.dump([], f) # Initialize with empty list

            # Fix: Pass only the expected 'memory_file' argument as a string
            feedback_manager_instance = TaskFeedbackManager(
                memory_file=str(memory_file_path) 
                # Removed incorrect memory_file_path and executed_dir arguments
            )
            services['task_feedback_manager'] = feedback_manager_instance
            logger.info("ServiceInitializer: TaskFeedbackManager initialized.")

            # Assuming CursorAutomation is not needed/available at this stage for the scanner
            # Fix: Ensure PromptExecutionService receives the correct feedback_manager instance
            prompt_execution_service_instance = PromptExecutionService(
                task_manager=task_manager_instance,
                template_dir=str(template_dir),
                queued_dir=str(queued_dir),
                # Assuming PromptExecutionService also uses memory_file string path
                memory_file=str(memory_file_path), 
                feedback_manager=feedback_manager_instance, # Pass the created instance
                cursor_automation=None # Explicitly set to None for now
            )
            services['prompt_execution_service_simple'] = prompt_execution_service_instance # Use distinct key
            logger.info("ServiceInitializer: PromptExecutionService (simple, for task file creation) initialized.")

        except Exception as e:
            # Log as warning, as this specific service might not be critical for all ops
            logger.warning(f"ServiceInitializer: Failed to initialize Task/Feedback/PromptExecution services: {e}", exc_info=True)
            services['task_manager'] = None
            services['task_feedback_manager'] = None
            services['prompt_execution_service_simple'] = None

        # ------------------------------------------------------------ -
        # 22. Run Initial TODO Scan (Non-Critical)
        # ------------------------------------------------------------ -
        if services.get('prompt_execution_service_simple'):
            try:
                logger.info("ServiceInitializer: Starting initial TODO scan...")
                todo_scanner = TodoScanner(
                    prompt_execution_service=services['prompt_execution_service_simple'],
                    root_dir=str(path_manager.get_path('project_root'))
                    # Using default excludes and patterns
                )
                queued_count = todo_scanner.scan_and_queue_tasks()
                logger.info(f"ServiceInitializer: TODO scan complete. Queued {queued_count} tasks.")
            except Exception as e:
                logger.error(f"ServiceInitializer: Error during initial TODO scan: {e}", exc_info=True)
        else:
             logger.warning("ServiceInitializer: Skipping initial TODO scan because PromptExecutionService (simple) failed to initialize.")

        # Final check for any absolutely critical services missed
        critical_keys = [ 'config_manager', 'system_loader', 'template_manager', 
                         'prompt_manager', 'prompt_cycle_orchestrator', 'cursor_session_manager', 
                         'project_scanner', 'metrics', 'recovery', 'chat_manager', 
                         'scraper_manager', 'resonance_scorer', 'elephant_builder_service', 
                         'task_queue_service', 'cursor_dispatcher', 'test_runner', 'git_manager', 
                         'prompt_service', 'episode_service', 'export_service', 'driver_manager',
                         'discord_manager', 'discord_logger', 'test_generator', 'test_analyzer'] # Excluded path_manager
                         
        for key in critical_keys:
            if key not in services: 
                 logger.critical(f"ServiceInitializer: CRITICAL - Service '{key}' was expected but not found after init attempts!")
                 # raise ServiceInitializationError(f"Critical service '{key}' missing after initialization.")
            elif services[key] is None or isinstance(services[key], MockService):
                 logger.critical(f"ServiceInitializer: CRITICAL - Service '{key}' failed to initialize properly (None or MockService)! Check its specific init block.")
                 # raise ServiceInitializationError(f"Critical service '{key}' failed initialization.")

        logger.info("ServiceInitializer: Service initialization complete.")
        return services
