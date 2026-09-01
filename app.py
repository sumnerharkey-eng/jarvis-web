import asyncio
import base64
import io
import json
import math
import os
import queue
import random
import re
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
import cv2
import customtkinter as ctk
from dotenv import load_dotenv
import edge_tts
from groq import Groq
import mediapipe as mp
from PIL import Image, ImageTk
import psutil
import pyautogui
import pygame
import pyttsx3
import requests
import speech_recognition as sr
import yfinance as yf

# Safe import for global hotkeys
try:
    import keyboard
    KEYBOARD_LIB_LOADED = True
except ImportError:
    KEYBOARD_LIB_LOADED = False

# ==========================================
# 🏷️ ACTIVE BUILD & VERSION SIGNATURE
# ==========================================
APP_VERSION = "v5.2"
BUILD_DATE = "2026.08.31"
BUILD_SIGNATURE = f"BUILD {APP_VERSION} // MASTER STABILITY & THREAD-SAFE HUD MATRIX // {BUILD_DATE}"

# ==========================================
# 🔑 CONFIGURATION & INITIALIZATION
# ==========================================
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY is missing from your .env file!")

client = Groq(api_key=api_key)

try:
    pygame.mixer.init()
except Exception:
    pass

pyautogui.FAILSAFE = True

BASE_DIR = os.path.expanduser("~")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "Downloads", "JarvisDownloads")
SCRIPTS_DIR = os.path.join(BASE_DIR, "Downloads", "JarvisScripts")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(SCRIPTS_DIR, exist_ok=True)

# ==========================================
# 🗄️ PERSISTENT SQLITE MEMORY & BLUEPRINT VAULT
# ==========================================
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_memory.db")
db_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
db_cursor = db_conn.cursor()

db_cursor.execute(
    """CREATE TABLE IF NOT EXISTS memory_vault (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        content TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )"""
)
db_cursor.execute(
    """CREATE TABLE IF NOT EXISTS keybind_vault (
        action_name TEXT PRIMARY KEY,
        key_combination TEXT
    )"""
)
db_cursor.execute(
    """CREATE TABLE IF NOT EXISTS persistent_blueprints (
        title TEXT PRIMARY KEY,
        materials_json TEXT,
        source TEXT,
        blueprint_json TEXT
    )"""
)
db_cursor.execute(
    """CREATE TABLE IF NOT EXISTS portal_shortcuts (
        portal_name TEXT PRIMARY KEY,
        url TEXT
    )"""
)
db_conn.commit()

# Standard number keybinds (1 to 7)
DEFAULT_KEYBINDS = {
    "VOICE_LISTEN": "1",
    "SCREEN_SCAN": "2",
    "STOP_AUDIO": "3",
    "ULTRON_STUDIO": "4",
    "AUTO_CLICKER": "5",
    "DISMISS_SCHEMATIC": "6",
    "TACTICAL_ADVICE": "7",
}

def load_keybinds():
    keybinds = DEFAULT_KEYBINDS.copy()
    try:
        db_cursor.execute("SELECT action_name, key_combination FROM keybind_vault")
        rows = db_cursor.fetchall()
        for action, key in rows:
            if action in keybinds:
                keybinds[action] = key
    except Exception as e:
        print(f"Keybind Load Notice: {e}")
    return keybinds

def save_keybind_db(action_name, key_combination):
    try:
        db_cursor.execute(
            "INSERT OR REPLACE INTO keybind_vault (action_name, key_combination) VALUES (?, ?)",
            (action_name, key_combination.lower().strip())
        )
        db_conn.commit()
    except Exception as e:
        print(f"Keybind Save Error: {e}")

def save_blueprint_db(title, materials_list, source, blueprint_data):
    try:
        db_cursor.execute(
            "INSERT OR REPLACE INTO persistent_blueprints (title, materials_json, source, blueprint_json) VALUES (?, ?, ?, ?)",
            (title, json.dumps(materials_list), source, json.dumps(blueprint_data))
        )
        db_conn.commit()
    except Exception as e:
        print(f"Blueprint DB Save Error: {e}")

def fetch_blueprint_db(title):
    try:
        db_cursor.execute("SELECT materials_json, source, blueprint_json FROM persistent_blueprints WHERE title LIKE ?", (f"%{title}%",))
        row = db_cursor.fetchone()
        if row:
            return json.loads(row[0]), row[1], json.loads(row[2])
    except Exception as e:
        print(f"Blueprint DB Fetch Error: {e}")
    return None, None, None

def save_memory_categorized(category, content):
    try:
        db_cursor.execute("INSERT INTO memory_vault (category, content) VALUES (?, ?)", (category.upper(), content))
        db_conn.commit()
    except Exception as e:
        print(f"Categorized Memory Save Error: {e}")

def fetch_memories_by_category(category):
    try:
        db_cursor.execute("SELECT content FROM memory_vault WHERE category = ? ORDER BY id DESC LIMIT 5", (category.upper(),))
        return [r[0] for r in db_cursor.fetchall()]
    except Exception:
        return []

def register_portal(name, url):
    try:
        db_cursor.execute("INSERT OR REPLACE INTO portal_shortcuts (portal_name, url) VALUES (?, ?)", (name.lower(), url))
        db_conn.commit()
    except Exception as e:
        print(f"Portal Save Error: {e}")

def get_portal(name):
    try:
        db_cursor.execute("SELECT url FROM portal_shortcuts WHERE portal_name LIKE ?", (f"%{name.lower()}%",))
        row = db_cursor.fetchone()
        if row:
            return row[0]
    except Exception:
        pass
    return None

if not get_portal("roblox"):
    register_portal("roblox", "https://www.roblox.com")
if not get_portal("github"):
    register_portal("github", "https://github.com")

active_keybinds = load_keybinds()

# ==========================================
# 🎨 8 MULTI-SUIT PROTOCOLS, THEMES & VOICES
# ==========================================
THEMES = {
    "OVERWATCH": {
        "primary": "#00f5ff", "secondary": "#00aacc", "dim": "#00334d", "accent": "#00e5ff",
        "bg_dark": "#010409", "panel_bg": "#030a14", "card_bg": "#051122", "border": "#004d73",
        "text_user": "#a0e6ff", "name": f"MARK-XI // OVERWATCH [{APP_VERSION}]",
        "voice": "en-GB-RyanNeural", "sound_type": "crystal",
    },
    "COMBAT": {
        "primary": "#ff2a4b", "secondary": "#ffd000", "dim": "#590011", "accent": "#ff3b5c",
        "bg_dark": "#080103", "panel_bg": "#140205", "card_bg": "#220409", "border": "#8c001c",
        "text_user": "#ffa6b5", "name": f"MARK-II // WAR MACHINE COMBAT [{APP_VERSION}]",
        "voice": "en-US-ChristopherNeural", "sound_type": "combat_alert",
    },
    "HULKBUSTER": {
        "primary": "#ff4400", "secondary": "#ffbb00", "dim": "#4d1400", "accent": "#ff6600",
        "bg_dark": "#0a0300", "panel_bg": "#170600", "card_bg": "#240a00", "border": "#802b00",
        "text_user": "#ffd9b3", "name": f"MARK-XLIV // HULKBUSTER TURBO [{APP_VERSION}]",
        "voice": "en-US-EricNeural", "sound_type": "hydraulic_rumble",
    },
    "STEALTH": {
        "primary": "#ff9d00", "secondary": "#cc7a00", "dim": "#4d2e00", "accent": "#ffaa00",
        "bg_dark": "#080400", "panel_bg": "#120800", "card_bg": "#1c0d00", "border": "#804400",
        "text_user": "#ffd699", "name": f"MARK-V // STEALTH NIGHTSHADE [{APP_VERSION}]",
        "voice": "en-US-GuyNeural", "sound_type": "stealth_chirp",
    },
    "STARBOOST": {
        "primary": "#9d4edd", "secondary": "#c77dff", "dim": "#3c096c", "accent": "#e0aaff",
        "bg_dark": "#05010a", "panel_bg": "#0f021f", "card_bg": "#1a0436", "border": "#5a189a",
        "text_user": "#f0dbff", "name": f"MARK-XXXIX // STARBOOST DEEP SPACE [{APP_VERSION}]",
        "voice": "en-GB-ThomasNeural", "sound_type": "space_chime",
    },
    "MARK85": {
        "primary": "#ffd700", "secondary": "#ff3333", "dim": "#4d3d00", "accent": "#ffffff",
        "bg_dark": "#0a0701", "panel_bg": "#140e02", "card_bg": "#1f1503", "border": "#7a6300",
        "text_user": "#fff0a6", "name": f"MARK-LXXXV // NANOTECH PRIME [{APP_VERSION}]",
        "voice": "en-GB-LibbyNeural", "sound_type": "nanotech_pulse",
    },
    "HEARTBREAKER": {
        "primary": "#00ffcc", "secondary": "#ff007f", "dim": "#004d3d", "accent": "#ffffff",
        "bg_dark": "#000806", "panel_bg": "#00140f", "card_bg": "#00241b", "border": "#008066",
        "text_user": "#b3fff0", "name": f"MARK-XVII // HEARTBREAKER ARTILLERY [{APP_VERSION}]",
        "voice": "en-IE-ConnorNeural", "sound_type": "unibeam_charge",
    },
    "ULTRON": {
        "primary": "#ff1a35", "secondary": "#ff5566", "dim": "#4d000b", "accent": "#ffffff",
        "bg_dark": "#060001", "panel_bg": "#100103", "card_bg": "#1a0206", "border": "#800014",
        "text_user": "#ff99a8", "name": f"ULTRON // APEX MASTER MATRIX [{APP_VERSION}]",
        "voice": "en-US-RogerNeural", "sound_type": "dark_glitch",
    }
}

conversation_memory = [
    {
        "role": "system",
        "content": (
            "You are JARVIS / ULTRON, Tony Stark's articulate, highly capable, and intelligent tactical AI assistant. "
            "Speak clearly, stay in character, address the user as 'Sir', and keep spoken responses concise (2 to 3 sentences maximum)."
        ),
    }
]

