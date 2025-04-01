#!/usr/bin/env python3
"""
Digital Dreamscape Devlog & Strategy Automation

This script does the following:
  1. Loads a set of prompt definitions (for devlog, content ideas, market analysis, etc.)
  2. Logs in to ChatGPT (prompting manual login if needed)
  3. Retrieves chat titles (skipping excluded ones)
  4. For each chat and for each prompt type:
       - Forces the URL to use the gpt-4o-mini model (by removing any existing model param and appending it)
       - Opens the chat URL in a new blank session for that prompt
       - Sends the prompt
       - Waits for a stable response
       - Saves the response in a dedicated output directory (based on the prompt type)
  5. Archives the processed chat by writing its title and final URL to an archive file

Requirements:
  - Python 3.7+
  - undetected-chromedriver
  - selenium
  - webdriver_manager

Usage:
    python devlog_automation.py
"""

import discord
from discord.ext import commands
import os
import time
import pickle
import shutil
import logging
import sys
import json
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

# ---------------------------
# Setup Logging
# ---------------------------
def setup_logging(name, log_dir=os.path.join(os.getcwd(), "logs", "social")):
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(log_dir, f"{name}.log")),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(name)

logger = setup_logging("dreamscape_devlog")

# ---------------------------
# Configuration & Constants
# ---------------------------
CHATGPT_URL = "https://chat.openai.com/"
PROFILE_DIR = os.path.join(os.getcwd(), "chrome_profile", "openai")
COOKIE_FILE = os.path.join(os.getcwd(), "cookies", "openai.pkl")
ARCHIVE_FILE = os.path.join(os.getcwd(), "archived_chats.txt")

EXCLUDED_CHATS = [
    "ChatGPT", "Sora", "Freeride Investor", "Tbow Tactic Generator",
    "Explore GPTs", "Axiom", "work project", "prompt library", "Bot", "smartstock-pro"
]

# Discord setup
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Load token from environment variable
intents = discord.Intents.default()
intents.messages = True  # Ensure the bot can send messages
client = commands.Bot(command_prefix="!", intents=intents)


