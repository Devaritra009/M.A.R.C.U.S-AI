"""
Autonomous Messaging Assistant & Dating Wingman for MARCUS.

Operates directly on native desktop applications and browsers (WhatsApp, Instagram,
Facebook Messenger) without requiring any official API tokens.

Capabilities:
- Autonomous chat loop: Runs in the background, continuously monitoring incoming messages
  and replying on the user's behalf until explicitly instructed to stop.
- Multilingual dating & messaging wingman: Fluent in English, Bengali (বাংলা & Benglish),
  and Hindi (हिंदी & Hinglish).
- Charismatic persona: Delivers witty pickup lines, heartfelt compliments, playful banter,
  and engaging conversation starters tailored to the context and language.
- Multimodal screen inspection: Observes chat windows via screen capture and Gemini vision
  to detect incoming messages and read context accurately.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import platform
import random
import re
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# Ensure standard streams survive non-UTF8 code pages on Windows
for _stream in ("stdout", "stderr"):
    try:
        _s = getattr(sys, _stream, None)
        if _s is not None and hasattr(_s, "reconfigure"):
            _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except Exception:
        try:
            safe = [str(a).encode("ascii", "replace").decode("ascii") for a in args]
            print(*safe, **kwargs)
        except Exception:
            pass


def _safe_log(player, text: str):
    if player and hasattr(player, "write_log"):
        try:
            player.write_log(text)
        except Exception:
            try:
                player.write_log(text.encode("ascii", "replace").decode("ascii"))
            except Exception:
                pass


# Automation dependencies
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

from core import gemini
from google.genai import types as gtypes

try:
    from actions.screen_processor import _capture_screen
except ImportError:
    _capture_screen = None

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"

# ── Authentic Multilingual Dating & Pickup Lines Knowledge Base ───────────────

DATING_LINES = {
    "english": {
        "pickup_lines": [
            "Are you a keyboard? Because you're definitely my type.",
            "Do you believe in love at first text, or should I message you again?",
            "I was having a pretty regular day until your name popped up on my screen.",
            "Are you a magician? Because whenever you text, everyone else disappears.",
            "I'm usually pretty focused, but you make being distracted way too easy.",
            "Is it hot in here, or is it just the vibe you bring to this chat?",
        ],
        "compliments": [
            "You have this effortless charm about you that is impossible to ignore.",
            "Your smile could honestly brighten anyone's worst day.",
            "You have great taste and an even better sense of humor.",
            "Talking to you is easily the best part of my day today.",
            "There's something wonderfully magnetic about the way you express yourself.",
        ],
        "banter": [
            "Careful now, you're dangerously close to making me smile at my phone in public.",
            "I have a confession: I checked my phone five times waiting for your reply.",
            "On a scale of 1 to 10, how lucky am I to be talking to you right now?",
            "You're not allowed to be this witty and this cute at the same time, it's unfair.",
            "Wait, are you always this fun to text or did I just catch you on a good day?",
            "Haha okay, you definitely win points for that one.",
        ],
        "casual_chat": [
            "Haha no way, are you serious? Tell me what happened next!",
            "Honestly that sounds like quite an adventure. How did your day go after that?",
            "I was just thinking about something similar earlier today, what a coincidence!",
            "Haha I love that. What else have you been up to today?",
            "That's awesome! You seem to always have interesting stories.",
        ],
        "openers": [
            "Hey! I was just thinking about you and wanted to say hi. How's your day treating you?",
            "Quick question: what is the highlight of your week so far? (Aside from talking to me, of course).",
            "Hey there! Random thought popped into my head and I knew I had to tell you.",
            "Hey! Hope you're having an amazing day today.",
        ],
    },
    "bengali": {
        "pickup_lines": [
            "তোমার কি কোনো জাদুর শক্তি আছে? কারণ তোমার সাথে কথা বললেই সব চিন্তা গায়েব হয়ে যায়।",
            "চা যেমন আড্ডা ছাড়া জমে না, ঠিক তেমনই তোমার মিষ্টি কথা ছাড়া দিনটা জমে না।",
            "Benglish: Tumi ki jadu jano? Karon tomar sathe kotha bolle shob tension ekdom vanish hoye jay!",
            "Benglish: Cha-er sathe jemon biscuit chhara chole na, thik temoni tomar sweet kotha chhara amar din chole na.",
        ],
        "compliments": [
            "তোমার মিষ্টি হাসিটা সত্যি অসম্ভব সুন্দর, মন ভালো করে দেয়।",
            "তুমি এত সুন্দর ও সাবলীলভাবে কথা বলো, মনে হয় সারাদিন শুধু তোমার কথাই শুনি।",
            "Benglish: Tomar hasi ta shotti oshadharon, jekono kharap din keo special banaye dey.",
            "Benglish: Tomar moddhe ekta shobar theke alada charm ache, jeta ignore kora oshombhob.",
            "Benglish: Tomar moto eto sweet ar funny manush dekha shotti ekhon khub durlabh.",
        ],
        "banter": [
            "Benglish: Eto sweet kotha bole amake distract korar plan ache naki?",
            "Benglish: Erom bhabe kotha bolle kintu ami protidin tomar inbox-e chole ashbo!",
            "Benglish: Shotti bolcho, naki shudhu amake impress korar chesta cholche?",
            "Benglish: Erom smart uttor deowa kotha theke shikhle bolo toh?",
            "Benglish: Tomar sathe kotha bolle time je kothaye chole jay bujhte e pari na!",
        ],
        "casual_chat": [
            "Benglish: Haha darun byapar! Tarpor bolo, ajker din ta kemon katlo?",
            "Benglish: Shotti bolcho? Ami bhablam tumi hoyto busy acho.",
            "Benglish: Arre wah, ei jinish ta amar o khub pochondo!",
            "Benglish: Hahaha ekdom thik bolecho, amar o majhe majhe erom mone hoy.",
            "Benglish: Besh bhalo! Ar ki korcho bolo ekhon?",
        ],
        "openers": [
            "Hey! Kemon acho? Ajker din ta kemon katche tomar?",
            "Eto shundor shondhey te bhablam tomar khoj niye dekhi, kemon acho?",
            "Kemon cholche shob? Kono bhalo khobor ache naki?",
            "Hey! Kemon katlo ajker din ta?",
        ],
    },
    "hindi": {
        "pickup_lines": [
            "क्या आप जादूगर हैं? क्योंकि जब भी आपका मैसेज आता है, बाकी सब गायब हो जाता है।",
            "आपकी मुस्कान में वो बात है जो किसी भी आम दिन को बेहद खास बना दे।",
            "Hinglish: Kya aap doctor ho? Kyunki aapka message aate hi meri saari tiredness gayab ho gayi!",
            "Hinglish: Aapki smile itni pyaari hai ki koi bhi bina shart apna dil haar baithe.",
        ],
        "compliments": [
            "आपकी बातें दिल को छू जाती हैं, आपसे बात करके बहुत सुकून मिलता है।",
            "Hinglish: Aapki smile sach mein bahut pyari hai, din ban gaya dekh kar.",
            "Hinglish: Aapke baat karne ka andaaz itna natural aur charming hai ki baat karte rehne ka man karta hai.",
            "Hinglish: Aap jitne acche dikhte ho, aapka nature usse bhi kahin zyada pyara hai.",
        ],
        "banter": [
            "Hinglish: Aise hi meethi baatein karte ho ya aaj mujh par extra meharbaan ho?",
            "Hinglish: Sambhal kar baat karo, kahin mujhe aapse roz baat karne ki aadat na pad jaaye!",
            "Hinglish: Sach mein itne sweet ho ya phir mujhe distract karne ka koi hidden plan hai?",
            "Hinglish: Aise smart jawab kahan se laate ho aap?",
            "Hinglish: Aapki baaton mein ek alag hi vibe hai, time ka pata hi nahi chalta!",
        ],
        "casual_chat": [
            "Hinglish: Haha sach mein? Yeh toh kaafi interesting hai, aur batao!",
            "Hinglish: Arre waah, mujhe laga sirf main hi aisa sochta hoon.",
            "Hinglish: Sahi hai yaar! Aur batao, aaj ka din kaisa raha aapka?",
            "Hinglish: Haha bilkul sahi kaha, agree karta hoon aapki baat se.",
            "Hinglish: Yeh toh bahut badhiya hai, aage kya hua phir?",
        ],
        "openers": [
            "Hey! Kaise ho aap? Kaisa chal raha hai aaj ka din?",
            "Bas aise hi aapka khayal aaya toh socha pooch loon, sab kaisa chal raha hai?",
            "Hey! Umeed hai aapka din utna hi pyara ja raha hoga jitna aapka smile hai!",
            "Hello! Aaj ka din kaisa raha aapka?",
        ],
    },
}

# ── Authentic Multilingual Normal / Casual Conversation Knowledge Base ───────

NORMAL_LINES = {
    "english": {
        "openers": [
            "Hey! How are you doing today?",
            "Hi! Hope your day is going well.",
            "Hey! Just checking in, how have you been?",
            "Hello! How's everything going with you?",
            "Hey there! What are you up to today?",
            "Hey! Long time, how have things been on your side?",
        ],
        "replies": [
            "That's great! Glad to hear that.",
            "Makes total sense. How did everything go after that?",
            "Nice! What else is new with you?",
            "Haha totally agree with you on that.",
            "That sounds really interesting, tell me more about it!",
            "I hear you! Sounds like quite a busy day.",
        ],
        "follow_ups": [
            "What have you been working on lately?",
            "Any plans for the rest of the day?",
            "Let me know when you're free to catch up!",
        ],
    },
    "bengali": {
        "openers": [
            "Hey! Kemon acho? Shob thikthak toh?",
            "Kemon cholche shob? Ajker din ta kemon katlo?",
            "Ki khobor bolo? Onek din por kotha hocche.",
            "Hello! Ki korcho ekhon? Bhablam ekbar khoj niye dekhi.",
            "Bhablam ekbar khoj niye dekhi kemon acho, shob bhalo toh?",
            "কেমন আছো? দিনকাল কেমন চলছে?",
            "কী খবর? সব ঠিকঠাক তো?",
        ],
        "replies": [
            "Besh bhalo! Shune bhalo laglo.",
            "Haa ekdom thik bolecho, shotti e taai.",
            "Arey wah, darun byapar toh!",
            "Haa bujhte perechi. Tarpor ar ki khobor?",
            "Haha thik kotha!",
            "হ্যাঁ একদম ঠিক বলেছো!",
            "বেশ ভালো, শুনে খুব ভালো লাগলো।",
        ],
        "follow_ups": [
            "Tarpor ar ki korcho ajke?",
            "Kaj-kormo kemon cholche?",
            "Shomoy pele pore abar kotha hobe.",
        ],
    },
    "hindi": {
        "openers": [
            "Hey! Kaise ho? Sab kaisa chal raha hai?",
            "Aur batao, kya chal raha hai aaj kal?",
            "Hello! Aaj ka din kaisa raha aapka?",
            "Hey! Kafi time ho gaya baat kiye, sab theek thaak?",
            "Bas aise hi dhyan aaya toh socha pooch loon, kaise ho?",
            "नमस्ते! कैसे हैं आप? सब ठीक चल रहा है?",
            "और बताओ, क्या हाल चाल सब बढ़िया?",
        ],
        "replies": [
            "Badhiya! Sun kar accha laga.",
            "Haan bilkul sahi kaha aapne.",
            "Arre waah, yeh toh bahut acchi baat hai!",
            "Haan samajh gaya main. Aur kya chal raha hai?",
            "Haha sahi baat hai!",
            "हाँ बिल्कुल सही कहा आपने!",
            "बढ़िया! सुनकर अच्छा लगा।",
        ],
        "follow_ups": [
            "Aur batao, aaj ka kya plan hai?",
            "Kaam / padhai kaisi chal rahi hai?",
            "Chalo theek hai, thodi der mein baat karte hain.",
        ],
    },
}


def _is_dating_mode(mode: str) -> bool:
    """Returns True only when the mode explicitly indicates dating/wingman/flirting."""
    if not mode:
        return False
    m = mode.strip().lower()
    return any(k in m for k in ("date", "dating", "wingman", "flirt", "romantic", "rizz", "crush"))


def _normalize_msg(text: str) -> str:
    """Normalizes message text for robust matching by stripping whitespace, punctuation, and emojis."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s\u0980-\u09FF\u0900-\u097F]", " ", text.lower())
    return " ".join(cleaned.split())