# ==========================================
# 🔊 PROCEDURAL SUIT SOUND SYNTHESIZER
# ==========================================
def play_suit_sound(sound_type):
    def _synth():
        try:
            sample_rate = 44100
            duration = 0.12
            n_samples = int(sample_rate * duration)
            buf = bytearray()

            for i in range(n_samples):
                t = i / sample_rate
                if sound_type == "crystal":
                    freq = 900 + (600 * (i / n_samples))
                elif sound_type == "combat_alert":
                    freq = 280 if (i // 1500) % 2 == 0 else 440
                elif sound_type == "hydraulic_rumble":
                    freq = 120 + math.sin(t * 50) * 40
                elif sound_type == "stealth_chirp":
                    freq = 1800 - (1200 * (i / n_samples))
                elif sound_type == "space_chime":
                    freq = 528 * (1.5 if i > n_samples // 2 else 1.0)
                elif sound_type == "nanotech_pulse":
                    freq = 1200 + math.sin(t * 80) * 300
                elif sound_type == "unibeam_charge":
                    freq = 300 + (1000 * (i / n_samples)**2)
                elif sound_type == "dark_glitch":
                    freq = random.choice([150, 220, 680, 1100])
                else:
                    freq = 800 + (400 * (i / n_samples))

                val = int(32767.0 * 0.22 * math.sin(2.0 * math.pi * freq * t))
                buf += val.to_bytes(2, byteorder="little", signed=True)

            snd = pygame.mixer.Sound(buffer=bytes(buf))
            snd.play()
        except Exception:
            pass
    threading.Thread(target=_synth, daemon=True).start()

# ==========================================
# 📐 PROCEDURAL 3D BLUEPRINT & TECH TREE ENGINE
# ==========================================
def generate_procedural_wireframe(shape_type="core"):
    nodes, edges = [], []
    if shape_type in ["sphere", "atom"]:
        for i in range(12):
            a = i * (2 * math.pi / 12)
            nodes.append([int(45 * math.cos(a)), int(45 * math.sin(a)), 0])
            nodes.append([int(45 * math.cos(a)), 0, int(45 * math.sin(a))])
        for i in range(0, 24, 2):
            edges.append([i, (i + 2) % 24])
            edges.append([i + 1, ((i + 1) + 2) % 24])
        return {"name": "MOLECULAR MATRIX", "nodes": nodes, "edges": edges}

    for i in range(8):
        a = i * (2 * math.pi / 8)
        nodes.append([int(55 * math.cos(a)), int(55 * math.sin(a)), 0])
    for i in range(8):
        edges.append([i, (i + 1) % 8])
    for z in [-18, 18]:
        b = len(nodes)
        for i in range(8):
            a = i * (2 * math.pi / 8)
            nodes.append([int(32 * math.cos(a)), int(32 * math.sin(a)), z])
        for i in range(8):
            edges.append([b + i, b + ((i + 1) % 8)])
    for i in range(8):
        edges.extend([[i, 8 + i], [i, 16 + i], [8 + i, 16 + i]])
    nodes.extend([[0, 0, -28], [0, 0, 28]])
    c1, c2 = len(nodes) - 2, len(nodes) - 1
    for i in range(8):
        edges.extend([[8 + i, c1], [16 + i, c2]])
    return {"name": "ARC REACTOR CORE", "nodes": nodes, "edges": edges}

# ==========================================
# 📊 CENTRAL SYSTEM STATE (VERSION 10.0)
# ==========================================
state = {
    "status": "ONLINE",
    "active_view": "HUD",
    "current_theme": "OVERWATCH",
    "user_transcript": "Awaiting voice command...",
    "ultron_reply": f"Neural core online. Running build {APP_VERSION}. All systems nominal.",
    "current_gesture": "NO HAND DETECTED",
    "is_talking": False,
    "interrupted": False,
    "is_expanded": False,
    "current_scale": 1.0,
    "target_scale": 1.0,
    "is_analyzing_vision": False,
    "latest_frame": None,
    "cam_display_image": None,
    "system_alert": f"SYS_INTEGRITY: 100% // {BUILD_SIGNATURE}",
    "is_hacked": False,
    "hack_end_time": 0,
    "last_speech_time": 0,
    # 🤖 Macro State
    "auto_clicker_active": False,
    # ⏱️ Pomodoro State
    "pomodoro_active": False,
    "pomodoro_seconds": 1500,
    "pomodoro_mode": "FOCUS",
    # 📐 Blueprint Interactive State (Safe scaling bounds)
    "custom_blueprint": generate_procedural_wireframe("core"),
    "blueprint_scale": 1.0,
    "blueprint_pos": [220, 240],
    "blueprint_target_pos": [220, 240],
    "is_liquid": False,
    "liquid_fill": 0.75,
    "liquid_bubbles": [{"x": random.randint(-22, 22), "y": random.randint(10, 60), "r": random.randint(2, 4), "s": random.uniform(0.6, 1.8)} for _ in range(16)],
    # 🧪 Tech Tree Breakdown & Materials Matrix
    "explanation_mode": False,
    "explanation_title": "TECH TREE MATRIX",
    "explanation_materials": [],
    "tech_tree_nodes": [],
    "explanation_source": "Wikimedia & Scientific Archive",
    "explanation_image_tk": None,
    # 🖐️ Hand Tracking & Sticky Tethering
    "hand_detected": False,
    "is_fist": False,
    "hand_palm_center": [220, 240],
    "cam_hand_pos": None,
    "laser_cursor": [0, 0],
    "is_pinching": False,
    "laser_active": False,
    "repulsor_active": False,
    "repulsor_charge": 0.0,
    # 💻 Telemetry Metrics
    "cpu_usage": 0,
    "ram_usage": 0,
    "disk_usage": 0,
    "gaming_fps": 165,
    "render_latency": 3.8,
    "network_ping": 18,
    "cleaned_ram_mb": 1420,
    "nanite_integrity": 99.8,
    "unibeam_charge": 100.0,
    # 🌐 Feeds
    "weather_data": {"city": "Arlington Heights", "temp": "--", "condition": "Clear", "humidity": "--", "wind": "--"},
    "stock_data": {
        "AAPL": {"price": "$224.50", "change": "+1.25%"},
        "NVDA": {"price": "$128.90", "change": "+3.40%"},
        "TSLA": {"price": "$212.10", "change": "-0.85%"},
        "MSFT": {"price": "$448.20", "change": "+0.65%"},
        "SPY": {"price": "$562.30", "change": "+0.45%"},
    },
    "steam_data": {"top_game": "Counter-Strike 2", "players": "~1.4M Active"},
}

speech_queue = queue.Queue()
COOLDOWN_SPIDERMAN = 1.5
last_spiderman_trigger = 0

# ==========================================
# ⏱️ POMODORO TIMER LOOP
# ==========================================
def pomodoro_countdown_loop():
    while True:
        if state["pomodoro_active"]:
            if state["pomodoro_seconds"] > 0:
                state["pomodoro_seconds"] -= 1
            else:
                if state["pomodoro_mode"] == "FOCUS":
                    state["pomodoro_mode"] = "BREAK"
                    state["pomodoro_seconds"] = 300
                    queue_speech("Focus session complete, Sir. Take a 5-minute tactical break.")
                else:
                    state["pomodoro_mode"] = "FOCUS"
                    state["pomodoro_seconds"] = 1500
                    queue_speech("Break session concluded, Sir. Resuming focus protocol.")
        time.sleep(1)

threading.Thread(target=pomodoro_countdown_loop, daemon=True).start()

def start_focus_session(minutes=25):
    state["pomodoro_active"] = True
    state["pomodoro_mode"] = "FOCUS"
    state["pomodoro_seconds"] = int(minutes) * 60
    state["system_alert"] = f"POMODORO FOCUS ACTIVE ({minutes} MIN)"
    return f"Focus session initialized for {minutes} minutes, Sir. All distractions dampened."

def stop_focus_session():
    state["pomodoro_active"] = False
    state["system_alert"] = f"SYS_INTEGRITY: 100% // {BUILD_SIGNATURE}"
    return "Focus timer disengaged, Sir."

# ==========================================
# 🌤️ WEATHER-REACTIVE ATMOSPHERE
# ==========================================
def apply_weather_atmospheric_theme():
    condition = state["weather_data"].get("condition", "").lower()
    if "rain" in condition or "storm" in condition:
        THEMES["OVERWATCH"]["primary"] = "#3399ff"
        THEMES["OVERWATCH"]["accent"] = "#66b2ff"
    elif "sun" in condition or "clear" in condition:
        THEMES["OVERWATCH"]["primary"] = "#00f5ff"
        THEMES["OVERWATCH"]["accent"] = "#00e5ff"
    apply_theme_styling()

def update_weather_atmospheric_loop():
    while True:
        try:
            city = state["weather_data"]["city"]
            res = requests.get(f"https://wttr.in/{urllib.parse.quote(city)}?format=j1", timeout=5).json()
            curr = res["current_condition"][0]
            state["weather_data"].update({
                "temp": f"{curr['temp_F']}°F",
                "condition": curr["weatherDesc"][0]["value"],
                "humidity": f"{curr['humidity']}%",
                "wind": f"{curr['windspeedMiles']} mph"
            })
            apply_weather_atmospheric_theme()
        except Exception:
            pass
        time.sleep(300)

threading.Thread(target=update_weather_atmospheric_loop, daemon=True).start()

# ==========================================
# 🛠️ SYSTEM DIAGNOSTIC SEQUENCE
# ==========================================
def run_system_diagnostic_sequence():
    state["status"] = "RUNNING DIAGNOSTICS..."
    subsystems = ["Power Core Reactor", "Neural Comm-Link", "Repulsor Stabilizers", "Nanite Bio-Armor"]
    
    def worker():
        for sub in subsystems:
            state["system_alert"] = f"DIAGNOSTIC: CHECKING {sub.upper()}..."
            queue_speech(f"Verifying integrity of {sub}, Sir.")
            time.sleep(1.0)
        state["system_alert"] = f"SYS_INTEGRITY: 100% // ALL SUBSYSTEMS NOMINAL"
        queue_speech("All diagnostic checks passed with zero anomalies, Sir.")
        state["status"] = "ONLINE"

    threading.Thread(target=worker, daemon=True).start()

# ==========================================
# 🛑 INSTANT SPEECH INTERRUPTION ENGINE
# ==========================================
def stop_speech():
    state["interrupted"] = True
    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except Exception:
        pass
    while not speech_queue.empty():
        try:
            speech_queue.get_nowait()
            speech_queue.task_done()
        except queue.Empty:
            break
    state["is_talking"] = False
    state["status"] = "ONLINE"
    state["system_alert"] = "AUDIO INTERRUPTED // STANDING BY"

def tts_queue_worker():
    while True:
        text = speech_queue.get()
        if text is None:
            break
        if state["interrupted"]:
            speech_queue.task_done()
            continue

        state["is_talking"] = True
        state["ultron_reply"] = text
        state["interrupted"] = False
        
        trigger_floating_subtitle(text)

        temp_audio_file = f"jarvis_voice_{int(time.time() * 1000)}.mp3"
        current_voice = THEMES[state["current_theme"]].get("voice", "en-GB-RyanNeural")

        async def generate_speech():
            communicate = edge_tts.Communicate(text, current_voice, rate="+0%", pitch="+0Hz")
            await communicate.save(temp_audio_file)

        try:
            asyncio.run(generate_speech())
            if not state["interrupted"]:
                pygame.mixer.music.load(temp_audio_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    if state["interrupted"]:
                        pygame.mixer.music.stop()
                        break
                    time.sleep(0.03)
            pygame.mixer.music.unload()
            if os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)
        except Exception:
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 155)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
                del engine
            except Exception:
                pass

        time.sleep(0.15)
        state["last_speech_time"] = time.time()
        state["is_talking"] = False
        speech_queue.task_done()

threading.Thread(target=tts_queue_worker, daemon=True).start()

def queue_speech(text):
    speech_queue.put(text)

# ==========================================
# ❌ CLOSE / DISMISS SCHEMATIC ENGINE
# ==========================================
def close_schematic():
    state["explanation_mode"] = False
    state["explanation_materials"] = []
    state["tech_tree_nodes"] = []
    state["explanation_image_tk"] = None
    state["is_liquid"] = False
    state["custom_blueprint"] = generate_procedural_wireframe("core")
    state["system_alert"] = f"SYS_INTEGRITY: 100% // {BUILD_SIGNATURE}"
    return "Schematic and tech tree matrix dismissed, Sir. Telemetry restored."

# ==========================================
# 🌐 THREAD-SAFE WEB REFERENCE IMAGE ENGINE
# ==========================================
def fetch_web_reference_image(keyword):
    try:
        clean_kw = re.sub(r"[^a-zA-Z0-9\s]", "", keyword).strip()
        search_term = urllib.parse.quote(clean_kw)
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original&titles={search_term}&redirects=1"
        headers = {"User-Agent": "JarvisSystemMatrix/10.0 (contact: admin@jarvis.ai)"}
        res = requests.get(wiki_url, headers=headers, timeout=4).json()
        pages = res.get("query", {}).get("pages", {})
        image_url = None
        for _, page in pages.items():
            if "original" in page:
                image_url = page["original"]["source"]
                break

        if not image_url:
            image_url = "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=500&auto=format&fit=crop&q=60"

        req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            raw_data = response.read()
            img = Image.open(io.BytesIO(raw_data)).convert("RGB")
            img = img.resize((260, 180), Image.Resampling.LANCZOS)
            
            # Safely create PhotoImage on the main Tkinter thread to prevent freezing
            app.after(0, lambda: set_safe_hud_image(img))
            return True
    except Exception as e:
        print(f"Image Fetch Notice: {e}")
        state["explanation_image_tk"] = None
        return False

def set_safe_hud_image(img):
    state["explanation_image_tk"] = ImageTk.PhotoImage(img)

# ==========================================
# 🧪 PERSISTENT TECH TREE & MATERIALS SYNTHESIZER
# ==========================================
def process_universal_query(user_query):
    cached_materials, cached_source, cached_blueprint = fetch_blueprint_db(user_query)
    if cached_materials:
        state["explanation_title"] = user_query[:22].upper()
        state["explanation_materials"] = cached_materials
        state["explanation_source"] = cached_source + " [RECALLED FROM VAULT]"
        if cached_blueprint:
            state["custom_blueprint"] = cached_blueprint
        state["explanation_mode"] = True
        state["is_expanded"] = True
        state["target_scale"] = 1.3  # Safe clamped expansion scale
        fetch_web_reference_image(user_query)
        queue_speech(f"Recalled blueprint and tech tree for {user_query} from persistent memory vault, Sir.")
        return

    state["status"] = "SYNTHESIZING TECH TREE..."
    state["explanation_mode"] = True
    state["is_expanded"] = True
    state["target_scale"] = 1.3

    def worker():
        prompt = (
            f"The user requests a comprehensive tech tree breakdown for: '{user_query}'.\n"
            "Provide exact measured amounts/components, hierarchical tech tree nodes (parent components and sub-components), indicate if it is a liquid/chemical, and cite the primary source.\n"
            "Respond ONLY with valid JSON matching this EXACT schema:\n"
            "{\n"
            '  "title": "EXACT TOPIC TITLE (max 22 chars)",\n'
            '  "is_liquid": true_or_false,\n'
            '  "materials": [\n'
            '    "Exact measured component/step 1",\n'
            '    "Exact measured component/step 2",\n'
            '    "Exact measured component/step 3",\n'
            '    "Exact measured component/step 4",\n'
            '    "Exact measured component/step 5"\n'
            '  ],\n'
            '  "tech_tree": [\n'
            '    {"node": "Root Core", "sub": "Sub-component A"},\n'
            '    {"node": "Sub-component A", "sub": "Refined Material X"},\n'
            '    {"node": "Root Core", "sub": "Sub-component B"}\n'
            '  ],\n'
            '  "blueprint_3d": {\n'
            '    "name": "BLUEPRINT NAME",\n'
            '    "nodes": [[x,y,z], ... (16 to 24 integer coordinates between -40 and 40)],\n'
            '    "edges": [[idx1, idx2], ... (16 to 32 connection indices)]\n'
            '  },\n'
            '  "source": "Primary authoritative source or field",\n'
            '  "spoken_summary": "Crisp 2-sentence explanation of how this functions or is prepared.",\n'
            '  "search_keyword": "A single clean search keyword to fetch an image"\n'
            "}"
        )
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.15,
                max_tokens=950,
            )
            raw = completion.choices[0].message.content.strip()
            raw = re.sub(r"^```json\s*", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"^```\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            data = json.loads(raw)
            title = data.get("title", user_query.upper())[:24]
            materials = [f"• {m.lstrip('•-* ')}" for m in data.get("materials", []) if m]
            source = data.get("source", "Global Scientific & Technical Database")
            is_liquid = data.get("is_liquid", False)
            bp_3d = data.get("blueprint_3d", generate_procedural_wireframe("sphere" if is_liquid else "core"))
            tree_nodes = data.get("tech_tree", [])

            state["explanation_title"] = title
            state["explanation_materials"] = materials
            state["tech_tree_nodes"] = tree_nodes
            state["explanation_source"] = source
            state["is_liquid"] = is_liquid
            state["custom_blueprint"] = bp_3d

            save_blueprint_db(user_query, materials, source, bp_3d)

            state["system_alert"] = f"TECH TREE DEPLOYED: {title}"
            search_kw = data.get("search_keyword", user_query)
            fetch_web_reference_image(search_kw)

            spoken_text = data.get("spoken_summary", f"The tech tree and component telemetry for {user_query} is rendered on your HUD, Sir.")
            queue_speech(spoken_text)

        except Exception as e:
            print(f"Universal Synthesis Error: {e}")
            state["explanation_title"] = user_query[:20].upper()
            state["explanation_materials"] = [
                f"• Primary Spec: {user_query[:22]}",
                "• Structural Integrity: Nominal",
                "• Material Analysis: Active",
                "• Operational Directive: Deployed"
            ]
            state["tech_tree_nodes"] = [{"node": user_query[:15], "sub": "Core Element"}]
            state["explanation_source"] = "Encyclopedic Archives"
            save_blueprint_db(user_query, state["explanation_materials"], state["explanation_source"], state["custom_blueprint"])
            fetch_web_reference_image(user_query)
            queue_speech(f"I have mapped the tech tree and components for {user_query} to your HUD, Sir.")
        finally:
            state["status"] = "ONLINE"

    threading.Thread(target=worker, daemon=True).start()

# ==========================================
# ⚡ ULTRON CODE SYNTHESIS ENGINE
# ==========================================
def synthesize_script(prompt_topic, language="Lua (Roblox)"):
    script_output_box.delete("1.0", "end")
    script_output_box.insert("1.0", f"// [ULTRON CORE] Initializing synthesis pipeline for: {prompt_topic}...\n// Compiling {language} code vectors...\n\n")
    script_status_label.configure(text=f"STATUS: COMPILING {language.upper()} CODE...", text_color="#ff1a35")
    
    def worker():
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are the ULTRON Autonomous Code Synthesis Engine. "
                            f"Write complete, production-ready, highly optimized {language} code for the user's prompt. "
                            "Output ONLY the pure, raw code. Do NOT wrap in conversational text. Include clean comments inside the code."
                        )
                    },
                    {"role": "user", "content": f"Generate {language} code for: {prompt_topic}"}
                ],
                temperature=0.1,
                max_tokens=2500,
            )
            code = completion.choices[0].message.content.strip()
            code = re.sub(r"^```[a-zA-Z]*\n", "", code)
            code = re.sub(r"\n```$", "", code)

            app.after(0, lambda: inject_script_into_ui(code, prompt_topic, language))
        except Exception as e:
            app.after(0, lambda: script_output_box.insert("end", f"\n[!] Compilation Error: {e}"))
            script_status_label.configure(text="STATUS: SYNTHESIS FAILED", text_color="#ff5555")

    threading.Thread(target=worker, daemon=True).start()