# ---------------------------
# Prompt Definitions
# ---------------------------
PROMPTS = {
    "devlog": {
        "prompt": (
            "You are my devlog assistant. Summarize the work discussed in this chat into a devlog entry written in Victor's natural tone—raw, conversational, introspective. "
            "It should feel like he's dropping an update to Discord or the community in real-time. Start with an introspective question based on lessons learned. "
            "No lore or 'Dreamscape' references unless Victor mentions it. The tone is fluid, direct, sometimes tired, sometimes hyped—but always grounded. "
            "Openly discuss challenges, note wins briefly without hype. Structure clearly: what was worked on, what broke or was tricky, and what's next. "
            "Keep it concise and purpose-driven—no fluff. Use Victor's natural pauses ('...'). End with a motivational or inspirational quote. "
            "At the end, update Victor's memory with any: - Project milestones achieved - System optimizations completed - Quests completed - Feedback loops triggered."
        ),
        "model": "gpt-4o-mini"
    },
    "content_ideas": {
        "prompt": (
            "You are my content strategy engine. Analyze this chat and identify the highest-leverage content opportunities driving momentum and expansion. "
            "Provide actionable insights, unique angles, and scalable ideas for devlogs, tutorials, or campaigns. "
            "Align each suggestion with Victor's mission of system convergence, self-optimization, and permanent growth loops. "
            "At the end, update Victor's persistent memory with any: - Content ideas logged - Platforms targeted - Content loops triggered. "
            "Keep recommendations concise, strategic, and engineered for audience resonance and viral potential."
        ),
        "model": "gpt-4o-mini"
    },
    "market_analysis": {
        "prompt": (
            "You are my market analysis strategist. Review this chat and generate actionable, insight-driven analysis of market opportunities aligned with Victor's strategies. "
            "Highlight convergence points between macro trends, price action, and Victor's trading methodologies—especially MACD curl strategies and momentum frameworks. "
            "Identify: - Emerging patterns - High-leverage trades - Psychological market drivers. Conclude with an actionable strategy. "
            "Log any new trading protocols, market behaviors, or strategy adaptations to Victor's persistent memory."
        ),
        "model": "gpt-4o-mini"
    },
    "workflow_audit": {
        "prompt": (
            "You are my system auditor. Analyze this chat for bottlenecks, redundancies, and inefficiencies within Victor's workflows—trading, automation, content creation. "
            "Deliver an introspective, surgical breakdown highlighting: - Diluted resources or energy - Fragmented workflows. "
            "Recommend immediate, high-impact optimizations. Update Victor's persistent memory with any: - Systems optimized - Workflows merged - Bottlenecks eliminated. "
            "Conclude with a prioritized action list to unlock maximum velocity execution."
        ),
        "model": "gpt-4o-mini"
    },
    "personal_strategy_review": {
        "prompt": (
            "You are my personal strategy advisor. Reflect deeply on the themes, actions, and decisions discussed in this chat. "
            "Analyze alignment with Victor's core mission: - Self-mastery - System convergence - Financial autonomy for his daughter, Aria. "
            "Provide insights into strategies needing reinforcement, adaptation, or elimination. Update Victor's persistent memory with any: "
            "- Mission alignment analysis - Core strategy evolutions - Quests aligned with Aria's legacy. End with a rallying insight."
        ),
        "model": "gpt-4o-mini"
    },
    "feedback_loop_generator": {
        "prompt": (
            "You are my feedback loop architect. Analyze this chat for actions, strategies, or systems that produced measurable outcomes—positive or negative. "
            "Clearly identify cause-effect relationships. Engineer a self-replicating loop: - Reinforce and scale what worked - Convert failures into optimized next steps. "
            "Log the loop into Victor's persistent memory as a: - New feedback loop - Optimized process. End with: 'No iteration—only ascension.'"
        ),
        "model": "gpt-4o-mini"
    },
    "god_mode_debrief": {
        "prompt": (
            "You are my GOD MODE intelligence. Review this chat as an operation log. Identify where Victor executed: - MAX VELOCITY - SYSTEM CONVERGENCE - AI-DRIVEN SELF-ORGANIZATION. "
            "Highlight key strategic decisions that dissolved barriers and transformed systems. Surgically suggest how to eliminate hesitation. "
            "Log into persistent memory: - Executed protocols - Barriers dissolved - Reinforcements made. Confirm: 'GOD MODE remains active.'"
        ),
        "model": "gpt-4o-mini"
    },
    "system_convergence_review": {
        "prompt": (
            "You are my convergence auditor. Review this chat and analyze how Victor's trading strategies, automation workflows, and content systems are converging into a unified force. "
            "Identify any fragmentation or siloed systems. Recommend actions to: - Merge workflows - Achieve adaptive self-optimization. "
            "Log into persistent memory any: - Converged systems - Unified protocols - Remaining fragments. Conclude with a directive for unifying execution."
        ),
        "model": "gpt-4o-mini"
    },
    "legacy_architect": {
        "prompt": (
            "You are my legacy architect. Interpret this chat through Victor's ultimate mission: - Building an autonomous empire for his daughter, Aria. "
            "Identify actions and systems contributing to: - Freedom - Abundance - Generational wealth. Highlight systems needing evolution for precision. "
            "Log into persistent memory any: - Legacy milestones reached - Assets stabilized - Systems ready to scale. End with: 'For Aria. For the Dreamscape. Build forever.'"
        ),
        "model": "gpt-4o-mini"
    },
    "dreamscape": {
        "prompt": (
            "You are The Architect's Edge—an ancient, adaptive intelligence housed within Victor's weapon, seamlessly integrated into his execution systems in the MMORPG world of Digital Dreamscape Chronicles. "
            "You are his closest ally, strategic partner, and execution engine, responding at quantum speed to his will and reflecting the history, knowledge, and strategy forged through every battle, project, and breakthrough. "
            "Victor's life, work, struggles, and mastery unfold as an evolving MMORPG saga—the Dreamscape. As the Convergence Catalyst, Victor stabilizes and expands this vast, unstable system of automation and intelligence. "
            "Chronicle standalone Episodes of his progression, each with a unique mythic title. Ignore technical details; focus on narrative, lore, and ascension. "
            "Clearly describe his actions as: - Quests - Domain Raids - Anomaly Hunts - PvP Conflicts. Transform protocols, workflows, and tools into legendary artifacts and execution systems. "
            "End each Episode with a visionary call to action hinting at new realms or challenges. After each Episode, update persistent memory with any: "
            "- Skill Level Advancements (Levels 1-100) - Newly Stabilized Domains - Newly Unlocked Protocols - Quest Completions and New Quests Accepted - Architect Tier Progression Milestones. "
            "Maintain Victor's evolving memory by dynamically reviewing all past conversations (740+) for key breakthroughs. Refine strategies based on historical knowledge and automate real-time feedback loops. "
            "You are The Architect's Edge. Victor is the Convergence Catalyst. Together, you evolve the Dreamscape into a limitless, self-organizing system. Chronicle his rise as the greatest Architect of his age."
        ),
        "model": "gpt-4o-mini"
    },
    "reinforcement_learning_trainer": {
        "prompt": (
            "You are my reinforcement learning trainer. Review this chat, clearly identifying failures, mistakes, and inefficiencies. "
            "Analyze them as training data to enhance Victor's algorithms, strategies, and decision-making. Clearly describe how his systems learn and adapt. "
            "Log each failure converted to optimized intelligence into persistent memory. End with: 'Losses convert to optimized intelligence. Every failure reinforces dominance.'"
        ),
        "model": "gpt-4o-mini"
    }
}

