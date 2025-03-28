import asyncio
from pathlib import Path

from config.ConfigManager import ConfigManager
from core.PathManager import PathManager
from core.refactor.cursor_dispatcher import CursorDispatcher
from core.pipelines.project_optimizer_agent import ProjectOptimizerAgent
from core.TemplateManager import TemplateManager

class FullSyncPipelineRunner:
    def __init__(self, logger=None):
        self.logger = logger or print
        self.config = ConfigManager()
        self.path_manager = PathManager()
        self.template_manager = TemplateManager()  # Using TemplateManager now
        self.cursor_dispatcher = CursorDispatcher(self.config, self.path_manager)
        self.optimizer_agent = ProjectOptimizerAgent(self.path_manager, self.logger)

        self.optimizer_plan_path = Path(".cursor/results/project_optimization_plan.json")
        self.prompt_output_dir = self.path_manager.get_temp_path("generated_prompts")

    async def run(self, mode: str = "all", auto: bool = True):
        """Run the full sync pipeline."""
        self.logger(f"\n🚀 [Full Sync] Starting full project optimization in mode: {mode.upper()}")

        # Step 1: Run meta-prompt to produce plan
        self.logger("📥 Rendering optimization plan prompt...")
        rendered_prompt = self.template_manager.render_general_template(
            "full_sync/project_optimizer.prompt.j2",
            {
                "project_context": self.optimizer_agent.load_optimization_plan("project_analysis.json"),
                "mode": mode,
            }
        )

        self.optimizer_plan_path.parent.mkdir(parents=True, exist_ok=True)
        self.optimizer_plan_path.write_text(rendered_prompt, encoding="utf-8")

        self.logger("📤 Dispatching optimization planner prompt to ChatGPT...")
        plan_result = await self.cursor_dispatcher.run_prompt_from_string(
            rendered_prompt,
            output_path=self.optimizer_plan_path,
            executor="chatgpt"
        )

        if not plan_result.get("success"):
            self.logger("❌ Failed to generate optimization plan.")
            return

        self.logger("✅ Optimization plan generated.")

        # Step 2: Convert plan to .prompt.md files
        plan = self.optimizer_agent.load_optimization_plan(self.optimizer_plan_path)
        prompt_paths = self.optimizer_agent.create_prompts_from_plan(plan)

        # Step 3: Dispatch all prompts to Cursor
        self.logger("🚀 Dispatching generated prompts...")
        for prompt_file in prompt_paths:
            result = await self.cursor_dispatcher.run_prompt_from_file(prompt_file, auto=auto)
            status = "✅" if result.get("success") else "❌"
            self.logger(f"{status} {prompt_file.name}")

        self.logger("🏁 Full Sync complete.")