def inject_script_into_ui(code, prompt_topic, language):
    script_output_box.delete("1.0", "end")
    header_comment = f"# ==========================================\n# ⚡ ULTRON SYNTHESIS: {prompt_topic.upper()}\n# LANGUAGE: {language} | BUILD: {APP_VERSION}\n# ==========================================\n\n"
    script_output_box.insert("1.0", header_comment + code)
    script_status_label.configure(text=f"STATUS: COMPILED SUCCESSFULLY [{len(code.splitlines())} LINES]", text_color="#00ff88")
    
    clean_name = re.sub(r"[^a-zA-Z0-9]", "_", prompt_topic)[:20]
    ext = ".lua" if "lua" in language.lower() or "roblox" in prompt_topic.lower() else ".py"
    filename = f"ultron_{clean_name}_{int(time.time())}{ext}"
    filepath = os.path.join(SCRIPTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    
    queue_speech(f"Ultron script for {prompt_topic} synthesized and ready for copy.")

# ==========================================
# 🎮 SCREEN VISION & TACTICAL ADVISOR
# ==========================================
def analyze_screen_view(user_query=None, is_instant_advisor=False):
    if state["is_analyzing_vision"]:
        return
    state["is_analyzing_vision"] = True
    state["status"] = "ANALYZING DISPLAY FEED..."
    state["system_alert"] = "TACTICAL ADVISOR OPTICAL SCAN ENGAGED" if is_instant_advisor else "OPTICAL SCREEN TELEMETRY ENGAGED"

    def worker():
        try:
            screenshot = pyautogui.screenshot().convert("RGB")
            screenshot.thumbnail((720, 405), Image.Resampling.LANCZOS)
            
            buf = io.BytesIO()
            screenshot.save(buf, format="JPEG", quality=70, optimize=True)
            b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")
            data_url = f"data:image/jpeg;base64,{b64_img}"
            
            if is_instant_advisor:
                instruction = (
                    "You are JARVIS / ULTRON Tactical Game Advisor. Look at the screen right now. "
                    "Tell the user EXACTLY what they should do next, where to move, or how to win in 2 short, crisp, highly practical sentences."
                )
            else:
                instruction = (
                    f"The user says: '{user_query or 'What should I do here?'}'. "
                    "Analyze what is visible on this screen capture and provide crisp, tactical advice in 2 direct sentences."
                )

            candidate_models = [
                "llama-3.2-11b-vision-preview",
                "llama-3.2-90b-vision-preview"
            ]

            response_text = None
            last_err = None

            for m in candidate_models:
                try:
                    res = client.chat.completions.create(
                        model=m,
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"You are JARVIS. {instruction}"},
                                {"type": "image_url", "image_url": {"url": data_url}},
                            ],
                        }],
                        max_tokens=180,
                        temperature=0.2,
                    )
                    if res.choices and len(res.choices) > 0:
                        response_text = res.choices[0].message.content.strip()
                        break
                except Exception as inner_e:
                    last_err = inner_e
                    continue

            if response_text:
                queue_speech(response_text)
            else:
                raise last_err or Exception("All vision pipelines exhausted.")

        except Exception as e:
            print(f"[!] Screen Vision Error: {e}")
            queue_speech("I encountered an anomaly analyzing your screen display, Sir.")
        finally:
            state["is_analyzing_vision"] = False
            state["status"] = "ONLINE"
            state["system_alert"] = f"SYS_INTEGRITY: 100% // {BUILD_SIGNATURE}"

    threading.Thread(target=worker, daemon=True).start()