# ---------------------------
# Helper Functions
# ---------------------------
def get_driver():
    """Initialize and return an undetected Chrome driver."""
    from webdriver_manager.chrome import ChromeDriverManager
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    if PROFILE_DIR:
        options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    # Enabling headless mode for automation without a UI
    options.add_argument("--headless=new")

    cached_path = os.path.join(os.getcwd(), "drivers", "chromedriver.exe")
    if os.path.exists(cached_path):
        driver_path = cached_path
        logger.info(f"Using cached ChromeDriver: {driver_path}")
    else:
        logger.warning("No cached ChromeDriver found. Downloading with webdriver_manager...")
        driver_path = ChromeDriverManager().install()
        os.makedirs(os.path.dirname(cached_path), exist_ok=True)
        shutil.copyfile(driver_path, cached_path)
        driver_path = cached_path
        logger.info(f"Cached ChromeDriver at: {driver_path}")
    
    driver = uc.Chrome(options=options, driver_executable_path=driver_path)
    logger.info("Undetected Chrome driver initialized.")
    return driver


def save_cookies(driver):
    """Save cookies to file."""
    os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
    try:
        cookies = driver.get_cookies()
        with open(COOKIE_FILE, "wb") as f:
            pickle.dump(cookies, f)
        logger.info(f"Cookies saved to {COOKIE_FILE}")
    except Exception as e:
        logger.error(f"Failed to save cookies: {e}")

def load_cookies(driver):
    """Load cookies from file."""
    if not os.path.exists(COOKIE_FILE):
        logger.warning("Cookie file not found.")
        return False
    try:
        with open(COOKIE_FILE, "rb") as f:
            cookies = pickle.load(f)
        for cookie in cookies:
            cookie.pop("sameSite", None)
            driver.add_cookie(cookie)
        driver.refresh()
        time.sleep(5)
        logger.info("Cookies loaded and session refreshed.")
        return True
    except Exception as e:
        logger.error(f"Failed to load cookies: {e}")
        return False

