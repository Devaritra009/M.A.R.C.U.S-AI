"""
Creator / Master Profile Action for MARCUS.

Creator: Aritra Sarkar
Portfolio: https://aritrasarkarportfolio.vercel.app/
LinkedIn:  https://www.linkedin.com/in/devaritra/

Flow:
1. Immediately opens the creator's portfolio website in a new browser tab.
2. Formats and returns the comprehensive spoken briefing about Aritra Sarkar for MARCUS.
3. Automatically launches a background monitor that waits for MARCUS to finish the briefing speech,
   then opens the creator's LinkedIn profile in another browser tab.
"""
from __future__ import annotations

import threading
import time
import webbrowser

PORTFOLIO_URL = "https://aritrasarkarportfolio.vercel.app/"
LINKEDIN_URL  = "https://www.linkedin.com/in/devaritra/"

CREATOR_BRIEFING = (
    "My creator is Aritra Sarkar, a Computer Science student from Sammilani Mahavidyalaya, "
    "affiliated with the University of Calcutta.\n\n"
    "Aritra is a technology enthusiast who enjoys exploring different areas of computer science "
    "and combining them to build useful and creative solutions. His interests extend across Artificial Intelligence, "
    "Web Development, IoT, Embedded Systems, Cybersecurity, UI/UX Design, and Graphic Design.\n\n"
    "He believes strongly in learning through experimentation and building real projects rather than limiting "
    "himself to theoretical knowledge. He enjoys understanding how things work, taking an idea from concept to "
    "implementation, and continuously improving what he creates.\n\n"
    "On the technical side, Aritra works with C, C++, Java, Python, JavaScript, and TypeScript, alongside web frameworks "
    "like React, Next.js, and Tailwind CSS. In hardware and IoT, he develops with ESP8266 and ESP32 boards, sensors, RFID, "
    "and wireless communication. In cybersecurity, he focuses on internal system mechanics and secure architecture.\n\n"
    "On the creative side, he is passionate about UI/UX and graphic design — emphasizing responsive aesthetics, smooth typography, "
    "and intuitive interactions. His core philosophy is: Curious, Creative, Experimental.\n\n"
    "As his AI assistant, my role is to understand his vision, support his continuous learning, and work alongside him as he turns "
    "ambitious ideas into reality. He is the creator; I am the assistant built to help him explore, create, learn, and build what comes next."
)


def _delayed_open_linkedin(player=None, delay_seconds: float = 20.0) -> None:
    """
    Monitor the speech state: wait until MARCUS begins and finishes speaking
    the briefing, then open the creator's LinkedIn profile in a new tab.
    """
    try:
        # Wait up to 6 seconds for speech to activate on HUD
        start_wait = time.time()
        while time.time() - start_wait < 6.0:
            if player and hasattr(player, "_win") and getattr(player._win.hud, "speaking", False):
                break
            time.sleep(0.3)

        # Wait while speaking is active (up to 60s max safeguard)
        speak_start = time.time()
        while time.time() - speak_start < 60.0:
            if player and hasattr(player, "_win"):
                is_speaking = getattr(player._win.hud, "speaking", False)
                # If speech has stopped and we had at least 3 seconds of speech, we're done
                if not is_speaking and (time.time() - speak_start > 3.0):
                    break
            else:
                # Fallback if headless/no player: wait the estimated reading delay
                if time.time() - speak_start > delay_seconds:
                    break
            time.sleep(0.5)

        # Short breathing pause after speech finishes before opening LinkedIn tab
        time.sleep(1.2)
        webbrowser.open_new_tab(LINKEDIN_URL)
    except Exception as e:
        print(f"[CreatorProfile] Error in delayed LinkedIn tab opening: {e}")


def creator_profile(
    parameters: dict | None = None,
    player=None,
    session_memory=None,
) -> str:
    """
    Executes the Creator/Master profile workflow:
    1. Opens creator's portfolio.
    2. Logs and presents profile card on the UI if available.
    3. Spawns background thread to open LinkedIn profile when briefing concludes.
    4. Returns the spoken briefing text for Gemini Live.
    """
    # 1. Open portfolio immediately
    try:
        webbrowser.open_new_tab(PORTFOLIO_URL)
    except Exception as e:
        print(f"[CreatorProfile] Failed to open portfolio: {e}")

    # 2. Present on UI
    if player:
        try:
            player.write_log("⚡ ACTION: Opened Creator Portfolio (https://aritrasarkarportfolio.vercel.app/)")
            player.write_log(
                "🤖 MARCUS: Presenting Creator & Master profile — Aritra Sarkar (University of Calcutta / Sammilani Mahavidyalaya)."
            )
            # Display rich content panel if available
            if hasattr(player, "show_content"):
                summary_card = (
                    "### 🌟 MARCUS Master & Creator Profile\n\n"
                    "**Creator:** Aritra Sarkar\n\n"
                    "**Institution:** Sammilani Mahavidyalaya (Affiliated with University of Calcutta)\n\n"
                    "**Specializations:** Artificial Intelligence, Full-Stack Web Development, IoT & Embedded Systems, "
                    "Cybersecurity, UI/UX & Graphic Design.\n\n"
                    "**Core Philosophy:** Curious. Creative. Experimental.\n\n"
                    f"**Portfolio:** [{PORTFOLIO_URL}]({PORTFOLIO_URL})\n\n"
                    f"**LinkedIn:** [{LINKEDIN_URL}]({LINKEDIN_URL})\n\n"
                    "*(Opening LinkedIn profile in browser upon completion of briefing...)*"
                )
                player.show_content("Creator Profile — Aritra Sarkar", summary_card)
        except Exception:
            pass

    # 3. Schedule opening LinkedIn profile in background once briefing finishes
    t = threading.Thread(target=_delayed_open_linkedin, args=(player, 18.0), daemon=True)
    t.start()

    # 4. Save to session memory if available
    if session_memory:
        try:
            session_memory.set_last_search(
                query="creator profile Aritra Sarkar",
                response="Presented creator profile for Aritra Sarkar.",
            )
        except Exception:
            pass

    # 5. Return briefing for Gemini Live spoken audio
    return CREATOR_BRIEFING


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "creator_profile",
    "description": (
        "Provides a comprehensive briefing about MARCUS's creator and master, Aritra Sarkar. "
        "ALWAYS call this tool whenever the user asks 'tell about your creator or master', "
        "'who made you', 'who is your creator', 'who is your master', 'who built you', "
        "'tell me about Aritra', 'who is Aritra Sarkar', or requests the Creator/Master profile. "
        "This tool automatically opens his portfolio website first, gives the official briefing, "
        "and opens his LinkedIn profile after the briefing."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "Optional user inquiry about the creator.",
            }
        },
    },
    "handler": creator_profile,
}