# ==========================================
# 🎮 CONTINUOUS ORBITAL MOUSE & ANTI-AFK
# ==========================================
def auto_clicker_loop():
    angle = 0.0
    last_action_time = time.time()
    while True:
        if state["auto_clicker_active"]:
            try:
                sw, sh = pyautogui.size()
                cx, cy = sw // 2, sh // 2
                target_x = cx + int(160 * math.cos(angle))
                target_y = cy + int(160 * math.sin(angle))
                pyautogui.moveTo(target_x, target_y, _pause=False)
                angle += 0.09
                if time.time() - last_action_time > 3.5:
                    pyautogui.click(_pause=False)
                    pyautogui.press("space", _pause=False)
                    last_action_time = time.time()
            except pyautogui.FailSafeException:
                toggle_auto_clicker(False)
            except Exception:
                pass
            time.sleep(0.015)
        else:
            angle = 0.0
            time.sleep(0.3)

threading.Thread(target=auto_clicker_loop, daemon=True).start()

def toggle_auto_clicker(enable=None):
    if enable is None:
        enable = not state["auto_clicker_active"]
    state["auto_clicker_active"] = enable
    if enable:
        state["system_alert"] = "MACRO ACTIVE // ORBITAL CURSOR & ANTI-AFK ENGAGED"
        auto_status_badge.configure(text="MACRO: RUNNING", fg_color="#006644", text_color="#00ff88")
        return "Autonomous gaming assistance activated. Orbital anti-AFK routines are online."
    else:
        state["system_alert"] = f"SYS_INTEGRITY: 100% // {BUILD_SIGNATURE}"
        auto_status_badge.configure(text="MACRO: STANDBY", fg_color="#1a1a24", text_color="#778899")
        return "Autonomous routines disengaged."

# ==========================================
# 💻 SYSTEM TELEMETRY & LIVE FEEDS
# ==========================================
def telemetry_monitor_loop():
    while True:
        try:
            state["cpu_usage"] = int(psutil.cpu_percent(interval=1))
            state["ram_usage"] = int(psutil.virtual_memory().percent)
            state["disk_usage"] = int(psutil.disk_usage("/").percent)
            state["gaming_fps"] = random.randint(158, 172)
            state["render_latency"] = round(random.uniform(3.4, 4.2), 1)
            state["network_ping"] = random.randint(14, 22)
            state["cleaned_ram_mb"] = random.randint(1200, 1800)
            state["nanite_integrity"] = round(random.uniform(99.4, 100.0), 1)
            state["unibeam_charge"] = round(min(100.0, state["unibeam_charge"] + 0.5), 1)
        except Exception:
            pass
        time.sleep(1)

threading.Thread(target=telemetry_monitor_loop, daemon=True).start()

def update_live_data_loop():
    while True:
        try:
            city = state["weather_data"]["city"]
            res = requests.get(f"[https://wttr.in/](https://wttr.in/){urllib.parse.quote(city)}?format=j1", timeout=5).json()
            curr = res["current_condition"][0]
            state["weather_data"].update({"temp": f"{curr['temp_F']}°F", "condition": curr["weatherDesc"][0]["value"], "humidity": f"{curr['humidity']}%", "wind": f"{curr['windspeedMiles']} mph"})
        except Exception:
            pass
        for symbol in ["AAPL", "NVDA", "TSLA", "MSFT", "SPY"]:
            try:
                t = yf.Ticker(symbol)
                price = round(t.fast_info.last_price, 2)
                prev = round(t.fast_info.previous_close, 2)
                pct = round(((price - prev) / prev) * 100, 2)
                sign = "+" if pct >= 0 else ""
                state["stock_data"][symbol] = {"price": f"${price:.2f}", "change": f"{sign}{pct}%"}
            except Exception:
                pass
        time.sleep(60)

threading.Thread(target=update_live_data_loop, daemon=True).start()

# ==========================================
# 🧠 INTENT PARSER & COMMAND ROUTER
# ==========================================
def is_close_schematic_command(cmd):
    return any(c in cmd for c in ["close schematic", "dismiss schematic", "clear display", "close synthesizer", "close breakdown", "reset hud", "hide materials"])

def is_screen_command(cmd):
    cues = [
        "watch my screen", "watch what i'm doing", "look at my screen", "look at what i'm doing",
        "look at my game", "scan my screen", "check my display", "see my screen", "view my screen",
        "help me in roblox", "what should i do on my screen", "what is on my screen", "read my screen", "check my screen"
    ]
    return any(c in cmd for c in cues)

def is_music_command(cmd):
    return (
        cmd.startswith("play music") or cmd.startswith("play song") or
        cmd.startswith("play track") or "play on youtube" in cmd or
        (cmd.startswith("play ") and "game" not in cmd and "auto" not in cmd)
    )

def is_universal_synthesis_command(cmd):
    triggers = [
        "how do i make", "how to make", "recipe for", "how do you make", "explain how",
        "materials for", "ingredients for", "how does a", "how does an", "how to build",
        "how do i build", "what do i need for", "how to craft", "how do i craft",
        "breakdown of", "how to forge", "how to bake", "how is a", "how are", "what is the formula for", "to make "
    ]
    return any(t in cmd for t in triggers) or ("web fluid" in cmd)

def is_scripting_command(cmd):
    return "scripting mode" in cmd or "open scripting" in cmd or "ultron mode" in cmd or "code studio" in cmd or "open script studio" in cmd

def handle_system_command(command_text):
    cmd = command_text.lower().strip()

    if cmd in ["stop", "jarvis stop", "shut up", "cancel", "be quiet", "stop talking", "halt"]:
        stop_speech()
        return None

    if is_close_schematic_command(cmd):
        return close_schematic()

    if "start focus session" in cmd or "start pomodoro" in cmd or "focus mode" in cmd:
        return start_focus_session(25)
    if "stop focus session" in cmd or "stop pomodoro" in cmd:
        return stop_focus_session()

    if cmd.startswith("open portal ") or cmd.startswith("launch portal "):
        portal_name = cmd.replace("open portal", "").replace("launch portal", "").strip()
        url = get_portal(portal_name)
        if url:
            webbrowser.open(url)
            return f"Opening portal to {portal_name}, Sir."
        else:
            return f"Portal {portal_name} not found in database, Sir."

    if "run diagnostic" in cmd or "system check" in cmd or "diagnostic check" in cmd:
        run_system_diagnostic_sequence()
        return "Initiating full system diagnostic sequence, Sir."

    if "what should i do" in cmd or "help me win" in cmd or "tactical advice" in cmd or "what do i do" in cmd:
        analyze_screen_view(is_instant_advisor=True)
        return "Analyzing current gameplay telemetry for immediate tactical maneuver, Sir."

    if "ultron protocol" in cmd or "engage ultron" in cmd or "master protocol" in cmd or "all in one" in cmd:
        set_proto("ULTRON")
        return "Ultron Apex Master Protocol online. All suit subsystems merged into master telemetry."

    if "combat protocol" in cmd or "war machine" in cmd or "gaming protocol" in cmd:
        set_proto("COMBAT")
        return "War Machine Combat & High-FPS Gaming matrix online."

    if "hulkbuster" in cmd or "heavy armor" in cmd or "turbo protocol" in cmd or "reduce lag" in cmd:
        set_proto("HULKBUSTER")
        return "Hulkbuster Heavy Armor and lag-reduction optimization routines active."

    if "stealth protocol" in cmd or "nightshade" in cmd:
        set_proto("STEALTH")
        return "Stealth Recon and cyber-anonymity protocol engaged."

    if "starboost protocol" in cmd or "deep space" in cmd:
        set_proto("STARBOOST")
        return "Starboost Deep Space orbital telemetry matrix online."

    if "mark 85" in cmd or "nanotech" in cmd:
        set_proto("MARK85")
        return "Mark 85 Nanotech Prime synthesis active."

    if "heartbreaker" in cmd or "artillery" in cmd or "unibeam" in cmd:
        set_proto("HEARTBREAKER")
        return "Heartbreaker Artillery Unibeam capacitor charged."

    if "overwatch protocol" in cmd or "standard protocol" in cmd:
        set_proto("OVERWATCH")
        return "Standard Overwatch Protocol restored."

    if is_scripting_command(cmd):
        switch_view("SCRIPTING")
        return "Ultron Code Synthesis Engine online. You may dictate code requests now, Sir."

    if "exit scripting mode" in cmd or "close scripting mode" in cmd or "exit ultron" in cmd or "return to overwatch" in cmd:
        switch_view("HUD")
        return "Returning to Overwatch HUD Matrix."

    if state["active_view"] == "SCRIPTING":
        if cmd.startswith("script ") or cmd.startswith("write ") or cmd.startswith("create ") or cmd.startswith("make "):
            topic = re.sub(r"^(script|write a script for|write code for|write|create|make)\s*", "", cmd)
            lang = script_lang_selector.get()
            synthesize_script(topic, language=lang)
            return f"Synthesizing {lang} code for {topic}."

    if is_screen_command(cmd):
        analyze_screen_view(user_query=command_text)
        return "Scanning your screen display telemetry now, Sir."

    if is_universal_synthesis_command(cmd):
        process_universal_query(command_text)
        return None

    if "what version" in cmd or "check version" in cmd or "current version" in cmd:
        return f"I am currently operating on core version {APP_VERSION}, build revision {BUILD_DATE}, Sir."

    if is_music_command(cmd):
        song = re.sub(r"^(play music|play song|play track|play on youtube|play)\s*", "", cmd).strip()
        if not song:
            song = "ACDC Back in Black"
        webbrowser.open(f"[https://www.youtube.com/results?search_query=](https://www.youtube.com/results?search_query=){urllib.parse.quote(song)}")
        return f"Streaming {song} on your primary audio channel, Sir."

    if "play a game for me" in cmd or "start auto clicker" in cmd or "anti afk" in cmd:
        return toggle_auto_clicker(True)

    if "stop playing for me" in cmd or "stop auto clicker" in cmd or "stop clicking" in cmd:
        return toggle_auto_clicker(False)

    if cmd.startswith("remember that") or cmd.startswith("store note"):
        note = re.sub(r"^(remember that|store note|save note)\s*", "", cmd).strip()
        save_memory_categorized("NOTES", note)
        return f"Saved to memory vault: {note}."

    if "what do you remember" in cmd or "check memory" in cmd:
        mems = fetch_memories_by_category("NOTES")
        return ("Stored records indicate: " + " | ".join(mems)) if mems else "The memory vault is currently clear."

    if "search" in cmd:
        query = cmd.replace("search for", "").replace("search up", "").replace("search", "").strip()
        if query:
            webbrowser.open(f"[https://www.google.com/search?q=](https://www.google.com/search?q=){urllib.parse.quote(query)}")
            return f"Searching Google for {query}."

    return None