def _is_our_own_message(incoming: str, outgoing_history: list[str]) -> bool:
    """
    Determines if an incoming string is actually Marcus's own message.
    Uses exact match, normalized match, substring containment, and fuzzy SequenceMatcher.
    """
    if not incoming or not outgoing_history:
        return False

    norm_inc = _normalize_msg(incoming)
    if not norm_inc:
        return False

    for out in outgoing_history:
        if not out:
            continue
        norm_out = _normalize_msg(out)
        if not norm_out:
            continue

        # 1. Exact or normalized equality
        if incoming.strip() == out.strip() or norm_inc == norm_out:
            return True

        # 2. Substring inclusion (e.g. OCR or vision extracted part of our message)
        if len(norm_inc) >= 5 and (norm_inc in norm_out or norm_out in norm_inc):
            return True

        # 3. Fuzzy similarity matching (ratio >= 0.70)
        ratio = difflib.SequenceMatcher(None, norm_inc, norm_out).ratio()
        if ratio >= 0.70:
            return True

    return False


# ── Active Chat Session State ────────────────────────────────────────────────

@dataclass
class ChatSession:
    session_id: str
    platform: str
    contact: str
    mode: str
    language: str
    vibe: str
    stop_event: threading.Event = field(default_factory=threading.Event)
    worker_thread: Optional[threading.Thread] = None
    last_incoming_text: str = ""
    last_outgoing_text: str = ""
    outgoing_history: list[str] = field(default_factory=list)
    last_screen_hash: str = ""
    messages_exchanged: int = 0
    history: list[dict] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    last_action_time: float = field(default_factory=time.time)