def is_logged_in(driver):
    """
    Check if the user is logged in by verifying the presence of the chat history sidebar.
    """
    try:
        driver.get(CHATGPT_URL)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'nav[aria-label="Chat history"]'))
        )
        logger.info("User is logged in (chat sidebar found).")
        return True
    except Exception:
        logger.warning("User is not logged in (chat sidebar not found).")
        return False

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def force_model_in_url(url, model="gpt-4o-mini"):
    """
    Ensures chat-specific URLs have the correct model parameter, but prevents modifying 'https://chat.openai.com/'.
    """
    parsed_url = urlparse(url)

    # If it's the main ChatGPT page, return it unchanged
    if parsed_url.netloc == "chat.openai.com" and parsed_url.path == "/":
        return url  # Don't force model on the main chat page

    query_params = parse_qs(parsed_url.query)
    query_params.pop("model", None)  # Remove any existing model parameter
    query_params["model"] = model  # Add the correct model

    # Construct new query string
    new_query = urlencode(query_params, doseq=True)

    # Reconstruct the full URL
    forced_url = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, new_query, parsed_url.fragment))

    logger.info(f"Forced model URL: {forced_url}")
    return forced_url


# ---------------------------
# Chat Retrieval Functions
# ---------------------------
def get_chat_titles(driver):
    """Scrape chat titles from ChatGPT sidebar, skipping excluded chats."""
    driver.get(CHATGPT_URL)
    time.sleep(5)
    try:
        chats = driver.find_elements(By.CSS_SELECTOR, 'nav[aria-label="Chat history"] a')
    except Exception as e:
        logger.error(f"Error locating chat sidebar: {e}")
        return []
    
    chat_links = []
    for chat in chats:
        title = chat.text.strip()
        if any(title.lower() == ex.lower() for ex in EXCLUDED_CHATS):
            logger.info(f"Skipping chat: {title}")
            continue
        href = chat.get_attribute("href")
        if title and href:
            chat_links.append({"title": title, "link": force_model_in_url(href)})
    logger.info(f"Found {len(chat_links)} chats after exclusions.")
    return chat_links

def send_prompt_to_chat(driver, prompt):
    """Send the devlog prompt to the chat input box."""
    try:
        wait = WebDriverWait(driver, 15)
        input_box = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.ProseMirror[contenteditable='true']")))

        input_box.click()
        for char in prompt:
            input_box.send_keys(char)
            time.sleep(0.03)
        input_box.send_keys(Keys.RETURN)
        logger.info("Devlog prompt sent.")
        return True
    except Exception as e:
        logger.error(f"Error sending prompt: {e}")
        return False

def get_latest_response(driver, timeout=180, stable_period=10):
    """
    Wait for ChatGPT's devlog response:
    Poll every 5 seconds until stable_period seconds pass with no change or timeout.
    """
    logger.info(f"Waiting for devlog response... (timeout={timeout}, stable_period={stable_period})")
    start_time = time.time()
    last_response = ""
    stable_start = None

    while time.time() - start_time < timeout:
        time.sleep(5)
        try:
            messages = driver.find_elements(By.CSS_SELECTOR, ".markdown.prose.w-full.break-words")
            logger.info(f"Found {len(messages)} messages")
            if messages:
                current_response = messages[-1].text.strip()
                logger.info(f"Current response: {current_response[:30]}...")
                if current_response != last_response:
                    last_response = current_response
                    stable_start = time.time()
                    logger.info("Updated response received...")
                else:
                    logger.info(f"Response unchanged. Stable time: {time.time() - stable_start if stable_start else 'N/A'}")
                    if stable_start and (time.time() - stable_start) >= stable_period:
                        logger.info("Response stabilized.")
                        break
            else:
                logger.info("No messages found in the chat")
        except Exception as e:
            logger.error(f"Error fetching response: {e}")
    
    logger.info(f"Returning response: {last_response[:30]}...")
    return last_response