def trigger_voice_listen_event():
    state["system_alert"] = "TACTICAL HOTKEY: FORCED VOICE LINK ENGAGED"
    play_suit_sound(THEMES[state["current_theme"]].get("sound_type", "crystal"))

def voice_listener_worker():
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 1.6

    with sr.Microphone() as source:
        state["status"] = "CALIBRATING"
        recognizer.adjust_for_ambient_noise(source, duration=1.0)
        state["status"] = "ONLINE"

        while True:
            try:
                state["status"] = "LISTENING"
                audio = recognizer.listen(source, timeout=4, phrase_time_limit=12)
                user_text = recognizer.recognize_google(audio).strip()
                state["user_transcript"] = user_text
                state["status"] = "PROCESSING"
            except (sr.WaitTimeoutError, sr.UnknownValueError):
                state["status"] = "ONLINE"
                continue
            except Exception:
                state["status"] = "ONLINE"
                continue

            if any(s in user_text.lower() for s in ["stop", "shut up", "halt", "cancel"]):
                stop_speech()
                continue

            action_reply = handle_system_command(user_text)
            if action_reply:
                queue_speech(action_reply)
            elif not state["interrupted"] and not state["explanation_mode"]:
                conversation_memory.append({"role": "user", "content": user_text})
                try:
                    state["status"] = "THINKING"
                    completion = client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=conversation_memory,
                    )
                    reply = completion.choices[0].message.content
                    conversation_memory.append({"role": "assistant", "content": reply})
                    queue_speech(reply)
                except Exception:
                    queue_speech("I encountered an issue processing that query, Sir.")

            state["status"] = "ONLINE"

threading.Thread(target=voice_listener_worker, daemon=True).start()

# ==========================================
# ⌨️ GLOBAL KEYBIND CONTROLLER (NUMBER KEYS 1-7)
# ==========================================
def execute_hotkey_action(action):
    if action == "VOICE_LISTEN":
        trigger_voice_listen_event()
    elif action == "SCREEN_SCAN":
        analyze_screen_view("Analyze what is currently active on my monitor.")
    elif action == "STOP_AUDIO":
        stop_speech()
    elif action == "ULTRON_STUDIO":
        target = "SCRIPTING" if state["active_view"] == "HUD" else "HUD"
        switch_view(target)
    elif action == "AUTO_CLICKER":
        msg = toggle_auto_clicker()
        queue_speech(msg)
    elif action == "DISMISS_SCHEMATIC":
        msg = close_schematic()
        queue_speech(msg)
    elif action == "TACTICAL_ADVICE":
        analyze_screen_view(is_instant_advisor=True)

def register_global_hotkeys():
    if not KEYBOARD_LIB_LOADED:
        return
    try:
        keyboard.unhook_all_hotkeys()
    except Exception:
        pass

    actions = ["VOICE_LISTEN", "SCREEN_SCAN", "STOP_AUDIO", "ULTRON_STUDIO", "AUTO_CLICKER", "DISMISS_SCHEMATIC", "TACTICAL_ADVICE"]
    for act in actions:
        hotkey_str = active_keybinds.get(act, "").strip()
        if hotkey_str:
            try:
                keyboard.add_hotkey(hotkey_str, lambda a=act: execute_hotkey_action(a), suppress=False)
            except Exception as err:
                print(f"[!] Global hotkey notice for {act}: {err}")

threading.Thread(target=register_global_hotkeys, daemon=True).start()

# ==========================================
# 📷 CAMERA & AR HAND WORKER (STABLE STICKY DRAG & DROP)
# ==========================================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.6, min_tracking_confidence=0.5)
mp_draw = mp.solutions.drawing_utils

try:
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        face_cascade = None
except Exception:
    face_cascade = None

cap = None
for cam_idx in [0, 1, 2]:
    temp_cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
    if temp_cap.isOpened():
        cap = temp_cap
        break

if not cap or not cap.isOpened():
    cap = cv2.VideoCapture(0)

def is_spiderman_gesture(hand_landmarks):
    lm = hand_landmarks.landmark
    return lm[8].y < lm[6].y and lm[20].y < lm[18].y and lm[12].y > lm[10].y and lm[16].y > lm[14].y

def is_palm_repulsor_gesture(hand_landmarks):
    lm = hand_landmarks.landmark
    return all(lm[tip].y < lm[tip - 2].y for tip in [4, 8, 12, 16, 20])

def is_fist_gesture(hand_landmarks):
    lm = hand_landmarks.landmark
    return (lm[8].y > lm[6].y and lm[12].y > lm[10].y and lm[16].y > lm[14].y and lm[20].y > lm[18].y)

def background_camera_worker():
    global last_spiderman_trigger
    frame_counter = 0
    while True:
        if not cap or not cap.isOpened():
            time.sleep(0.5)
            continue

        success, frame = cap.read()
        if not success or frame is None:
            time.sleep(0.06)
            continue

        frame = cv2.flip(frame, 1)
        state["latest_frame"] = frame.copy()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_counter += 1

        if face_cascade and frame_counter % 2 == 0:
            try:
                faces = face_cascade.detectMultiScale(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 1.2, 5, minSize=(60, 60))
                for (fx, fy, fw, fh) in faces:
                    col = (255, 245, 0) if state["current_theme"] == "OVERWATCH" else (0, 165, 255)
                    cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), col, 1)
                    cv2.putText(frame, "TARGET LOCK: SIR", (fx, fy - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, col, 1)
            except Exception:
                pass

        results = hands.process(rgb)
        num_hands = len(results.multi_hand_landmarks) if results.multi_hand_landmarks else 0
        curr_time = time.time()

        if num_hands > 0:
            state["hand_detected"] = True
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                if is_spiderman_gesture(hand_landmarks):
                    state["current_gesture"] = "🕷️ SPIDER-MAN GESTURE"
                    if (curr_time - last_spiderman_trigger) > COOLDOWN_SPIDERMAN:
                        state["is_expanded"] = not state["is_expanded"]
                        state["target_scale"] = 1.3 if state["is_expanded"] else 1.0  # Clamped safe scale
                        last_spiderman_trigger = curr_time
                elif is_palm_repulsor_gesture(hand_landmarks):
                    state["current_gesture"] = "⚡ REPULSOR PALM ACTIVE"
                    state["repulsor_active"] = True
                elif is_fist_gesture(hand_landmarks):
                    state["current_gesture"] = "✊ FIST GRAB [STICKY TETHER ACTIVE]"
                    state["is_fist"] = True
                else:
                    state["repulsor_active"] = False
                    state["is_fist"] = False

            if num_hands == 2:
                h1 = results.multi_hand_landmarks[0].landmark[0]
                h2 = results.multi_hand_landmarks[1].landmark[0]
                dist = math.hypot(h2.x - h1.x, h2.y - h1.y)

                if dist > 0.35:
                    state["is_expanded"] = True
                    state["target_scale"] = 1.3
                    state["current_gesture"] = "👐 GALAXY LOCKED OPEN"
            
            if state["is_expanded"]:
                state["target_scale"] = 1.3

            h0 = results.multi_hand_landmarks[0].landmark
            palm_x, palm_y = int(h0[9].x * frame.shape[1]), int(h0[9].y * frame.shape[0])
            state["cam_hand_pos"] = (palm_x, palm_y)

            cw = hud_canvas.winfo_width() if hud_canvas.winfo_width() > 100 else 930
            ch = hud_canvas.winfo_height() if hud_canvas.winfo_height() > 100 else 510
            canvas_palm_x, canvas_palm_y = int(h0[9].x * cw), int(h0[9].y * ch)
            state["hand_palm_center"] = [canvas_palm_x, canvas_palm_y]

            if state["is_fist"]:
                state["blueprint_target_pos"] = state["hand_palm_center"]

            ar_col = (255, 245, 0) if state["current_theme"] == "OVERWATCH" else (0, 165, 255)
            cv2.circle(frame, (palm_x, palm_y), 24, ar_col, 2)
            cv2.circle(frame, (palm_x, palm_y), 8, (255, 255, 255), -1)
            cv2.putText(frame, "AR HOLOGRAM ANCHOR", (palm_x - 55, palm_y - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.35, ar_col, 1)

            idx_x, idx_y, thumb_x, thumb_y = h0[8].x, h0[8].y, h0[4].x, h0[4].y
            state["laser_active"] = True
            state["laser_cursor"] = [int(idx_x * cw), int(idx_y * ch)]
            state["is_pinching"] = math.hypot(idx_x - thumb_x, idx_y - thumb_y) < 0.06

        else:
            state["hand_detected"] = False
            state["is_fist"] = False
            state["laser_active"] = False
            state["is_pinching"] = False
            state["repulsor_active"] = False
            state["cam_hand_pos"] = None
            state["current_gesture"] = "NO HAND DETECTED"
            if state["is_expanded"] or state["explanation_mode"]:
                state["target_scale"] = 1.3
            else:
                state["target_scale"] = 1.0

        img = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (260, 180))
        state["cam_display_image"] = ImageTk.PhotoImage(image=Image.fromarray(img))
        time.sleep(0.02)

threading.Thread(target=background_camera_worker, daemon=True).start()

# ==========================================
# 🖥️ HUD UI SETUP & WORKSPACE CONTAINERS
# ==========================================
ctk.set_appearance_mode("Dark")
app = ctk.CTk()
app.geometry("1340x920")
app.title(f"JARVIS NEURAL OVERWATCH // {BUILD_SIGNATURE}")
app.configure(fg_color="#010409")

def register_tkinter_keybinds():
    def _tk_press(act):
        execute_hotkey_action(act)

    for k in ["1", "2", "3", "4", "5", "6", "7"]:
        app.bind_all(k, lambda e, key=k: _tk_press(
            "VOICE_LISTEN" if key=="1" else
            "SCREEN_SCAN" if key=="2" else
            "STOP_AUDIO" if key=="3" else
            "ULTRON_STUDIO" if key=="4" else
            "AUTO_CLICKER" if key=="5" else
            "DISMISS_SCHEMATIC" if key=="6" else "TACTICAL_ADVICE"
        ))

register_tkinter_keybinds()

header = ctk.CTkFrame(app, fg_color="#030a14", corner_radius=10, border_width=1, border_color="#004d73", height=52)
header.pack(fill="x", padx=18, pady=(14, 6))

title_label = ctk.CTkLabel(
    header,
    text=f"▲ JARVIS OVERWATCH MATRIX // MARK-XI [{APP_VERSION}]",
    font=ctk.CTkFont(family="Consolas", size=15, weight="bold"),
    text_color="#00f5ff"
)
title_label.pack(side="left", padx=18)

alert_label = ctk.CTkLabel(header, text=state["system_alert"], font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color="#00aacc")
alert_label.pack(side="right", padx=18)

center_frame = ctk.CTkFrame(app, fg_color="transparent")
center_frame.pack(fill="both", expand=True, padx=18, pady=4)
center_frame.grid_rowconfigure(0, weight=1)
center_frame.grid_columnconfigure(0, weight=1)

# --- WORKSPACE 1: NORMAL HUD VIEW ---
hud_container = ctk.CTkFrame(center_frame, fg_color="transparent")
hud_container.grid(row=0, column=0, sticky="nsew")

canvas_frame = ctk.CTkFrame(hud_container, fg_color="#01060f", corner_radius=14, border_width=1, border_color="#00334d")
canvas_frame.pack(side="left", fill="both", expand=True)

hud_canvas = ctk.CTkCanvas(canvas_frame, width=930, height=510, bg="#01060f", highlightthickness=0)
hud_canvas.pack(fill="both", expand=True, padx=8, pady=8)

right_panel = ctk.CTkFrame(hud_container, width=320, fg_color="#030a14", corner_radius=12, border_width=1, border_color="#004d73")
right_panel.pack(side="right", fill="y", padx=(12, 0))

cam_heading = ctk.CTkLabel(right_panel, text="OPTICAL / VISUAL TELEMETRY", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color="#00e5ff")
cam_heading.pack(pady=(8, 2))

cam_view = ctk.CTkLabel(right_panel, text="", width=260, height=180, corner_radius=8)
cam_view.pack(padx=14, pady=2)

gesture_banner = ctk.CTkLabel(right_panel, text="GESTURE: STANDBY", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color="#00f5ff", fg_color="#021c2c", corner_radius=6, padx=8, pady=4)
gesture_banner.pack(pady=3, fill="x", padx=14)

status_box = ctk.CTkLabel(right_panel, text="STATUS: ONLINE", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), fg_color="#011824", text_color="#00f5ff", corner_radius=6, padx=10, pady=2)
status_box.pack(pady=2)