class ChatManager:
    """Singleton managing active autonomous messaging threads."""

    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: dict[str, ChatSession] = {}

    def _make_key(self, platform_name: str, contact_name: str) -> str:
        return f"{platform_name.strip().lower()}:{contact_name.strip().lower()}"

    def get_session(self, platform_name: str, contact_name: str) -> Optional[ChatSession]:
        with self._lock:
            key = self._make_key(platform_name, contact_name)
            return self._sessions.get(key)

    def get_active_sessions(self) -> list[ChatSession]:
        with self._lock:
            return [s for s in self._sessions.values() if not s.stop_event.is_set()]

    def stop_session(self, platform_name: str = "", contact_name: str = "") -> list[str]:
        stopped = []
        with self._lock:
            for key, sess in list(self._sessions.items()):
                plat_match = not platform_name or sess.platform.lower() == platform_name.lower().strip()
                contact_match = not contact_name or sess.contact.lower() == contact_name.lower().strip()
                if plat_match and contact_match:
                    sess.stop_event.set()
                    stopped.append(f"{sess.contact} ({sess.platform}, {sess.messages_exchanged} msgs)")
                    del self._sessions[key]
        return stopped

    def stop_all(self) -> list[str]:
        stopped = []
        with self._lock:
            for key, sess in list(self._sessions.items()):
                sess.stop_event.set()
                stopped.append(f"{sess.contact} ({sess.platform})")
            self._sessions.clear()
        return stopped

    def register_session(self, session: ChatSession) -> None:
        with self._lock:
            key = self._make_key(session.platform, session.contact)
            if key in self._sessions:
                self._sessions[key].stop_event.set()
            self._sessions[key] = session


_CHAT_MANAGER = ChatManager()


# ── GUI Automation & App Control ─────────────────────────────────────────────

def _require_pyautogui():
    if not _PYAUTOGUI:
        raise RuntimeError("PyAutoGUI not installed. Run: pip install pyautogui")


def _paste_unicode_text(text: str) -> None:
    """Pasting via clipboard guarantees full Unicode support for Bengali & Hindi."""
    _require_pyautogui()
    paste_keys = ("command", "v") if _OS == "Darwin" else ("ctrl", "v")
    if _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.12)
        pyautogui.hotkey(*paste_keys)
        time.sleep(0.12)
    else:
        # Fallback character typing (may fail for complex Brahmic ligatures)
        pyautogui.write(text, interval=0.03)

_LAST_WINDOW_HWND = None

def _focus_window_by_title_substring(keywords: list[str]) -> bool:
    """Brings any window whose title matches one of the keywords to the foreground."""
    global _LAST_WINDOW_HWND
    if _OS != "Windows":
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        wnd_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        matched_hwnd = None

        def enum_cb(hwnd, lparam):
            nonlocal matched_hwnd
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if any(k.lower() in title for k in keywords):
                        matched_hwnd = hwnd
                        return False
            return True

        user32.EnumWindows(wnd_proc(enum_cb), 0)
        if matched_hwnd:
            _LAST_WINDOW_HWND = matched_hwnd
            user32.ShowWindow(matched_hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(matched_hwnd)
            time.sleep(0.5)
            return True
    except Exception as e:
        _safe_print(f"[ChatAssistant] Focus window failed: {e}")
    return False


def _click_chat_input_box(platform_name: str = "whatsapp") -> None:
    """
    Directly clicks inside the text input area at the bottom of the chat pane.
    Prevents focus from landing on the '+' / Attachment / Document button.
    """
    if _OS != "Windows":
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        class RECT(ctypes.Structure):
            _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]

        hwnd = _LAST_WINDOW_HWND or user32.GetForegroundWindow()
        if hwnd:
            rect = RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if w > 350 and h > 250:
                    # In WhatsApp & Instagram Desktop/Web, the chat input field is centered horizontally
                    # in the right chat pane (~65% width) and 45px up from the bottom edge.
                    # Clicking here focuses the text field directly and dismisses any attachment menu.
                    click_x = rect.left + int(w * 0.65)
                    click_y = rect.bottom - 45
                    pyautogui.click(click_x, click_y)
                    time.sleep(0.2)
    except Exception as e:
        _safe_print(f"[ChatAssistant] Click chat input error: {e}")


