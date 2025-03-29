import argparse
import asyncio
from pathlib import Path

from core.dispatchers.cursor_dispatcher import CursorDispatcher
from config.ConfigManager import ConfigManager
from core.PathManager import PathManager

async def dispatch_all_prompts(prompt_dir: Path, auto: bool = False):
    config = ConfigManager()
    path_manager = PathManager()
    dispatcher = CursorDispatcher(config, path_manager)

    prompt_files = sorted(prompt_dir.glob("*.prompt.md"))
    if not prompt_files:
        print(f"[!] No prompt files found in: {prompt_dir}")
        return

    for prompt_file in prompt_files:
        print(f"\n📤 Dispatching: {prompt_file.name}")
        result = await dispatcher.run_prompt_from_file(prompt_file, auto=auto)
        
        if result.get("success"):
            print(f"✅ Success: {prompt_file.name}")
        else:
            print(f"❌ Failed: {prompt_file.name}")
            print(result.get("error"))

def main():
    parser = argparse.ArgumentParser(description="Dispatch all generated prompt files to Cursor.")
    parser.add_argument(
        "--dir", type=str, default="temp/generated_prompts",
        help="Directory containing .prompt.md files"
    )
    parser.add_argument(
        "--auto", action="store_true",
        help="Run in automatic mode without manual trigger"
    )
    args = parser.parse_args()

    prompt_dir = Path(args.dir)
    if not prompt_dir.exists():
        print(f"[!] Directory does not exist: {prompt_dir}")
        return

    asyncio.run(dispatch_all_prompts(prompt_dir, auto=args.auto))

if __name__ == "__main__":
    main()