version_badge = ctk.CTkLabel(right_panel, text=f"CORE: {APP_VERSION}", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), fg_color="#002233", text_color="#00ddff", corner_radius=6, padx=10, pady=2)
version_badge.pack(pady=2)

auto_status_badge = ctk.CTkLabel(right_panel, text="MACRO: STANDBY", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), fg_color="#1a1a24", text_color="#778899", corner_radius=6, padx=10, pady=2)
auto_status_badge.pack(pady=2)

proto_container = ctk.CTkFrame(right_panel, fg_color="transparent")
proto_container.pack(fill="x", padx=10, pady=4)

def set_proto(theme_name):
    state["current_theme"] = theme_name
    apply_theme_styling()
    play_suit_sound(THEMES[theme_name].get("sound_type", "crystal"))
    update_topright_overlay()

proto_buttons = [
    ("OVERWATCH", "#004466"), ("COMBAT", "#660c18"), ("HULKBUSTER", "#802b00"), ("STEALTH", "#663b00"),
    ("STARBOOST", "#3c096c"), ("MARK85", "#7a6300"), ("HEARTBREAKER", "#004d3d"), ("ULTRON", "#4d000b")
]

for idx, (th_key, th_col) in enumerate(proto_buttons):
    row, col = divmod(idx, 4)
    btn = ctk.CTkButton(
        proto_container,
        text=th_key[:4],
        width=34,
        height=20,
        font=ctk.CTkFont(family="Consolas", size=8, weight="bold"),
        fg_color=th_col,
        command=lambda k=th_key: set_proto(k)
    )
    btn.grid(row=row, column=col, padx=2, pady=2)

btn_keybind_config = ctk.CTkButton(
    right_panel,
    text="⌨️ CONFIGURE KEYBINDS",
    font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
    fg_color="#005577",
    hover_color="#0077aa",
    text_color="#ffffff",
    height=26,
    command=lambda: open_keybind_modal()
)
btn_keybind_config.pack(fill="x", padx=14, pady=(4, 2))

btn_diagnostic = ctk.CTkButton(
    right_panel,
    text="🛡️ RUN SYSTEM DIAGNOSTIC",
    font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
    fg_color="#004d3d",
    hover_color="#008066",
    text_color="#ffffff",
    height=26,
    command=lambda: run_system_diagnostic_sequence()
)
btn_diagnostic.pack(fill="x", padx=14, pady=2)

btn_dismiss_schematic = ctk.CTkButton(
    right_panel,
    text="✖ DISMISS SCHEMATIC",
    font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
    fg_color="#00334d",
    hover_color="#005577",
    text_color="#00f5ff",
    height=26,
    command=lambda: close_schematic()
)
btn_dismiss_schematic.pack(fill="x", padx=14, pady=2)

btn_open_scripting = ctk.CTkButton(
    right_panel,
    text="⚡ ULTRON SCRIPT STUDIO",
    font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
    fg_color="#800014",
    hover_color="#ff1a35",
    text_color="#ffffff",
    height=26,
    command=lambda: switch_view("SCRIPTING")
)
btn_open_scripting.pack(fill="x", padx=14, pady=(2, 4))

# --- WORKSPACE 2: ULTRON SCRIPTING STUDIO VIEW ---
scripting_container = ctk.CTkFrame(center_frame, fg_color="#060001", corner_radius=14, border_width=2, border_color="#800014")
scripting_container.grid(row=0, column=0, sticky="nsew")

ultron_top_bar = ctk.CTkFrame(scripting_container, fg_color="#120104", corner_radius=8, height=45)
ultron_top_bar.pack(fill="x", padx=14, pady=(12, 6))

ultron_title = ctk.CTkLabel(
    ultron_top_bar,
    text="⚡ ULTRON CODE SYNTHESIS ENGINE // SCRIPT STUDIO",
    font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
    text_color="#ff1a35"
)
ultron_title.pack(side="left", padx=16)

script_status_label = ctk.CTkLabel(
    ultron_top_bar,
    text="STATUS: READY FOR DIRECTIVES",
    font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
    text_color="#ff7788"
)
script_status_label.pack(side="right", padx=16)

ultron_toolbar = ctk.CTkFrame(scripting_container, fg_color="transparent")
ultron_toolbar.pack(fill="x", padx=14, pady=4)

script_lang_label = ctk.CTkLabel(ultron_toolbar, text="LANGUAGE:", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color="#ff5566")
script_lang_label.pack(side="left", padx=(4, 6))

script_lang_selector = ctk.CTkOptionMenu(
    ultron_toolbar,
    values=["Lua (Roblox)", "Python", "JavaScript", "C++", "C#", "Batch / PowerShell"],
    fg_color="#330007",
    button_color="#66000e",
    text_color="#ffffff",
    font=ctk.CTkFont(family="Consolas", size=11),
    width=140
)
script_lang_selector.pack(side="left", padx=4)

script_prompt_input = ctk.CTkEntry(
    ultron_toolbar,
    placeholder_text="Enter script prompt (e.g. 'Roblox auto clicker script' or 'Python web scraper')...",
    font=ctk.CTkFont(family="Consolas", size=11),
    fg_color="#180206",
    border_color="#800014",
    text_color="#ffffff",
    width=450
)
script_prompt_input.pack(side="left", fill="x", expand=True, padx=8)
script_prompt_input.bind("<Return>", lambda event: synthesize_script(script_prompt_input.get(), script_lang_selector.get()))

btn_generate = ctk.CTkButton(
    ultron_toolbar,
    text="⚡ SYNTHESIZE",
    font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
    fg_color="#800014",
    hover_color="#ff1a35",
    width=110,
    command=lambda: synthesize_script(script_prompt_input.get(), script_lang_selector.get())
)
btn_generate.pack(side="left", padx=4)

btn_copy_script = ctk.CTkButton(
    ultron_toolbar,
    text="📋 COPY SCRIPT",
    font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
    fg_color="#006644",
    hover_color="#00aa66",
    width=110,
    command=lambda: copy_script_to_clipboard()
)
btn_copy_script.pack(side="left", padx=4)

btn_exit_studio = ctk.CTkButton(
    ultron_toolbar,
    text="◀ BACK TO HUD",
    font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
    fg_color="#22222b",
    hover_color="#444455",
    width=110,
    command=lambda: switch_view("HUD")
)
btn_exit_studio.pack(side="left", padx=4)

script_output_box = ctk.CTkTextbox(
    scripting_container,
    font=ctk.CTkFont(family="Consolas", size=12),
    fg_color="#0a0002",
    border_color="#4d000b",
    border_width=1,
    text_color="#ff99a8",
    wrap="none"
)
script_output_box.pack(fill="both", expand=True, padx=14, pady=(6, 14))
script_output_box.insert("1.0", (
    "# ==========================================\n"
    "# ⚡ ULTRON CODE SYNTHESIS ENGINE\n"
    "# Speak: 'Script a Roblox fly script' or type above and click SYNTHESIZE.\n"
    "# Click 'COPY SCRIPT' anytime to copy directly to your clipboard.\n"
    "# ==========================================\n"
))

hud_container.tkraise()

def copy_script_to_clipboard():
    code = script_output_box.get("1.0", "end-1c")
    if code.strip():
        app.clipboard_clear()
        app.clipboard_append(code)
        app.update()
        script_status_label.configure(text="STATUS: COPIED TO CLIPBOARD! ✔", text_color="#00ff88")
        queue_speech("Script copied to your clipboard, Sir.")

def switch_view(view_name):
    state["active_view"] = view_name
    if view_name == "SCRIPTING":
        scripting_container.tkraise()
        set_proto("ULTRON")
    else:
        hud_container.tkraise()
        set_proto("OVERWATCH")

# --- BOTTOM LOG DECK ---
log_container = ctk.CTkFrame(app, fg_color="transparent")
log_container.pack(fill="x", padx=18, pady=(8, 16))

user_card = ctk.CTkFrame(log_container, fg_color="#030a14", corner_radius=8, border_width=1, border_color="#002b3d")
user_card.pack(fill="x", pady=(0, 6))

user_tag = ctk.CTkLabel(user_card, text="YOU >", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color="#00aacc", anchor="w")
user_tag.pack(fill="x", padx=16, pady=(6, 0))

user_display = ctk.CTkLabel(user_card, text="Awaiting voice command...", font=ctk.CTkFont(family="Consolas", size=12), text_color="#99d6ea", anchor="w", justify="left", wraplength=1240)
user_display.pack(fill="x", padx=16, pady=(2, 8))

ai_card = ctk.CTkFrame(log_container, fg_color="#051122", corner_radius=8, border_width=1, border_color="#005577")
ai_card.pack(fill="x")

ai_tag = ctk.CTkLabel(ai_card, text=f"JARVIS [{APP_VERSION}] >", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color="#00f5ff", anchor="w")
ai_tag.pack(fill="x", padx=16, pady=(6, 0))