def _open_or_focus_whatsapp(contact: str) -> bool:
    """Focuses or launches WhatsApp desktop or web, searches for the contact, and opens chat."""
    _require_pyautogui()
    _safe_print(f"[ChatAssistant] Opening WhatsApp chat with '{contact}'...")

    # 1. Try to focus existing WhatsApp window
    focused = _focus_window_by_title_substring(["WhatsApp", "WhatsApp Web"])

    if not focused:
        # Launch Windows desktop app
        if _OS == "Windows":
            try:
                subprocess.Popen("start whatsapp:", shell=True)
                time.sleep(2.5)
                focused = _focus_window_by_title_substring(["WhatsApp"])
            except Exception:
                pass

        if not focused:
            # Fallback: Start Menu search
            pyautogui.press("win")
            time.sleep(0.5)
            _paste_unicode_text("WhatsApp")
            time.sleep(0.6)
            pyautogui.press("enter")
            time.sleep(3.0)
            focused = _focus_window_by_title_substring(["WhatsApp"])

        if not focused:
            # Fallback to WhatsApp Web
            webbrowser.open("https://web.whatsapp.com/")
            time.sleep(5.0)
            _focus_window_by_title_substring(["WhatsApp", "WhatsApp Web"])

    # 2. Search for the contact in WhatsApp (only if a specific contact name was given)
    is_generic = (not contact) or (contact.strip().lower() in ("active chat", "current", "this", "chat", "person", "opponent", "someone", "friend"))
    if not is_generic:
        time.sleep(0.8)
        search_keys = ("command", "f") if _OS == "Darwin" else ("ctrl", "f")
        pyautogui.hotkey(*search_keys)
        time.sleep(0.5)

        _paste_unicode_text(contact)
        time.sleep(1.0)
        pyautogui.press("enter")
        time.sleep(1.0)

    # 3. Focus message input directly without Escape/Tab to avoid opening attachment/document menu
    _click_chat_input_box("whatsapp")
    return True


def _open_or_focus_instagram(contact: str) -> bool:
    """Focuses or opens Instagram Direct inbox, searches for contact, and enters chat."""
    _require_pyautogui()
    _safe_print(f"[ChatAssistant] Opening Instagram direct with '{contact}'...")

    focused = _focus_window_by_title_substring(["Instagram", "Direct • Instagram"])
    if not focused:
        webbrowser.open("https://www.instagram.com/direct/inbox/")
        time.sleep(4.5)
        _focus_window_by_title_substring(["Instagram", "Direct"])

    is_generic = (not contact) or (contact.strip().lower() in ("active chat", "current", "this", "chat", "person", "opponent", "someone", "friend"))
    if not is_generic:
        time.sleep(1.0)
        search_keys = ("command", "f") if _OS == "Darwin" else ("ctrl", "f")
        pyautogui.hotkey(*search_keys)
        time.sleep(0.5)
        _paste_unicode_text(contact)
        time.sleep(1.2)
        pyautogui.press("down")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(1.0)

    _click_chat_input_box("instagram")
    return True


def _open_or_focus_messenger(contact: str) -> bool:
    """Focuses or opens Facebook Messenger."""
    _require_pyautogui()
    focused = _focus_window_by_title_substring(["Messenger", "Facebook"])
    if not focused:
        webbrowser.open("https://www.messenger.com/")
        time.sleep(4.0)

    is_generic = (not contact) or (contact.strip().lower() in ("active chat", "current", "this", "chat", "person", "opponent", "someone", "friend"))
    if not is_generic:
        time.sleep(0.8)
        search_keys = ("command", "f") if _OS == "Darwin" else ("ctrl", "f")
        pyautogui.hotkey(*search_keys)
        time.sleep(0.5)
        _paste_unicode_text(contact)
        time.sleep(1.0)
        pyautogui.press("down")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.8)

    _click_chat_input_box("messenger")
    return True


def _open_chat_target(platform_name: str, contact: str) -> bool:
    p = platform_name.lower().strip()
    if any(k in p for k in ("whatsapp", "wp", "wapp")):
        return _open_or_focus_whatsapp(contact)
    elif any(k in p for k in ("instagram", "ig", "insta")):
        return _open_or_focus_instagram(contact)
    elif any(k in p for k in ("messenger", "facebook", "fb")):
        return _open_or_focus_messenger(contact)
    else:
        return _open_or_focus_whatsapp(contact)


def _send_chat_message(message: str, platform_name: str = "whatsapp") -> bool:
    """Types and sends text in whatever chat window currently holds input focus."""
    _require_pyautogui()
    if not message.strip():
        return False
    # Ensure text box is focused before pasting
    _click_chat_input_box(platform_name)
    time.sleep(0.15)
    _paste_unicode_text(message)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.3)
    return True


# ── AI Dating & Conversation Generation Engine ───────────────

def _get_curated_line(language: str, line_type: str = "", mode: str = "normal") -> str:
    lang = language.lower().strip()
    is_dating = _is_dating_mode(mode)

    if is_dating:
        pack = DATING_LINES.get("english", {})
        if "bengali" in lang or "bangla" in lang:
            pack = DATING_LINES.get("bengali", {})
        elif "hindi" in lang or "hinglish" in lang:
            pack = DATING_LINES.get("hindi", {})
        default_type = "banter" if line_type != "pickup_lines" else "pickup_lines"
    else:
        pack = NORMAL_LINES.get("english", {})
        if "bengali" in lang or "bangla" in lang:
            pack = NORMAL_LINES.get("bengali", {})
        elif "hindi" in lang or "hinglish" in lang:
            pack = NORMAL_LINES.get("hindi", {})
        default_type = "openers"

    target_type = line_type if (line_type and line_type in pack) else default_type
    choices = pack.get(target_type) or pack.get(default_type) or pack.get("banter") or pack.get("casual_chat") or []
    if choices:
        return random.choice(choices)

    if is_dating:
        return "I was having a pretty regular day until your name popped up on my screen."
    return "Hey! How are you doing today?"


