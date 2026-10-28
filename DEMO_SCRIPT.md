# Demo Script (3-4 minutes)

Speak in your own words. The lines below are a guide. Practise once with the app open.

## Before the demo (2 minutes)
* Double-click `run.bat` so the app is already open in the browser.
* Keep `outputs\sample_property_video.mp4` ready as a backup in case the laptop is slow.
* Have `src\script_generator.py` and `src\video_generator.py` open in your editor.

## 1. Problem (20 seconds)
"Real-estate sales teams spend time making a promotional video for every property by hand. My app automates it:
the agent enters the property facts and uploads 4-8 photos, and gets a ready-to-share MP4."

## 2. Live demo (90 seconds)
1. **Show the empty form** and press **Generate video**. Point at the friendly error list. "Missing details and image-count problems never crash the app."
2. Click **Load sample property** (fictional data, 7 synthetic illustrations and a label under each photo, such as Kitchen).
3. Press **Generate video**. While the progress bar runs say: "The script is created first, then each image becomes a scene with a caption, and FFmpeg encodes the MP4."
4. **Play the video.** Point out: opening hook, price scene, feature scenes (each feature is shown with its matching photo), final enquiry prompt with contact details, smooth cross-fades, slow zoom.
5. Open the **Scene captions** table and the **Voice-over script** tab. "Every word is either the user's fact or a fixed template sentence."
6. Click **Download MP4**.
7. (Optional, 20 s) Switch the aspect ratio to vertical 9:16 for social media and show it renders.

## 3. Technical decisions (60 seconds)
* **Streamlit + MoviePy + Pillow**: the simplest stack that installs cleanly on a normal Windows laptop. No ImageMagick, no GPU, no API keys.
* **Template-based script with a grounding check**: "A real-estate ad must never invent a pool or a distance. Templates make that impossible. `check_grounding()` re-reads the finished script and rejects any number or word that is not in the user's facts or the template vocabulary. Tests also confirm the templates contain no words like luxury or stunning."
* **Validation first**: required fields, lengths, contact format, and for images the *real* file type, corruption, size and phone-photo rotation.
* **Reliability**: the video is first written to a temporary file and renamed only when complete; every failure becomes a readable message.
* **102 automated tests**, including real MP4 renders that check codec, size, duration and that the last frame shows the enquiry prompt.

## 4. Limitations and future work (30 seconds)
* No narration audio or background music yet (optional in the assignment). The voice-over exists as text.
* Photos are used in upload order and the app does not understand what a photo shows; it relies on the optional labels you type (future: automatic labelling with an image classifier).
* Future: text-to-speech, licensed music, an LLM that rewrites captions but is checked by the same grounding guard, auto-ordering photos with an image classifier, batch mode.

---

# Likely questions and answers (simple Hinglish)

**Q: Isme AI kahan hai?**
A: Script generation rule-based NLG hai: fixed templates mein user ke facts bharte hain. Uske upar ek grounding checker hai jo verify karta hai ki har number aur word user ke facts ya template se aaya hai. Maine jaan-bujhkar LLM nahi liya kyunki LLM kabhi-kabhi amenities ya distance invent kar deta hai, aur real estate mein ye galat claim hota hai. Future mein LLM add kar sakte hain, aur wahi checker uska output verify karega.

**Q: Facts invent nahi hote, ye kaise guarantee karte ho?**
A: Teen layers: (1) templates mein sirf neutral words hain, (2) `check_grounding()` har scene ke numbers aur words verify karta hai, (3) tests mein ek invented "Swimming pool" aur "5 km from airport" daal ke dikhaya hai ki checker usse pakad leta hai.

**Q: Images scenes mein kaise arrange hoti hain?**
A: Har image ek scene banti hai. Pehli image opening hook, doosri intro, beech ki feature scenes, aur aakhri image closing enquiry. Order upload ka rehta hai. User photo ke neeche label likh sakta hai (jaise Kitchen), aur matcher "Modular kitchen" feature ko usi photo par laga deta hai.

**Q: Video browser mein chale, iske liye kya kiya?**
A: H.264 codec (libx264) aur `yuv420p` pixel format. Ye dono har browser aur phone mein chalte hain. Test mein ffmpeg se codec aur pixel format check hota hai.

**Q: Text overlay MoviePy ke TextClip se kyun nahi?**
A: TextClip ko ImageMagick ya font path chahiye, jo Windows pe sabse zyada install errors deta hai. Pillow se text draw karna aur bundled font use karna har PC pe chalta hai.

**Q: Transition kaise banaya?**
A: Har scene ke clip ko 0.8 second ka CrossFadeIn deke agle scene ke start par overlap karte hain. Saath mein har image par 6% slow zoom (Ken Burns effect) hai.

**Q: Galat ya corrupted image upload ho toh?**
A: Pillow se pehle `verify()` karte hain, phir poori image load karke dekhte hain. Sirf extension nahi, asli format bhi check hota hai (GIF ko .jpg rename karne se kaam nahi chalega). Message mein file ka naam aur wajah dikhti hai.

**Q: Export fail ho jaye toh?**
A: Video pehle `.part.mp4` temp file mein banta hai, aur complete hone par hi rename hota hai. Fail hone par temp file delete ho jaati hai aur user ko friendly message milta hai (jaise disk full ya file locked). Test mein fake failure inject karke ye verify kiya hai.

**Q: Narration kyun nahi?**
A: Assignment mein optional hai. Maine pehle reliable core (facts-only script, valid MP4, validation, tests) pakka kiya. Voice-over script text mein bana hai, toh TTS add karna agla chhota step hai.

**Q: Kaunsi cheez improve karoge?**
A: TTS narration, licensed background music, LLM-based caption rewriting (grounding check ke saath), photo ko classify karke automatic order, aur batch generation.

## Code tour (if asked to explain a file)
| File | Say this |
|---|---|
| `src/validators.py` | "Sab input yahin check hota hai. Errors block karte hain, warnings sirf bataate hain." |
| `src/script_generator.py` | "Templates dict, `generate_script()` scenes banata hai, `check_grounding()` guard hai." |
| `src/video_generator.py` | "`build_overlay()` caption panel draw karta hai, `_make_scene_clip()` zoom wala clip, `generate_video()` sab jodkar MP4 export karta hai." |
| `app.py` | "Streamlit UI. Result `session_state` mein rakhte hain taaki download button dabane par video gayab na ho." |
| `src/config.py` | "Saari settings ek jagah." |