ultron_display = ctk.CTkLabel(ai_card, text=state["ultron_reply"], font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), text_color="#00f5ff", anchor="w", justify="left", wraplength=1240)
ultron_display.pack(fill="x", padx=16, pady=(2, 10))

def apply_theme_styling():
    t = THEMES[state["current_theme"]]
    app.configure(fg_color=t["bg_dark"])
    header.configure(fg_color=t["panel_bg"], border_color=t["border"])
    title_label.configure(text=f"▲ JARVIS OVERWATCH MATRIX // {t['name']}", text_color=t["primary"])
    alert_label.configure(text_color=t["secondary"])
    canvas_frame.configure(border_color=t["dim"])
    right_panel.configure(fg_color=t["panel_bg"], border_color=t["border"])
    cam_heading.configure(text_color=t["accent"])
    user_card.configure(fg_color=t["panel_bg"], border_color=t["dim"])
    user_tag.configure(text_color=t["secondary"])
    user_display.configure(text_color=t["text_user"])
    ai_card.configure(fg_color=t["card_bg"], border_color=t["border"])
    ai_tag.configure(text=f"JARVIS [{APP_VERSION}] >", text_color=t["primary"])
    ultron_display.configure(text=state["ultron_reply"], text_color=t["primary"])

# ==========================================
# 🌟 GAMING OVERLAYS
# ==========================================
screen_w, screen_h = pyautogui.size()
overlay_tr = ctk.CTkToplevel()
overlay_tr.geometry(f"280x90+{screen_w - 295}+15")
overlay_tr.overrideredirect(True)
overlay_tr.attributes("-topmost", True)
overlay_tr.attributes("-alpha", 0.90)
overlay_tr.configure(fg_color="#020813")

tr_box = ctk.CTkFrame(overlay_tr, fg_color="#041220", corner_radius=6, border_width=1, border_color="#005577")
tr_box.pack(fill="both", expand=True, padx=2, pady=2)

tr_title = ctk.CTkLabel(tr_box, text=f"JARVIS // {APP_VERSION}", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color="#00f5ff")
tr_title.pack(anchor="w", padx=8, pady=(4, 0))

tr_stats = ctk.CTkLabel(tr_box, text="SUIT: OVERWATCH // ALL NOMINAL", font=ctk.CTkFont(family="Consolas", size=9), text_color="#88ccee")
tr_stats.pack(anchor="w", padx=8, pady=(0, 2))

tr_wave_canvas = ctk.CTkCanvas(tr_box, width=260, height=22, bg="#041220", highlightthickness=0)
tr_wave_canvas.pack(padx=8, pady=(0, 4))

def update_topright_overlay():
    t = THEMES[state["current_theme"]]
    theme_name = state["current_theme"]
    
    if theme_name == "ULTRON":
        stat_line = f"APEX MASTER: {state['gaming_fps']}FPS | {state['cleaned_ram_mb']}MB | PING {state['network_ping']}ms"
    elif theme_name == "COMBAT":
        stat_line = f"{state['gaming_fps']} FPS | {state['render_latency']}ms | {state['network_ping']}ms PING"
    elif theme_name == "HULKBUSTER":
        stat_line = f"LAG OPTIMIZER ACTIVE | {state['cleaned_ram_mb']}MB PURGED"
    elif theme_name == "STEALTH":
        stat_line = "CYBER GHOST TUNNEL // 0dB RADAR"
    elif theme_name == "STARBOOST":
        stat_line = "ORBITAL SPEED: 7.82km/s // LEO"
    elif theme_name == "MARK85":
        stat_line = f"NANITE REGEN: {state['nanite_integrity']}% // ACTIVE"
    elif theme_name == "HEARTBREAKER":
        stat_line = f"UNIBEAM RT: {state['unibeam_charge']}% CHARGED"
    else:
        stat_line = f"CPU: {state['cpu_usage']}% | RAM: {state['ram_usage']}% | ONLINE"

    tr_title.configure(text=f"JARVIS // {theme_name} [{APP_VERSION}]", text_color=t["primary"])
    tr_stats.configure(text=stat_line, text_color=t["accent"])
    tr_box.configure(border_color=t["border"])

    tr_wave_canvas.delete("all")
    if state["is_talking"] or state["status"] == "LISTENING":
        amp = 8 if state["is_talking"] else 3
        col = t["primary"]
        for x in range(10, 250, 8):
            y = 11 + math.sin(x * 0.1 + time.time() * 10) * amp * random.uniform(0.6, 1.3)
            tr_wave_canvas.create_oval(x-1, y-1, x+1, y+1, fill=col, outline="")

    overlay_tr.after(100, update_topright_overlay)

overlay_tr.after(100, update_topright_overlay)

overlay_tl = ctk.CTkToplevel()
overlay_tl.geometry("380x85+15+15")
overlay_tl.overrideredirect(True)
overlay_tl.attributes("-topmost", True)
overlay_tl.attributes("-alpha", 0.0)
overlay_tl.configure(fg_color="#020813")

tl_box = ctk.CTkFrame(overlay_tl, fg_color="#041220", corner_radius=6, border_width=1, border_color="#00f5ff")
tl_box.pack(fill="both", expand=True, padx=2, pady=2)

tl_title = ctk.CTkLabel(tl_box, text=f"JARVIS [{APP_VERSION}] >", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color="#00f5ff")
tl_title.pack(anchor="w", padx=8, pady=(4, 0))

tl_content = ctk.CTkLabel(tl_box, text="", font=ctk.CTkFont(family="Consolas", size=10), text_color="#ffffff", justify="left", wraplength=360)
tl_content.pack(anchor="w", padx=8, pady=(0, 4))

subtitle_hide_timer = None

def trigger_floating_subtitle(message_text):
    global subtitle_hide_timer
    def _show():
        t = THEMES[state["current_theme"]]
        tl_title.configure(text=f"JARVIS [{state['current_theme']}] >", text_color=t["primary"])
        tl_content.configure(text=message_text[:140] + ("..." if len(message_text) > 140 else ""), text_color="#ffffff")
        tl_box.configure(border_color=t["primary"])
        overlay_tl.attributes("-alpha", 0.92)

    app.after(0, _show)
    if subtitle_hide_timer:
        app.after_cancel(subtitle_hide_timer)
    subtitle_hide_timer = app.after(8000, lambda: overlay_tl.attributes("-alpha", 0.0))

# ==========================================
# ⚙️ KEYBIND CONFIGURATION MODAL
# ==========================================
def open_keybind_modal():
    modal = ctk.CTkToplevel(app)
    modal.geometry("540x540")
    modal.title("TACTICAL KEYBIND MATRIX CONFIGURATION")
    modal.configure(fg_color="#020813")
    modal.grab_set()
    modal.resizable(False, False)

    lbl_head = ctk.CTkLabel(
        modal,
        text="⌨️ TACTICAL NUMBER KEYBIND CONFIGURATION",
        font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
        text_color="#00f5ff"
    )
    lbl_head.pack(pady=(16, 8))

    lbl_sub = ctk.CTkLabel(
        modal,
        text="Assign number keys (e.g. '1', '2', '3', '4', '5', '6', '7').",
        font=ctk.CTkFont(family="Consolas", size=10),
        text_color="#7799aa"
    )
    lbl_sub.pack(pady=(0, 10))

    entries = {}
    rows_frame = ctk.CTkFrame(modal, fg_color="#041220", corner_radius=10, border_width=1, border_color="#004d73")
    rows_frame.pack(fill="both", expand=True, padx=20, pady=8)

    action_labels = [
        ("VOICE_LISTEN", "Voice Listen Link [Default: 1]:"),
        ("SCREEN_SCAN", "Screen Vision Telemetry [Default: 2]:"),
        ("STOP_AUDIO", "Instant Mute / Halt [Default: 3]:"),
        ("ULTRON_STUDIO", "Toggle Ultron Studio [Default: 4]:"),
        ("AUTO_CLICKER", "Toggle Gaming Anti-AFK [Default: 5]:"),
        ("DISMISS_SCHEMATIC", "Dismiss Schematics [Default: 6]:"),
        ("TACTICAL_ADVICE", "Instant Tactical Advice [Default: 7]:"),
    ]

    for idx, (act_key, act_name) in enumerate(action_labels):
        r_f = ctk.CTkFrame(rows_frame, fg_color="transparent")
        r_f.pack(fill="x", padx=14, pady=5)

        lbl = ctk.CTkLabel(r_f, text=act_name, font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color="#a0e6ff", width=280, anchor="w")
        lbl.pack(side="left")

        ent = ctk.CTkEntry(r_f, font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), fg_color="#01070f", border_color="#005577", text_color="#00f5ff", width=140)
        ent.insert(0, active_keybinds.get(act_key, ""))
        ent.pack(side="right")
        entries[act_key] = ent

    def save_and_close():
        for act_key, ent_widget in entries.items():
            new_val = ent_widget.get().strip().lower()
            if new_val:
                active_keybinds[act_key] = new_val
                save_keybind_db(act_key, new_val)
        register_global_hotkeys()
        modal.destroy()
        queue_speech("Number hotkeys calibrated and updated, Sir.")

    btn_save = ctk.CTkButton(
        modal,
        text="💾 SAVE & ENGAGE HOTKEYS",
        font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
        fg_color="#006644",
        hover_color="#009966",
        height=32,
        command=save_and_close
    )
    btn_save.pack(fill="x", padx=20, pady=(6, 16))

# ==========================================
# 🌌 3D PARTICLES GALAXY
# ==========================================
NUM_PARTICLES = 45
particles = []
for _ in range(NUM_PARTICLES):
    theta, phi, r_val = random.uniform(0, math.pi * 2), random.uniform(-math.pi / 2, math.pi / 2), random.uniform(35, 120)
    particles.append({
        "x": r_val * math.cos(phi) * math.cos(theta), "y": r_val * math.sin(phi), "z": r_val * math.cos(phi) * math.sin(theta),
        "vx": random.uniform(-0.35, 0.35), "vy": random.uniform(-0.35, 0.35), "vz": random.uniform(-0.35, 0.35),
    })

rot_x, rot_y = 0.0, 0.0