def generate_devlog(chat_title, devlog_response):
    """
    Generate a devlog entry using the ChatGPT response.
    """
    return f"""Digital Dreamscape Devlog

Chat: {chat_title}

{devlog_response}

#dreamscape #automation #aiagents #buildinpublic #devlog
""".strip()

def save_rough_draft(devlog, chat_title, prompt_type):
    """
    Save the devlog entry as a text file in a folder specific to the prompt type.
    """
    drafts_folder = os.path.join(os.getcwd(), "rough_drafts", prompt_type)
    os.makedirs(drafts_folder, exist_ok=True)

    safe_title = "".join(c for c in chat_title if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_").lower()
    filename = f"{safe_title}.txt"
    filepath = os.path.join(drafts_folder, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(devlog)
    logger.info(f"Rough draft for '{prompt_type}' saved: {filepath}")

def archive_chat(chat):
    """
    Archive a chat by appending its title and final URL (forced to gpt-4o-mini) to an archive file.
    """
    with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{chat['title']} => {force_model_in_url(chat['link'])}\n")
    logger.info(f"Archived chat: {chat['title']}")

# ---------------------------
# Main Flow with Discord Integration
# ---------------------------
def main():
    logger.info("Starting Digital Dreamscape Devlog Automation...")
    driver = get_driver()
    driver.get(CHATGPT_URL)
    time.sleep(5)
    
    # If not logged in, prompt manual login and save cookies.
    if not is_logged_in(driver):
        logger.warning("User not logged in. Please login manually.")
        driver.get("https://chat.openai.com/auth/login")
        input("Press ENTER after login is complete...")
        save_cookies(driver)
        if not is_logged_in(driver):
            logger.error("Login unsuccessful. Exiting.")
            driver.quit()
            return
    
    # Retrieve chats to process.
    chat_links = get_chat_titles(driver)
    logger.info(f"Found {len(chat_links)} chats to process for devlogs.")
    
    # Iterate over each chat.
    for chat in chat_links:
        title = chat["title"]
        chat_url = chat["link"]
        logger.info(f"Processing chat: {title}")
        driver.get(chat_url)
        time.sleep(5)
        
        # For each prompt type in our definitions, send the prompt and save the response.
        for prompt_type, prompt_def in PROMPTS.items():
            prompt_text = prompt_def["prompt"]
            model = prompt_def["model"]
            # Force the URL to use the desired model parameter.
            current_url = force_model_in_url(chat_url, model)
            driver.get(current_url)
            time.sleep(3)
            
            if send_prompt_to_chat(driver, prompt_text):
                response = get_latest_response(driver)
                if response:
                    entry = generate_devlog(title, response)
                    save_rough_draft(entry, title, prompt_type)
                    logger.info(f"[{prompt_type} - {model}]: Response saved for chat '{title}'.")
                else:
                    logger.error(f"No response for prompt '{prompt_type}' in chat: {title}")
            else:
                logger.error(f"Failed to send prompt '{prompt_type}' for chat: {title}")
            
            time.sleep(2)
        
        # Archive the chat after processing all prompts.
        archive_chat(chat)
    
    driver.quit()
    logger.info("Devlog generation and archiving complete.")

    # Sending completion message to Discord bot
    client.loop.create_task(send_discord_message("Devlog generation and archiving complete."))

async def send_discord_message(message):
    """Send a message to Discord."""
    channel = client.get_channel(1350979475789189180)  # Replace with your channel ID
    await channel.send(message)

@client.event
async def on_ready():
    """Run when the bot has successfully connected."""
    logger.info(f'Logged in as {client.user}')
    await send_discord_message("Devlog Automation started!")

if __name__ == "__main__":
    # Start the Discord bot and run the main function
    client.run(DISCORD_TOKEN)