def _generate_chat_reply(
    contact: str,
    incoming_text: str,
    history: list[dict],
    mode: str,
    language: str,
    vibe: str,
    platform_name: str,
) -> str:
    """
    Generates an authentic, context-aware reply on behalf of the user.
    Strictly separates:
    - Normal Conversation Mode: Friendly, natural, polite, respectful everyday chat (ABSOLUTELY NO FLIRTING).
    - Dating Wingman Mode: Charismatic, witty, flirtatious banter, compliments, and pickup lines.
    """
    recent_history = history[-6:] if history else []
    hist_text = "\n".join(
        f"{m.get('sender', 'Speaker')}: {m.get('text', '')}" for m in recent_history
    )
    is_dating = _is_dating_mode(mode)
    lang_clean = language.lower().strip()

    if is_dating:
        role_desc = "the user's charming dating wingman and romantic messaging companion"
        mode_desc = (
            f"Mode: REALISTIC DATING & WINGMAN ({mode}). Natural, authentic chemistry between two people getting to know each other. "
            f"Balanced mix of everyday conversational chat, playful teasing, subtle charm, and occasional witty lines"
        )
        vibe_desc = (
            vibe or
            "Flow like a real, authentic modern dating text conversation. Sound genuinely interested, relaxed, witty, and subtly magnetic"
        )
        rules = """Realistic Dating & Wingman Rules:
1. Speak as the USER, not as an AI or assistant. Never mention AI, bots, or third parties.
2. BALANCE IS CRITICAL — DO NOT BE A NON-STOP PICKUP LINE BOT:
   - In real life, sending cheesy pickup lines in every text is a turn-off.
   - Most replies (~70%) should be natural, curious everyday conversation: react to what they said, share a funny relatable reaction, talk about your day, or ask an engaging follow-up question.
   - Add lighthearted charm and playful teasing (~20-25%): gentle banter, noticing a cute detail, laughing together.
   - Use bold catchy lines or pickup lines SPARINGLY (~5-10%): save them for rare, playful moments or initial icebreakers.
3. ADAPTIVE TO BOTH GENDERS:
   - Whether the user is a boy impressing a girl, or a girl impressing a boy: match their conversational wavelength, be confident, attentive, playful, and fun to talk to.
4. Keep the response natural, conversational, and punchy (1 to 2 sentences max). People text concisely in DMs.
5. In Bengali: Use warm, authentic Bengali/Benglish charm with Kolkata warmth and playful wit.
6. In Hindi: Use smooth, natural Hindi/Hinglish with relaxed Bollywood charm and friendly banter.
7. Never repeat phrases or compliments already used earlier in the conversation."""
        lang_instruction = {
            "bengali": (
                "Reply strictly in Bengali. Use either authentic Bengali script (বাংলা) "
                "or natural Benglish/Banglish (Romanized Bengali) matching the tone of the contact. "
                "Incorporate sweet Kolkata charm, witty compliments, and playful romantic banter."
            ),
            "hindi": (
                "Reply strictly in Hindi. Use either authentic Devanagari script (हिंदी) "
                "or smooth Hinglish matching the contact's style. "
                "Incorporate charismatic Bollywood charm, sweet compliments, and witty teasing."
            ),
            "english": (
                "Reply strictly in English. Be witty, charismatic, playfully flirtatious, "
                "and naturally engaging. Keep responses concise, confident, and magnetic."
            ),
            "auto": (
                "Detect the language and script used by the contact (English, Bengali, Hindi, Hinglish, Benglish). "
                "Mirror their language and script naturally with high charisma, charm, and authenticity."
            ),
        }.get(lang_clean, "Mirror the contact's language and style with charm.")
    else:
        role_desc = "an autonomous, polite, and natural personal messaging assistant"
        mode_desc = f"Mode: NORMAL CONVERSATION ({mode}). STRICTLY CASUAL, FRIENDLY, AND POLITE EVERYDAY CHAT"
        vibe_desc = vibe or "Be polite, friendly, responsive, casual, and natural"
        rules = """CRITICAL NORMAL CONVERSATION RULES:
1. Speak as the USER, not as an AI or third party. Never say "I am an AI" or "As an assistant".
2. ABSOLUTE PROHIBITION: DO NOT flirt. DO NOT send pickup lines. DO NOT send romantic teasing or cheesy compliments. This is a regular, everyday chat with a friend, family member, colleague, or acquaintance.
3. Keep the response natural, friendly, conversational, and punchy (1 to 2 sentences max), just like a real person texting.
4. Answer their question directly or ask a polite question back about their day or work.
5. In Bengali: Use natural, friendly Bengali (বাংলা or Benglish) like "হ্যাঁ একদম ঠিক বলেছো", "তারপর আর কি খবর?", etc.
6. In Hindi: Use natural, friendly Hindi (हिंदी or Hinglish) like "हाँ बिल्कुल सही कहा", "और बताओ सब कैसा चल रहा है?", etc.
7. Never repeat phrases already in the conversation history."""
        lang_instruction = {
            "bengali": (
                "Reply strictly in Bengali. Use either authentic Bengali script (বাংলা) "
                "or natural Benglish (Romanized Bengali) matching the contact's style. "
                "Keep it completely normal, friendly, and polite. ABSOLUTELY NO FLIRTING."
            ),
            "hindi": (
                "Reply strictly in Hindi. Use either authentic Devanagari script (हिंदी) "
                "or smooth Hinglish matching the contact's style. "
                "Keep it completely normal, respectful, and friendly. ABSOLUTELY NO FLIRTING."
            ),
            "english": (
                "Reply strictly in English. Be friendly, natural, casual, and polite. "
                "Keep responses concise and authentic. ABSOLUTELY NO FLIRTING."
            ),
            "auto": (
                "Detect the language and script used by the contact (English, Bengali, Hindi, Hinglish, Benglish). "
                "Mirror their language and script naturally in a friendly, normal everyday conversational tone."
            ),
        }.get(lang_clean, "Mirror the contact's language and style in a friendly, normal tone.")

    prompt = f"""
You are M.A.R.C.U.S acting as {role_desc} for your user.
You are chatting with '{contact}' on {platform_name}.

{mode_desc}.
Custom Directives: {vibe_desc}.
Language Rule: {lang_instruction}

Conversation history so far:
{hist_text or '(Beginning of conversation)'}

Latest incoming message from {contact}:
"{incoming_text}"

{rules}

Return ONLY the reply text to be sent in the chat. Do not include quotes, explanations, or labels.
"""

    try:
        reply = gemini.text(prompt, tier=gemini.FAST, timeout_ms=15_000)
        if reply and reply.strip():
            clean = reply.strip().strip('"\'')
            clean = re.sub(r"^(User|Reply|Me):\s*", "", clean, flags=re.IGNORECASE)
            return clean.strip()
    except Exception as e:
        _safe_print(f"[ChatAssistant] Gemini reply generation failed: {e}")

    # Fallback to curated lines if offline or out of quota
    if is_dating:
        return _get_curated_line(language, "pickup_lines" if not history else "compliments", mode="dating")
    return _get_curated_line(language, "openers" if not history else "replies", mode="normal")


_generate_dating_reply = _generate_chat_reply


# ── Screen Multimodal Vision Inspection ──────────────────────────────────────