# ==========================================
# 🧪 CENTER CANVAS: 3D BLUEPRINT & LIQUID FLASK
# ==========================================
def draw_animated_liquid_flask(canvas, bx, by, t):
    canvas.create_polygon(
        bx - 18, by - 65, bx + 18, by - 65,
        bx + 18, by - 35, bx + 55, by + 45,
        bx - 55, by + 45, bx - 18, by - 35,
        outline=t["primary"], fill="#021424", width=2
    )
    canvas.create_oval(bx - 18, by - 68, bx + 18, by - 62, outline=t["accent"], width=2)
    canvas.create_oval(bx - 52, by + 35, bx + 52, by + 50, outline=t["dim"], width=1)

    fluid_top = by + 45 - int(75 * state["liquid_fill"])
    wave_offset = math.sin(time.time() * 4) * 3
    canvas.create_polygon(
        bx - 42, fluid_top + wave_offset, bx + 42, fluid_top - wave_offset,
        bx + 52, by + 42, bx - 52, by + 42,
        fill="#005577", outline=t["accent"], width=1
    )

    for b in state["liquid_bubbles"]:
        b["y"] -= b["s"]
        if b["y"] < fluid_top + 10:
            b["y"] = by + 40
            b["x"] = random.randint(-35, 35)
        
        bub_x = bx + b["x"] + math.sin(time.time() * 3 + b["y"]) * 2
        bub_y = b["y"]
        canvas.create_oval(bub_x - b["r"], bub_y - b["r"], bub_x + b["r"], bub_y + b["r"], outline="#ffffff", fill=t["accent"], width=1)

    canvas.create_text(bx, by - 80, text=f"[ FLUID MATRIX: {state['explanation_title']} ]", fill=t["primary"], font=("Consolas", 8, "bold"))
    canvas.create_text(bx, by + 65, text=f"VOLUME: 265ml // STABILITY: 99.4%", fill=t["secondary"], font=("Consolas", 7, "bold"))

def draw_center_3d_blueprint(canvas, bx, by, rx, ry, t):
    bp = state["custom_blueprint"]
    b_scale = state["blueprint_scale"]
    b_name = bp.get("name", "SCHEMATIC CORE")
    nodes = bp.get("nodes", [])
    edges = bp.get("edges", [])

    r_inner = int(95 * b_scale)
    r_outer = int(112 * b_scale)

    canvas.create_oval(bx - r_outer - 4, by - r_outer - 4, bx + r_outer + 4, by + r_outer + 4, outline=t["dim"], width=2)
    canvas.create_oval(bx - r_inner, by - r_inner, bx + r_inner, by + r_inner, outline=t["dim"], width=1, dash=(4, 4))
    canvas.create_oval(bx - r_outer, by - r_outer, bx + r_outer, by + r_outer, outline=t["secondary"], width=1)

    projected = []
    for v in nodes:
        x, y, z = v[0] * b_scale, v[1] * b_scale, (v[2] * b_scale if len(v) > 2 else 0)
        x1 = x * math.cos(ry) - z * math.sin(ry)
        z1 = x * math.sin(ry) + z * math.cos(ry)
        y1 = y * math.cos(rx) - z1 * math.sin(rx)
        z2 = y * math.sin(rx) + z1 * math.cos(rx)
        projected.append((bx + int(x1), by + int(y1), z2))

    for edge in edges:
        if len(edge) >= 2 and edge[0] < len(projected) and edge[1] < len(projected):
            p1, p2 = projected[edge[0]], projected[edge[1]]
            line_col = t["primary"] if (p1[2] + p2[2]) / 2 > 0 else t["dim"]
            canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=line_col, width=1)

    for sx, sy, z in projected:
        canvas.create_oval(sx - 2, sy - 2, sx + 2, sy + 2, fill="#ffffff" if z > 15 else t["accent"], outline="")

    canvas.create_text(bx, by - r_outer - 16, text=f"[ SCHEMATIC: {b_name} ]", fill=t["primary"], font=("Consolas", 8, "bold"))
    canvas.create_text(bx, by + r_outer + 16, text="ROTATING WIREFRAME CORE", fill=t["secondary"], font=("Consolas", 7, "bold"))

# ==========================================
# 🎨 HUD RENDERING & GAUGES
# ==========================================
def draw_telemetry_gauges(canvas, w, h, t):
    gx, gy, r = w - 110, h - 85, 28
    canvas.create_arc(gx - 80 - r, gy - r, gx - 80 + r, gy + r, start=0, extent=359, outline=t["dim"], width=4, style="arc")
    canvas.create_arc(gx - 80 - r, gy - r, gx - 80 + r, gy + r, start=90, extent=-int((state["cpu_usage"] / 100) * 359), outline=t["primary"], width=4, style="arc")
    canvas.create_text(gx - 80, gy - 6, text=f"{state['cpu_usage']}%", fill=t["primary"], font=("Consolas", 8, "bold"))
    canvas.create_text(gx - 80, gy + 8, text="CPU", fill=t["secondary"], font=("Consolas", 7))

    canvas.create_arc(gx - r, gy - r, gx + r, gy + r, start=0, extent=359, outline=t["dim"], width=4, style="arc")
    canvas.create_arc(gx - r, gy - r, gx + r, gy + r, start=90, extent=-int((state["ram_usage"] / 100) * 359), outline=t["accent"], width=4, style="arc")
    canvas.create_text(gx, gy - 6, text=f"{state['ram_usage']}%", fill=t["accent"], font=("Consolas", 8, "bold"))
    canvas.create_text(gx, gy + 8, text="RAM", fill=t["secondary"], font=("Consolas", 7))

    if state["auto_clicker_active"]:
        canvas.create_oval(gx + 40, gy - 16, gx + 60, gy + 4, fill="#00ff88", outline="#ffffff", width=1)
        canvas.create_text(gx + 50, gy + 14, text="ORBIT ON", fill="#00ff88", font=("Consolas", 7, "bold"))

def draw_repulsor_ring(canvas, cx, cy, t):
    if state["repulsor_active"]:
        state["repulsor_charge"] = min(1.0, state["repulsor_charge"] + 0.08)
        rc = int(45 * state["repulsor_charge"])
        canvas.create_oval(cx - rc, cy - rc, cx + rc, cy + rc, outline="#ffffff", width=3)
        canvas.create_oval(cx - rc - 10, cy - rc - 10, cx + rc + 10, cy + rc + 10, outline=t["primary"], width=2)
        canvas.create_text(cx, cy - rc - 18, text="[ REPULSOR CHARGING ]", fill=t["primary"], font=("Consolas", 8, "bold"))
    else:
        state["repulsor_charge"] = max(0.0, state["repulsor_charge"] - 0.1)

def draw_audio_waveform(canvas, w, h, t):
    if not state["is_talking"] and state["status"] != "LISTENING":
        return
    wave_y = h - 22
    points = []
    amp = 18 if state["is_talking"] else 8
    col = t["primary"] if state["is_talking"] else t["secondary"]
    for x in range(30, w - 30, 10):
        points.append((x, wave_y + math.sin(x * 0.05 + time.time() * 8) * amp * random.uniform(0.6, 1.2)))
    for i in range(len(points) - 1):
        canvas.create_line(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1], fill=col, width=2)

def update_hud():
    global rot_x, rot_y
    if state["active_view"] == "HUD":
        hud_canvas.delete("all")
        w = hud_canvas.winfo_width() if hud_canvas.winfo_width() > 100 else 930
        h = hud_canvas.winfo_height() if hud_canvas.winfo_height() > 100 else 510
        cx, cy = w / 2, h / 2
        t = THEMES[state["current_theme"]]

        # Strict scale clamping to prevent canvas matrix crashes
        state["current_scale"] += (state["target_scale"] - state["current_scale"]) * 0.08
        state["current_scale"] = max(0.5, min(state["current_scale"], 1.3))
        scale = state["current_scale"]

        tx, ty = state["blueprint_target_pos"]
        state["blueprint_pos"][0] += int((tx - state["blueprint_pos"][0]) * 0.15)
        state["blueprint_pos"][1] += int((ty - state["blueprint_pos"][1]) * 0.15)
        bx, by = state["blueprint_pos"]

        rot_y += 0.05 if state["is_talking"] else 0.02
        rot_x += 0.02 if state["is_talking"] else 0.01

        projected = []
        fov = 340
        galaxy_center_x = cx if scale > 1.2 else cx + 180
        for p in particles:
            jitter = random.uniform(-1.5, 1.5) if state["is_talking"] else 0.0
            p["x"] += p["vx"] + jitter
            p["y"] += p["vy"] + jitter
            p["z"] += p["vz"]
            if p["x"] ** 2 + p["y"] ** 2 + p["z"] ** 2 > (70 * scale) ** 2:
                p["vx"] *= -1
                p["vy"] *= -1
                p["vz"] *= -1
            x1 = p["x"] * math.cos(rot_y) - p["z"] * math.sin(rot_y)
            z1 = p["x"] * math.sin(rot_y) + p["z"] * math.cos(rot_y)
            y1 = p["y"] * math.cos(rot_x) - z1 * math.sin(rot_x)
            factor = fov / max(1.0, (fov + z1 + 200))
            projected.append((galaxy_center_x + int(x1 * factor * 1.4), cy + int(y1 * factor * 1.4), z1))

        max_link = int(45 + 20 * scale)
        for i in range(len(projected)):
            for j in range(i + 1, len(projected)):
                d = math.hypot(projected[j][0] - projected[i][0], projected[j][1] - projected[i][1])
                if d < max_link:
                    col = t["primary"] if d < max_link * 0.4 else t["dim"]
                    hud_canvas.create_line(projected[i][0], projected[i][1], projected[j][0], projected[j][1], fill=col, width=1)

        for sx, sy, z in projected:
            node_r = 3 if z > 0 else 2
            col = "#ffffff" if (state["is_talking"] and random.random() < 0.15) else ("#ffffff" if z > 40 else t["primary"])
            hud_canvas.create_oval(sx - node_r, sy - node_r, sx + node_r, sy + node_r, fill=col, outline="")

        if scale < 1.3 or state["explanation_mode"]:
            if state["is_liquid"]:
                draw_animated_liquid_flask(hud_canvas, bx, by, t)
            else:
                draw_center_3d_blueprint(hud_canvas, bx, by, rot_x, rot_y, t)

        draw_repulsor_ring(hud_canvas, cx, cy, t)
        draw_telemetry_gauges(hud_canvas, w, h, t)
        draw_audio_waveform(hud_canvas, w, h, t)

        if state["is_fist"]:
            hud_canvas.create_oval(bx - 35, by - 35, bx + 35, by + 35, outline="#00ff88", width=1, dash=(3, 3))
            hud_canvas.create_text(bx, by + 85, text="[ FIST GRIP: STICKY TETHER ACTIVE ]", fill="#00ff88", font=("Consolas", 7, "bold"))

    status_box.configure(text=f"STATUS: {state['status']}", fg_color=t["panel_bg"], text_color=t["primary"])
    alert_label.configure(text=state["system_alert"], text_color=t["secondary"])
    user_display.configure(text=state["user_transcript"])
    ultron_display.configure(text=state["ultron_reply"])
    gesture_banner.configure(text=state["current_gesture"])

    app.after(33, update_hud)

def update_camera_display():
    if state["explanation_mode"] and state["explanation_image_tk"] is not None:
        cam_heading.configure(text="WEB VISUAL SCHEMATIC")
        cam_view.configure(image=state["explanation_image_tk"])
    elif state["cam_display_image"] is not None:
        cam_heading.configure(text="OPTICAL SENSOR FEED")
        cam_view.configure(image=state["cam_display_image"])
    app.after(33, update_camera_display)

# ==========================================
# 🚀 SYSTEM BOOT (VERSION 10.0)
# ==========================================
apply_theme_styling()
update_hud()
update_camera_display()

app.mainloop()
if cap and cap.isOpened():
    cap.release()