def _inspect_chat_screen_with_vision(
    session: ChatSession,
) -> dict:
    """
    Captures screen and asks Gemini Vision if there is a new incoming message from the contact,
    reading its content and determining the appropriate reply.
    Uses MD5 screen hashing to skip API calls when the screen hasn't changed (saves Gemini Free quota).
    Uses REST gemini-flash-latest for fast, reliable JSON extraction.
    """
    if _capture_screen is None:
        return {"new_message": False}

    try:
        img_bytes, mime_type = _capture_screen()
    except Exception as e:
        _safe_print(f"[ChatAssistant] Screen capture error: {e}")
        return {"new_message": False}

    # MD5 screen hash check: if the screen hasn't changed at all, no new message arrived
    curr_hash = hashlib.md5(img_bytes).hexdigest()
    if session.last_screen_hash and curr_hash == session.last_screen_hash:
        # Screen is identical to previous check — no incoming activity, save free quota
        return {"new_message": False}
    session.last_screen_hash = curr_hash

    is_dating = _is_dating_mode(session.mode)
    if is_dating:
        mode_instruction = (
            f"Mode: REALISTIC DATING & WINGMAN ({session.mode}). Natural dating conversation with balanced everyday chat, playful teasing, and subtle charm.\n"
            f"- DO NOT spam pickup lines on every turn. Respond naturally to what they said, keeping the conversation engaging, curious, and pleasantly flirtatious."
        )
        reply_spec = "natural, engaging, subtly charming reply to send or empty"
    else:
        mode_instruction = (
            f"Mode: NORMAL CONVERSATION ({session.mode}). Strictly casual, friendly, polite, everyday chat.\n"
            f"- CRITICAL PROHIBITION: DO NOT flirt. DO NOT generate pickup lines or romantic comments.\n"
            f"- Formulate a polite, friendly, natural casual reply on behalf of the user matching their language and script."
        )
        reply_spec = "polite, casual normal reply to send or empty"

    recent_out = session.outgoing_history[-4:] if session.outgoing_history else []
    out_list = "\n".join(f"- \"{t}\"" for t in recent_out) if recent_out else f"- \"{session.last_outgoing_text}\""

    prompt = f"""
You are M.A.R.C.U.S, an autonomous messaging assistant for the user.
Analyze this screen capture of the chat window on {session.platform} (conversation with '{session.contact}').

LAYOUT & ROLES:
- Messages sent by USER / MARCUS (Outgoing): Aligned to the RIGHT side of the chat pane, usually colored (green/blue/purple) with checkmarks/ticks.
- Messages sent by CONTACT / OPPONENT '{session.contact}' (Incoming): Aligned to the LEFT side of the chat pane, usually white/gray, without checkmarks.
- Chronology: Conversation flows from top to bottom.

OUR PREVIOUS SENT MESSAGES (DO NOT treat these as incoming):
{out_list}

LAST INCOMING MESSAGE WE ALREADY REPLIED TO:
"{session.last_incoming_text}"

{mode_instruction}

TASK:
1. Examine the chat thread. Look at the latest message received from '{session.contact}' on the LEFT side.
2. Has '{session.contact}' sent a message that needs a reply (i.e. it is received on the left side, arrived after our message, is NOT in our sent messages list above, and is different from "{session.last_incoming_text}")?
3. If YES:
   - Extract their message text into "contact_text".
   - Detect their language and script (English, Bengali, Hindi, Benglish, Hinglish).
   - Formulate an appropriate, natural reply into "reply_text" matching their language and tone.
   - Set "new_message": true
4. If NO (the contact has not replied yet, or the latest visible message is our own sent message on the right side):
   - Set "new_message": false

Return ONLY a JSON object:
{{
  "new_message": true or false,
  "contact_text": "text of their message or empty",
  "detected_language": "english|bengali|hindi|benglish|hinglish",
  "reply_text": "{reply_spec}"
}}
"""

    try:
        part = gtypes.Part.from_bytes(data=img_bytes, mime_type=mime_type)
        result = gemini.as_json([part, prompt], tier=gemini.FAST, timeout_ms=15_000)
        if isinstance(result, dict):
            return result
    except Exception as e:
        _safe_print(f"[ChatAssistant] Vision inspection error: {e}")

    return {"new_message": False}


# ── Autonomous Chat Worker Loop ──────────────────────────────────────────────

def _chat_worker_loop(session: ChatSession, player=None, speak=None):
    """
    Continuous background loop for autonomous messaging:
    1. Opens/focuses the chat target.
    2. Sends icebreaker / starter message if initial start.
    3. Regularly inspects screen for replies from the contact.
    4. Automatically composes and sends charming dating replies.
    5. Repeats continuously until user signals stop.
    """
    _safe_print(f"[ChatAssistant] [STARTED] Autonomous loop for {session.contact} on {session.platform}")
    _safe_log(player, f"[Chat] Autonomous assistant started for {session.contact} ({session.mode} mode)")

    # Step 1: Open chat
    try:
        opened = _open_chat_target(session.platform, session.contact)
        if not opened:
            _safe_print(f"[ChatAssistant] Could not focus chat for {session.contact}")
    except Exception as e:
        _safe_print(f"[ChatAssistant] Error opening chat: {e}")

    time.sleep(1.5)

    # Step 2: Send starter message / greeting if needed
    if session.messages_exchanged == 0 and not session.stop_event.is_set():
        starter = session.last_outgoing_text
        if not starter:
            if _is_dating_mode(session.mode):
                starter = _get_curated_line(session.language, "pickup_lines", mode="dating")
            else:
                starter = _get_curated_line(session.language, "openers", mode="normal")
        
        _safe_print(f"[ChatAssistant] [OPENER] Sending to {session.contact}: '{starter}'")
        try:
            _send_chat_message(starter, session.platform)
            session.last_outgoing_text = starter
            if starter not in session.outgoing_history:
                session.outgoing_history.append(starter)
            session.messages_exchanged += 1
            session.history.append({"sender": "User", "text": starter, "time": time.time()})
            _safe_log(player, f"[Chat] Sent to {session.contact}: {starter[:45]}...")
            _update_hud_content(player, session)
            time.sleep(2.0)
        except Exception as e:
            _safe_print(f"[ChatAssistant] Failed to send opening message: {e}")

    # Step 3: Main autonomous observation & auto-reply loop
    poll_interval = 5.0  # check every ~5 seconds
    max_safety_messages = 80  # safety threshold per session

    while not session.stop_event.is_set():
        # Sleep in small slices so stop_event is instantly responsive
        sleep_until = time.time() + poll_interval + random.uniform(0.3, 1.0)
        while time.time() < sleep_until and not session.stop_event.is_set():
            time.sleep(0.4)

        if session.stop_event.is_set():
            break

        if session.messages_exchanged >= max_safety_messages:
            _safe_print(f"[ChatAssistant] [LIMIT] Reached safety limit of {max_safety_messages} messages.")
            _safe_log(player, f"[Chat] Max messages ({max_safety_messages}) reached for {session.contact}")
            break

        # Check screen for new incoming message
        try:
            info = _inspect_chat_screen_with_vision(session)
            has_new = info.get("new_message", False)
            incoming = str(info.get("contact_text", "")).strip()

            # Reject immediately if text matches any of our own sent messages (exact, substring, or fuzzy)
            if incoming and _is_our_own_message(incoming, session.outgoing_history):
                _safe_print(f"[ChatAssistant] [IGNORED] Extracted text matches our own sent message: '{incoming[:40]}...'")
                has_new = False
                incoming = ""

            # Reject if identical to incoming message we already replied to
            if incoming and incoming == session.last_incoming_text:
                has_new = False

            is_valid_new_msg = (
                has_new
                and incoming
            )

            if is_valid_new_msg:
                _safe_print(f"[ChatAssistant] [INCOMING] {session.contact}: '{incoming}'")
                session.last_incoming_text = incoming
                session.history.append({"sender": session.contact, "text": incoming, "time": time.time()})
                _safe_log(player, f"[Chat] {session.contact}: {incoming[:45]}...")

                # Determine reply
                reply = str(info.get("reply_text", "")).strip()
                if not reply:
                    detected_lang = info.get("detected_language") or session.language
                    reply = _generate_chat_reply(
                        contact=session.contact,
                        incoming_text=incoming,
                        history=session.history,
                        mode=session.mode,
                        language=detected_lang,
                        vibe=session.vibe,
                        platform_name=session.platform,
                    )

                if reply and not session.stop_event.is_set():
                    # Natural human-like typing delay (1.2s - 2.8s)
                    typing_delay = max(1.2, min(2.8, len(reply) * 0.03 + random.uniform(0.6, 1.2)))
                    _safe_print(f"[ChatAssistant] Simulating typing pause ({typing_delay:.1f}s)...")
                    time.sleep(typing_delay)

                    if session.stop_event.is_set():
                        break

                    # Focus chat window and send the reply automatically
                    _focus_window_by_title_substring([session.platform, session.contact])
                    time.sleep(0.2)

                    _send_chat_message(reply, session.platform)
                    session.last_outgoing_text = reply
                    session.outgoing_history.append(reply)
                    session.messages_exchanged += 1
                    session.history.append({"sender": "User", "text": reply, "time": time.time()})
                    session.last_action_time = time.time()
                    session.last_screen_hash = ""  # Force screen hash to refresh after sending

                    _safe_print(f"[ChatAssistant] [AUTONOMOUS REPLY] To {session.contact}: '{reply}'")
                    _safe_log(player, f"[Chat] Replied: {reply[:45]}...")
                    _update_hud_content(player, session)

                    # Give chat app time to render outgoing bubble before next inspection
                    time.sleep(2.0)

        except Exception as e:
            _safe_print(f"[ChatAssistant] Loop inspection error: {e}")

    _safe_print(f"[ChatAssistant] [STOPPED] Autonomous loop ended for {session.contact}. Exchanged {session.messages_exchanged} msgs.")
    _safe_log(player, f"[Chat] Assistant stopped for {session.contact}. Exchanged {session.messages_exchanged} messages.")


def _update_hud_content(player, session: ChatSession) -> None:
    """Updates MARCUS UI content display with latest conversation transcript."""
    if not player or not hasattr(player, "show_content"):
        return
    try:
        title = f"CHAT: {session.contact.upper()} ({session.platform.upper()})"
        mode_title = "Dating Wingman" if _is_dating_mode(session.mode) else "Normal Chat"
        lines = [f"Mode: {mode_title} | Language: {session.language.title()} | Messages: {session.messages_exchanged}\n"]
        for m in session.history[-8:]:
            lines.append(f"{m['sender']}: {m['text']}")
        hint = "Autonomous Dating Wingman" if _is_dating_mode(session.mode) else "Autonomous Chat Assistant"
        lines.append(f"\n({hint} active — say 'stop chatting' to end)")
        player.show_content(title, "\n".join(lines))
    except Exception:
        pass


# ── Action Dispatch Handler ──────────────────────────────────────────────────

def chat_assistant(
    parameters: dict,
    player=None,
    speak=None,
    session_memory=None,
    **kwargs,
) -> str:
    """
    Main entry point for Marcus Autonomous Messaging & Dating Assistant.
    Discovered automatically by core/action_loader.py.
    """
    params = parameters or {}
    action = str(params.get("action", "start")).strip().lower()
    platform_name = str(params.get("platform", "whatsapp")).strip()
    contact = str(params.get("contact", "")).strip()
    raw_mode = str(params.get("mode", "")).strip().lower()
    language = str(params.get("language", "auto")).strip().lower()
    vibe = str(params.get("vibe", "")).strip()
    starter_msg = str(params.get("starter_message", "")).strip()
    pickup_type = str(params.get("pickup_type", "")).strip()

    # Normalize action
    if any(k in action for k in ("stop", "halt", "cancel", "end", "pause", "exit")):
        action = "stop"
    elif any(k in action for k in ("status", "list", "check")):
        action = "status"
    elif any(k in action for k in ("flirt", "pickup", "compliment")):
        action = "send_pickup_line"
    else:
        action = "start"

    # Sanitize raw_mode against hallucinations/error messages
    if len(raw_mode) > 25 or any(bad in raw_mode for bad in ("demand", "msg", "error", "whatsapp", "fail", "ackno", "vision")):
        raw_mode = ""

    # Sanitize platform_name against hallucinations/error strings
    p_lower = platform_name.lower()
    if any(k in p_lower for k in ("insta", "ig")):
        platform_name = "instagram"
    elif any(k in p_lower for k in ("mess", "fb", "face")):
        platform_name = "messenger"
    else:
        platform_name = "whatsapp"

    # Sanitize contact
    contact = re.sub(r"[\r\n\t]+", " ", contact).strip()
    if " " in contact and len(contact) > 35:
        contact = contact.split("\n")[0].strip()[:35]

    if not contact or contact.lower() in ("active chat", "current", "this", "chat", "person", "opponent", "someone", "friend", "here", "window"):
        contact = "Active Chat"

    # Determine mode: default to 'normal' unless user or parameters specifically signal dating/wingman/flirting
    if not raw_mode:
        context_hints = f"{action} {vibe} {starter_msg} {pickup_type}".lower()
        if any(k in context_hints for k in ("date", "dating", "wingman", "flirt", "romantic", "pickup", "rizz", "crush")):
            mode = "dating"
        else:
            mode = "normal"
    else:
        mode = "dating" if _is_dating_mode(raw_mode) else "normal"

    if not _PYAUTOGUI:
        return "PyAutoGUI is not installed — desktop control is unavailable."

    # ── Action: STOP ──────────────────────────────────────────────────────────
    if action == "stop":
        stopped = _CHAT_MANAGER.stop_session(platform_name if contact else "", contact)
        if not stopped and not contact:
            stopped = _CHAT_MANAGER.stop_all()

        if stopped:
            summary = ", ".join(stopped)
            msg = f"Autonomous messaging assistant stopped for: {summary}. I have handed full control back to you."
            _safe_log(player, f"[Chat] Stopped: {summary}")
            return msg
        return "No active messaging assistant session was running."

    # ── Action: STATUS ────────────────────────────────────────────────────────
    if action == "status":
        active = _CHAT_MANAGER.get_active_sessions()
        if not active:
            return "No autonomous messaging assistant sessions are currently running."
        items = []
        for s in active:
            elapsed_min = int((time.time() - s.start_time) / 60)
            items.append(
                f"• {s.contact} on {s.platform} (Mode: {s.mode}, Lang: {s.language}, "
                f"Exchanged: {s.messages_exchanged} msgs, Active: {elapsed_min}m)"
            )
        return "Active Messaging Sessions:\n" + "\n".join(items)

    # ── Action: SEND_PICKUP_LINE / SINGLE_REPLY ───────────────────────────────
    if action == "send_pickup_line":
        if not contact:
            return "Please specify the contact person to send the line to."

        target_line = starter_msg
        if not target_line:
            target_line = _get_curated_line(
                language,
                "compliments" if "compliment" in pickup_type else "pickup_lines",
                mode="dating",
            )

        _safe_print(f"[ChatAssistant] Sending one-off line to {contact} on {platform_name}: '{target_line}'")
        try:
            _open_chat_target(platform_name, contact)
            time.sleep(1.0)
            _send_chat_message(target_line, platform_name)
            _safe_log(player, f"[Chat] Sent line to {contact}: {target_line[:40]}...")
            return f"Sent dating message to {contact} via {platform_name}: '{target_line}'"
        except Exception as e:
            return f"Could not send dating message: {e}"

    # ── Action: START (Autonomous Continuous Chat Loop) ───────────────────────
    if not contact:
        contact = "Active Chat"

    # Resolve starter message if not explicitly provided
    if not starter_msg:
        if _is_dating_mode(mode):
            starter_msg = _get_curated_line(language, "pickup_lines", mode="dating")
        else:
            starter_msg = _get_curated_line(language, "openers", mode="normal")

    # Create new session
    session_id = f"{platform_name}_{contact}_{int(time.time())}"
    session = ChatSession(
        session_id=session_id,
        platform=platform_name,
        contact=contact,
        mode=mode,
        language=language,
        vibe=vibe,
        last_outgoing_text=starter_msg,
        outgoing_history=[starter_msg] if starter_msg else [],
    )

    # Launch daemon background thread
    worker = threading.Thread(
        target=_chat_worker_loop,
        args=(session, player, speak),
        name=f"chat-assistant-{contact}",
        daemon=True,
    )
    session.worker_thread = worker
    _CHAT_MANAGER.register_session(session)
    worker.start()

    lang_desc = {
        "bengali": "in Bengali (বাংলা / Benglish)",
        "hindi": "in Hindi (हिंदी / Hinglish)",
        "english": "in English",
        "auto": "matching their language (English, Bengali, Hindi)",
    }.get(language, f"in {language}")

    mode_label = "dating wingman" if _is_dating_mode(mode) else "normal conversation"
    reply_text = (
        f"Autonomous messaging assistant activated for {contact} on {platform_name} {lang_desc} in {mode_label} mode. "
        f"I have opened the chat and will continuously read replies and respond on your behalf."
    )

    _safe_log(player, f"[Chat] Started autonomous assistant for {contact} on {platform_name} ({mode_label} mode)")

    return reply_text


# ── Tool Declaration (Auto-discovered by core/action_loader.py) ───────────────
TOOL = {
    "name": "chat_assistant",
    "description": (
        "Autonomous messaging assistant and dating wingman for WhatsApp, Instagram, and Facebook Messenger. "
        "Opens the native application or browser directly (no official API required), locates the contact, "
        "reads incoming messages, and autonomously conducts conversations in English, Bengali (বাংলা & Benglish), "
        "and Hindi (हिंदी & Hinglish). Runs in the background and keeps replying until stopped. "
        "Features two strictly separated modes: "
        "1. 'normal' (DEFAULT): Casual, friendly, respectful everyday chat for friends, family, or colleagues (ABSOLUTELY NO FLIRTING). "
        "2. 'dating': Charismatic dating wingman with sweet compliments, playful banter, and pickup lines (ONLY when explicitly requested). "
        "Use action='start' to begin autonomous chatting, action='stop' to halt, action='status' to inspect active sessions, "
        "or action='send_pickup_line' for a single charming opener."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action: 'start' (autonomous loop), 'stop' (halt chatting), 'status' (check running chats), 'send_pickup_line' (one-off line)"
            },
            "platform": {
                "type": "STRING",
                "description": "Platform: 'whatsapp', 'instagram', 'facebook', or 'messenger' (default: 'whatsapp')"
            },
            "contact": {
                "type": "STRING",
                "description": "The person or contact name to chat with (e.g. 'Priya', 'Sneha', 'Rahul')"
            },
            "mode": {
                "type": "STRING",
                "description": "Conversation mode: 'normal' (casual/polite/friendly - DEFAULT) or 'dating' (flirty wingman - ONLY when requested)"
            },
            "language": {
                "type": "STRING",
                "description": "Language: 'auto' (detect and match), 'english', 'bengali' (বাংলা / Benglish), or 'hindi' (हिंदी / Hinglish)"
            },
            "vibe": {
                "type": "STRING",
                "description": "Optional custom guidance (e.g. 'friendly and polite', 'ask about work', 'compliment her smile')"
            },
            "starter_message": {
                "type": "STRING",
                "description": "Optional opening message to send (if omitted, an appropriate normal opener or dating line is chosen based on mode)"
            },
            "pickup_type": {
                "type": "STRING",
                "description": "For dating mode: 'pickup_lines', 'compliments', 'banter', 'openers'"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": chat_assistant,
}
